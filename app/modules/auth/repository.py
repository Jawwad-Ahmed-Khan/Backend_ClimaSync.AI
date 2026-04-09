"""Auth repository — data access for verification tokens and refresh tokens.

Contains ONLY database query logic. No business rules or decisions.
Returns model instances, None, or scalar values.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AuthRefreshToken, AuthVerificationToken

_PURPOSE_EMAIL_VERIFICATION = "email_verification"
_PURPOSE_PASSWORD_RESET = "password_reset"


class VerificationTokenRepository:
    """Data access for auth_verification_tokens table."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with async session."""
        self.session = session

    async def create_token(
        self,
        *,
        user_id: uuid.UUID,
        email: str,
        token_hash: str,
        expires_at: datetime,
        max_attempts: int,
        purpose: str = _PURPOSE_EMAIL_VERIFICATION,
    ) -> AuthVerificationToken:
        """Insert a new verification token and return it."""
        token = AuthVerificationToken(
            user_id=user_id,
            email=email,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=expires_at,
            max_attempts=max_attempts,
        )
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def find_open_token_by_email(
        self,
        email: str,
        purpose: str = _PURPOSE_EMAIL_VERIFICATION,
    ) -> AuthVerificationToken | None:
        """Find the most recent open (unused, unrevoked) token for an email."""
        stmt = (
            select(AuthVerificationToken)
            .where(
                and_(
                    AuthVerificationToken.email == email,
                    AuthVerificationToken.purpose == purpose,
                    AuthVerificationToken.used_at.is_(None),
                    AuthVerificationToken.revoked_at.is_(None),
                ),
            )
            .order_by(AuthVerificationToken.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_attempts(
        self,
        token_id: uuid.UUID,
    ) -> None:
        """Increment the attempts_count for a token."""
        stmt = (
            update(AuthVerificationToken)
            .where(
                AuthVerificationToken.verification_token_id == token_id,
            )
            .values(
                attempts_count=AuthVerificationToken.attempts_count + 1,
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def mark_used(self, token_id: uuid.UUID) -> None:
        """Set used_at = now() on a token."""
        stmt = (
            update(AuthVerificationToken)
            .where(
                AuthVerificationToken.verification_token_id == token_id,
            )
            .values(used_at=func.now())
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def revoke_open_tokens(
        self,
        user_id: uuid.UUID,
        purpose: str = _PURPOSE_EMAIL_VERIFICATION,
    ) -> None:
        """Revoke all open tokens for a user+purpose."""
        stmt = (
            update(AuthVerificationToken)
            .where(
                and_(
                    AuthVerificationToken.user_id == user_id,
                    AuthVerificationToken.purpose == purpose,
                    AuthVerificationToken.used_at.is_(None),
                    AuthVerificationToken.revoked_at.is_(None),
                ),
            )
            .values(revoked_at=func.now())
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def count_recent_tokens(
        self,
        user_id: uuid.UUID,
        purpose: str = _PURPOSE_EMAIL_VERIFICATION,
        hours: int = 1,
    ) -> int:
        """Count tokens created in the last N hours for rate limiting."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(func.count())
            .select_from(AuthVerificationToken)
            .where(
                and_(
                    AuthVerificationToken.user_id == user_id,
                    AuthVerificationToken.purpose == purpose,
                    AuthVerificationToken.created_at > cutoff,
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()


class RefreshTokenRepository:
    """Data access for auth_refresh_tokens table."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with async session."""
        self.session = session

    async def create_token(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthRefreshToken:
        """Insert a new refresh token and return it."""
        token = AuthRefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def find_active_by_hash(
        self,
        token_hash: str,
    ) -> AuthRefreshToken | None:
        """Find a non-revoked refresh token by its SHA-256 hash."""
        stmt = (
            select(AuthRefreshToken)
            .where(
                and_(
                    AuthRefreshToken.token_hash == token_hash,
                    AuthRefreshToken.revoked_at.is_(None),
                ),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_token(
        self,
        token_id: uuid.UUID,
        reason: str = "token_rotated",
    ) -> None:
        """Revoke a single refresh token."""
        stmt = (
            update(AuthRefreshToken)
            .where(AuthRefreshToken.refresh_token_id == token_id)
            .values(revoked_at=func.now(), revoke_reason=reason)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def revoke_all_user_tokens(
        self,
        user_id: uuid.UUID,
        reason: str = "password_changed",
    ) -> None:
        """Revoke all active refresh tokens for a user."""
        stmt = (
            update(AuthRefreshToken)
            .where(
                and_(
                    AuthRefreshToken.user_id == user_id,
                    AuthRefreshToken.revoked_at.is_(None),
                ),
            )
            .values(revoked_at=func.now(), revoke_reason=reason)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def update_last_used(
        self,
        token_id: uuid.UUID,
    ) -> None:
        """Update the last_used_at timestamp on a refresh token."""
        stmt = (
            update(AuthRefreshToken)
            .where(AuthRefreshToken.refresh_token_id == token_id)
            .values(last_used_at=func.now())
        )
        await self.session.execute(stmt)
        await self.session.flush()
