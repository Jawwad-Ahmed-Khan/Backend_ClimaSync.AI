"""Auth service — business logic for registration, login, OTP verification,
password management, token refresh, logout, and profile operations.

Orchestrates repositories and security utilities. Contains ALL business
rules and decisions. NEVER imports FastAPI, HTTP concepts, or database
session objects directly.

Designed for extensibility: login() is structured so adding new
authentication strategies (e.g. social/OAuth) requires only new
service methods — the core token generation and storage helpers
are shared and role-agnostic.
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
    InvalidRefreshTokenException,
    NoProfileFoundException,
    NoPendingVerificationException,
    OtpExpiredException,
    OtpInvalidException,
    OtpMaxAttemptsException,
    OtpRateLimitException,
    PasswordMismatchException,
    PasswordSameAsOldException,
)
from app.modules.auth.repository import (
    RefreshTokenRepository,
    VerificationTokenRepository,
)
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterNgoRequest,
    RegisterResponse,
    ResetPasswordRequest,
    ResendOtpRequest,
    UpdateProfileRequest,
    UserBasicResponse,
    UserProfileResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.modules.ngo.repository import NgoRepository
from app.modules.users.repository import UserRepository

logger = logging.getLogger(__name__)

_ROLE_NGO_USER = "ngo_user"
_TEMP_REG_PREFIX = "TEMP-"
_PURPOSE_EMAIL_VERIFICATION = "email_verification"
_PURPOSE_PASSWORD_RESET = "password_reset"


class AuthService:
    """Handles registration, login, OTP verification, password management,
    token refresh, logout, and profile operations."""

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
            purpose=_PURPOSE_EMAIL_VERIFICATION,
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
            purpose=_PURPOSE_EMAIL_VERIFICATION,
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
        token = await self._token_repo.find_open_token_by_email(
            data.email, purpose=_PURPOSE_EMAIL_VERIFICATION,
        )
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

        access_token, refresh_token = self._generate_tokens(
            t.user_id, role=_ROLE_NGO_USER,
        )

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
        2. Password matches bcrypt hash (constant-time even if user is None)
        3. Account is active
        4. Email is verified

        Extensibility:
            Additional authentication strategies (e.g. social/OAuth)
            can be added as new public methods that share the private
            helpers `_generate_tokens`, `_store_refresh_token`, etc.
        """
        user = await self._user_repo.get_by_email(data.email)

        # Always run verify_password even when user is None to prevent
        # timing-based user enumeration attacks.
        _dummy_hash = "$2b$12$invalidhashpadding000000000000000"
        password_ok = self._check_password(
            data.password,
            user.password_hash if user else _dummy_hash,
        )

        if user is None or not password_ok:
            raise InvalidCredentialsException()

        self._validate_account_active(user.is_active)
        self._validate_email_verified(user.email_verified)

        # Use the role stored on the user record (supports ngo_user + admin)
        access_token, refresh_token = self._generate_tokens(
            user.user_id, role=user.role,
        )

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
                verification_status=(
                    profile.verification_status if profile else "pending"
                ),
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

        await self._check_otp_rate_limit(
            user.user_id, purpose=_PURPOSE_EMAIL_VERIFICATION,
        )

        await self._revoke_and_send_otp(
            user_id=user.user_id,
            email=data.email,
            org_name="your organisation",
            purpose=_PURPOSE_EMAIL_VERIFICATION,
        )
        return {"message": "New OTP sent to your email"}

    # ------------------------------------------------------------------
    # forgot_password
    # ------------------------------------------------------------------

    async def forgot_password(
        self,
        data: ForgotPasswordRequest,
    ) -> dict[str, str]:
        """Send password reset OTP to the user's email.

        Anti-enumeration: always returns the same success message
        regardless of whether the email exists in the system.
        """
        user = await self._user_repo.get_by_email(data.email)

        if user is not None and user.email_verified and user.is_active:
            # Rate limit check
            await self._check_otp_rate_limit(
                user.user_id, purpose=_PURPOSE_PASSWORD_RESET,
            )

            await self._revoke_and_send_otp(
                user_id=user.user_id,
                email=data.email,
                purpose=_PURPOSE_PASSWORD_RESET,
            )
            logger.info("Password reset OTP sent: user=%s", user.user_id)
        else:
            # Log but don't reveal to the caller that the email doesn't exist
            logger.info(
                "Password reset requested for unknown/unverified email: %s",
                data.email,
            )

        return {
            "message": (
                "If an account with this email exists, "
                "a password reset code has been sent."
            ),
        }

    # ------------------------------------------------------------------
    # reset_password
    # ------------------------------------------------------------------

    async def reset_password(
        self,
        data: ResetPasswordRequest,
    ) -> dict[str, str]:
        """Verify OTP and reset the user's password.

        After success: marks token used, updates password hash,
        and revokes ALL refresh tokens (forces re-login everywhere).
        """
        token = await self._token_repo.find_open_token_by_email(
            data.email, purpose=_PURPOSE_PASSWORD_RESET,
        )
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

        # OTP verified — reset the password
        await self._token_repo.mark_used(token.verification_token_id)

        new_hash = hash_password(data.new_password)
        now = datetime.now(timezone.utc)
        await self._user_repo.update_password(token.user_id, new_hash, now)

        # Force re-login on all devices
        await self._refresh_repo.revoke_all_user_tokens(
            token.user_id, reason="password_reset",
        )

        logger.info("Password reset completed: user=%s", token.user_id)

        return {"message": "Password has been reset successfully. Please log in with your new password."}

    # ------------------------------------------------------------------
    # change_password
    # ------------------------------------------------------------------

    async def change_password(
        self,
        user_id: uuid.UUID,
        data: ChangePasswordRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResponse:
        """Change password for an authenticated user.

        Validates current password, ensures new != old, updates hash,
        revokes all existing refresh tokens, and returns fresh tokens
        for the current session.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise InvalidCredentialsException()

        # Verify current password
        if not self._check_password(data.current_password, user.password_hash):
            raise PasswordMismatchException()

        # Ensure new password is different
        if self._check_password(data.new_password, user.password_hash):
            raise PasswordSameAsOldException()

        # Update password
        new_hash = hash_password(data.new_password)
        now = datetime.now(timezone.utc)
        await self._user_repo.update_password(user_id, new_hash, now)

        # Revoke all existing sessions
        await self._refresh_repo.revoke_all_user_tokens(
            user_id, reason="password_changed",
        )

        # Issue fresh tokens for the current session
        access_token, refresh_token = self._generate_tokens(
            user_id, role=user.role,
        )
        await self._store_refresh_token(
            user_id=user_id,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        profile = await self._ngo_repo.get_profile_by_ngo_id(user_id)

        logger.info("Password changed: user=%s", user_id)

        return LoginResponse(
            message="Password changed successfully",
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserBasicResponse(
                user_id=user_id,
                email=user.email,
                role=user.role,
                org_name=profile.org_name if profile else "",
                is_active=user.is_active,
                email_verified=user.email_verified,
                verification_status=(
                    profile.verification_status if profile else "pending"
                ),
            ),
        )

    # ------------------------------------------------------------------
    # refresh_token
    # ------------------------------------------------------------------

    async def refresh_token(
        self,
        data: RefreshTokenRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResponse:
        """Exchange a valid refresh token for a new access + refresh token pair.

        Implements single-use token rotation: the old refresh token is
        revoked and a new one is issued.
        """
        token_hash = hash_token(data.refresh_token)
        stored_token = await self._refresh_repo.find_active_by_hash(token_hash)

        if stored_token is None:
            raise InvalidRefreshTokenException()

        # Check expiry
        if stored_token.expires_at < datetime.now(timezone.utc):
            await self._refresh_repo.revoke_token(
                stored_token.refresh_token_id, reason="expired",
            )
            raise InvalidRefreshTokenException()

        # Fetch user
        user = await self._user_repo.get_by_id(stored_token.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenException()

        # Revoke old token (rotation)
        await self._refresh_repo.revoke_token(
            stored_token.refresh_token_id, reason="token_rotated",
        )

        # Issue new pair
        access_token, new_refresh_token = self._generate_tokens(
            user.user_id, role=user.role,
        )
        await self._store_refresh_token(
            user_id=user.user_id,
            refresh_token=new_refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        profile = await self._ngo_repo.get_profile_by_ngo_id(user.user_id)

        return LoginResponse(
            message="Token refreshed successfully",
            access_token=access_token,
            refresh_token=new_refresh_token,
            user=UserBasicResponse(
                user_id=user.user_id,
                email=user.email,
                role=user.role,
                org_name=profile.org_name if profile else "",
                is_active=user.is_active,
                email_verified=user.email_verified,
                verification_status=(
                    profile.verification_status if profile else "pending"
                ),
            ),
        )

    # ------------------------------------------------------------------
    # logout / logout_all
    # ------------------------------------------------------------------

    async def logout(
        self,
        data: LogoutRequest,
    ) -> dict[str, str]:
        """Revoke a single refresh token (logout current session)."""
        token_hash = hash_token(data.refresh_token)
        stored_token = await self._refresh_repo.find_active_by_hash(token_hash)

        if stored_token is not None:
            await self._refresh_repo.revoke_token(
                stored_token.refresh_token_id, reason="user_logout",
            )
            logger.info("Logout: user=%s", stored_token.user_id)

        # Always return success (don't reveal if token was valid)
        return {"message": "Logged out successfully"}

    async def logout_all(
        self,
        user_id: uuid.UUID,
    ) -> dict[str, str]:
        """Revoke all refresh tokens for a user (logout everywhere)."""
        await self._refresh_repo.revoke_all_user_tokens(
            user_id, reason="user_logout_all",
        )
        logger.info("Logout all sessions: user=%s", user_id)
        return {"message": "All sessions have been logged out"}

    # ------------------------------------------------------------------
    # get_me / update_profile
    # ------------------------------------------------------------------

    async def get_me(
        self,
        user_id: uuid.UUID,
    ) -> UserProfileResponse:
        """Return the full profile for the authenticated user."""
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise InvalidCredentialsException()

        profile = await self._ngo_repo.get_profile_by_ngo_id(user_id)
        if profile is None:
            raise NoProfileFoundException()

        return UserProfileResponse(
            user_id=user.user_id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            email_verified=user.email_verified,
            org_name=profile.org_name,
            head_of_operations=profile.head_of_operations,
            phone=profile.phone,
            website=profile.website,
            base_city=profile.base_city,
            base_district=profile.base_district,
            base_province=profile.base_province,
            verification_status=profile.verification_status,
            last_login_at=user.last_login_at,
        )

    async def update_profile(
        self,
        user_id: uuid.UUID,
        data: UpdateProfileRequest,
    ) -> UserProfileResponse:
        """Update the NGO profile for the authenticated user."""
        profile = await self._ngo_repo.get_profile_by_ngo_id(user_id)
        if profile is None:
            raise NoProfileFoundException()

        # Extract only fields that were explicitly set (not None)
        update_fields = data.model_dump(exclude_unset=True)
        if update_fields:
            await self._ngo_repo.update_profile(user_id, **update_fields)

        # Return the full updated profile
        return await self.get_me(user_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _revoke_and_send_otp(
        self,
        *,
        user_id: uuid.UUID,
        email: str,
        org_name: str | None = None,
        purpose: str = _PURPOSE_EMAIL_VERIFICATION,
    ) -> None:
        """Revoke old tokens, create a new one, and send the OTP email."""
        await self._token_repo.revoke_open_tokens(user_id, purpose=purpose)

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
            purpose=purpose,
        )

        if purpose == _PURPOSE_PASSWORD_RESET:
            from app.common.services.notification_service import NotificationService
            await NotificationService.dispatch_password_recovery(email, otp_plain)
        else:
            from app.common.services.notification_service import NotificationService
            await NotificationService.dispatch_otp_verification(email, otp_plain, org_name or "your organisation")

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
        *,
        role: str,
    ) -> tuple[str, str]:
        """Create JWT access and refresh token pair via centralized generator."""
        from app.common.services.jwt_service import JwtService
        return JwtService.generate_tokens(user_id, role)

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
        purpose: str = _PURPOSE_EMAIL_VERIFICATION,
    ) -> None:
        """Enforce max OTPs per hour rate limit."""
        recent_count = await self._token_repo.count_recent_tokens(
            user_id, purpose=purpose,
        )
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

