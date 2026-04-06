"""Auth service — business logic for registration, OTP verification, and resend.

Orchestrates repositories and security utilities. Contains ALL business
rules and decisions. NEVER imports FastAPI, HTTP concepts, or database
session objects directly.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_otp,
    hash_otp,
    hash_password,
    hash_token,
    verify_otp,
    verify_password,
)
from app.modules.auth.exceptions import (
    AccountDisabledException,
    EmailAlreadyRegisteredException,
    EmailAlreadyVerifiedException,
    EmailNotVerifiedException,
    InvalidCredentialsException,
    NoPendingVerificationException,
    OtpExpiredException,
    OtpInvalidException,
    OtpMaxAttemptsException,
    OtpRateLimitException,
)
from app.modules.auth.repository import (
    RefreshTokenRepository,
    VerificationTokenRepository,
)
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterNgoRequest,
    RegisterResponse,
    ResendOtpRequest,
    UserBasicResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.modules.ngo.repository import NgoRepository
from app.modules.users.repository import UserRepository

logger = logging.getLogger(__name__)

_ROLE_NGO_USER = "ngo_user"
_TEMP_REG_PREFIX = "TEMP-"


class AuthService:
    """Handles registration, OTP verification, and OTP resend logic."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: VerificationTokenRepository,
        refresh_repo: RefreshTokenRepository,
        ngo_repo: NgoRepository,
    ) -> None:
        """Inject all required repositories."""
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._refresh_repo = refresh_repo
        self._ngo_repo = ngo_repo

    # ------------------------------------------------------------------
    # register_ngo
    # ------------------------------------------------------------------

    async def register_ngo(
        self,
        data: RegisterNgoRequest,
    ) -> RegisterResponse:
        """Register a new NGO user and send OTP email.

        Handles the case where an unverified user re-registers with
        the same email by reusing the existing user and resending OTP.
        """
        existing_user = await self._user_repo.get_by_email(data.email)

        if existing_user is not None:
            return await self._handle_existing_user(existing_user, data)

        return await self._create_new_user_and_send_otp(data)

    async def _handle_existing_user(
        self,
        existing_user: object,
        data: RegisterNgoRequest,
    ) -> RegisterResponse:
        """Handle registration when email already exists in the system."""
        from app.modules.users.models import User

        user: User = existing_user  # type: ignore[assignment]

        if user.email_verified:
            raise EmailAlreadyRegisteredException()

        # Unverified user re-registering — reuse and resend OTP
        await self._revoke_and_send_otp(
            user_id=user.user_id,
            email=data.email,
            org_name=data.org_name,
        )
        return RegisterResponse(
            message="Verification OTP sent to your email",
            email=data.email,
        )

    async def _create_new_user_and_send_otp(
        self,
        data: RegisterNgoRequest,
    ) -> RegisterResponse:
        """Create a brand-new user and send the first OTP."""
        password_hash = hash_password(data.password)

        user = await self._user_repo.create_user(
            email=data.email,
            password_hash=password_hash,
            role=_ROLE_NGO_USER,
        )
        logger.info("New NGO user created: %s", user.user_id)

        await self._revoke_and_send_otp(
            user_id=user.user_id,
            email=data.email,
            org_name=data.org_name,
        )
        return RegisterResponse(
            message="Verification OTP sent to your email",
            email=data.email,
        )

    # ------------------------------------------------------------------
    # verify_otp
    # ------------------------------------------------------------------

    async def verify_otp(
        self,
        data: VerifyOtpRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> VerifyOtpResponse:
        """Verify OTP and complete NGO registration.

        Creates ngo_profile, ngo_resources, and JWT tokens in a single
        transaction (the session commit happens in the dependency).
        """
        token = await self._token_repo.find_open_token_by_email(data.email)
        if token is None:
            raise NoPendingVerificationException()

        self._validate_token_not_expired(token.expires_at)
        self._validate_attempts_remaining(
            token.attempts_count,
            token.max_attempts,
        )
        await self._validate_otp_match(
            data.otp,
            token.token_hash,
            token.verification_token_id,
        )

        # All validations passed — execute the registration transaction
        return await self._complete_verification(
            token=token,
            org_name=data.org_name,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def _complete_verification(
        self,
        *,
        token: object,
        org_name: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> VerifyOtpResponse:
        """Execute all post-OTP steps in the current transaction."""
        from app.modules.auth.models import AuthVerificationToken

        t: AuthVerificationToken = token  # type: ignore[assignment]

        await self._token_repo.mark_used(t.verification_token_id)

        now = datetime.now(timezone.utc)
        await self._user_repo.mark_email_verified(t.user_id, now)

        reg_number = _generate_temp_registration_number()
        profile = await self._ngo_repo.create_profile(
            ngo_id=t.user_id,
            org_name=org_name,
            org_email=t.email,
            registration_number=reg_number,
        )
        await self._ngo_repo.create_resources(t.user_id)

        access_token, refresh_token = self._generate_tokens(t.user_id)

        await self._store_refresh_token(
            user_id=t.user_id,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info("NGO verified: user=%s org='%s'", t.user_id, org_name)

        return VerifyOtpResponse(
            message="Email verified successfully",
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserBasicResponse(
                user_id=t.user_id,
                email=t.email,
                role=_ROLE_NGO_USER,
                org_name=org_name,
                is_active=True,
                email_verified=True,
                verification_status=profile.verification_status,
            ),
        )

    # ------------------------------------------------------------------
    # login
    # ------------------------------------------------------------------

    async def login(
        self,
        data: LoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResponse:
        """Authenticate a verified NGO user and return JWT tokens.

        Validation order (fail-fast):
        1. User exists by email
        2. Password matches bcrypt hash
        3. Account is active
        4. Email is verified
        """
        user = await self._user_repo.get_by_email(data.email)

        # Always run verify_password even when user is None to prevent
        # timing-based user enumeration attacks.
        password_ok = self._check_password(data.password, user.password_hash if user else "$2b$12$invalidhashpadding000000000000000")

        if user is None or not password_ok:
            raise InvalidCredentialsException()

        self._validate_account_active(user.is_active)
        self._validate_email_verified(user.email_verified)

        access_token, refresh_token = self._generate_tokens(user.user_id)

        now = datetime.now(timezone.utc)
        await self._user_repo.update_last_login(user.user_id, now)

        await self._store_refresh_token(
            user_id=user.user_id,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        profile = await self._ngo_repo.get_profile_by_ngo_id(user.user_id)

        logger.info("NGO login: user=%s", user.user_id)

        return LoginResponse(
            message="Login successful",
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserBasicResponse(
                user_id=user.user_id,
                email=user.email,
                role=user.role,
                org_name=profile.org_name if profile else "",
                is_active=user.is_active,
                email_verified=user.email_verified,
                verification_status=profile.verification_status if profile else "pending",
            ),
        )

    # ------------------------------------------------------------------
    # resend_otp
    # ------------------------------------------------------------------

    async def resend_otp(
        self,
        data: ResendOtpRequest,
    ) -> dict[str, str]:
        """Resend OTP to an unverified user with rate limiting."""
        user = await self._user_repo.get_by_email(data.email)
        if user is None:
            from app.core.exceptions import NotFoundException
            raise NotFoundException(resource="Account", identifier=data.email)

        if user.email_verified:
            raise EmailAlreadyVerifiedException()

        await self._check_otp_rate_limit(user.user_id)

        await self._revoke_and_send_otp(
            user_id=user.user_id,
            email=data.email,
            org_name="your organisation",
        )
        return {"message": "New OTP sent to your email"}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _revoke_and_send_otp(
        self,
        *,
        user_id: uuid.UUID,
        email: str,
        org_name: str,
    ) -> None:
        """Revoke old tokens, create a new one, and send the OTP email."""
        await self._token_repo.revoke_open_tokens(user_id)

        otp_plain = generate_otp()
        otp_hashed = hash_otp(otp_plain)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.OTP_EXPIRE_MINUTES,
        )

        await self._token_repo.create_token(
            user_id=user_id,
            email=email,
            token_hash=otp_hashed,
            expires_at=expires_at,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
        )

        from app.modules.auth.email import send_otp_email
        await send_otp_email(email, otp_plain, org_name)

    def _validate_token_not_expired(self, expires_at: datetime) -> None:
        """Raise if the token has expired."""
        if expires_at < datetime.now(timezone.utc):
            raise OtpExpiredException()

    def _validate_attempts_remaining(
        self,
        attempts: int,
        max_attempts: int,
    ) -> None:
        """Raise if max OTP attempts have been reached."""
        if attempts >= max_attempts:
            raise OtpMaxAttemptsException()

    async def _validate_otp_match(
        self,
        plain_otp: str,
        hashed_otp: str,
        token_id: uuid.UUID,
    ) -> None:
        """Verify OTP hash match; increment attempts on failure."""
        if not verify_otp(plain_otp, hashed_otp):
            await self._token_repo.increment_attempts(token_id)
            raise OtpInvalidException()

    def _generate_tokens(
        self,
        user_id: uuid.UUID,
    ) -> tuple[str, str]:
        """Create JWT access and refresh token pair."""
        subject = str(user_id)
        access = create_access_token(subject, {"role": _ROLE_NGO_USER})
        refresh = create_refresh_token(subject)
        return access, refresh

    async def _store_refresh_token(
        self,
        *,
        user_id: uuid.UUID,
        refresh_token: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        """Hash and store a refresh token in the database."""
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )
        await self._refresh_repo.create_token(
            user_id=user_id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def _check_otp_rate_limit(
        self,
        user_id: uuid.UUID,
    ) -> None:
        """Enforce max OTPs per hour rate limit."""
        recent_count = await self._token_repo.count_recent_tokens(user_id)
        if recent_count >= settings.OTP_RATE_LIMIT_PER_HOUR:
            raise OtpRateLimitException()

    def _check_password(self, plain_password: str, password_hash: str) -> bool:
        """Constant-time bcrypt password comparison."""
        return verify_password(plain_password, password_hash)

    def _validate_account_active(self, is_active: bool) -> None:
        """Raise if the account has been disabled."""
        if not is_active:
            raise AccountDisabledException()

    def _validate_email_verified(self, email_verified: bool) -> None:
        """Raise if the user has not yet verified their email."""
        if not email_verified:
            raise EmailNotVerifiedException()


def _generate_temp_registration_number() -> str:
    """Generate a temporary registration number: TEMP-XXXXXXXX."""
    return f"{_TEMP_REG_PREFIX}{uuid.uuid4().hex[:8].upper()}"
