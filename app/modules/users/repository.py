"""User repository — data access for the users table.

Provides query methods needed by the auth service during registration.
"""

import uuid
from datetime import datetime

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


class UserRepository:
    """Data access for the users table."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with async session."""
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        """Find an active (non-deleted) user by email."""
        stmt = select(User).where(
            and_(
                User.email == email,
                User.deleted_at.is_(None),
            ),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        role: str,
    ) -> User:
        """Insert a new user and return it with generated fields."""
        user = User(
            email=email,
            password_hash=password_hash,
            role=role,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def mark_email_verified(
        self,
        user_id: uuid.UUID,
        verified_at: datetime,
    ) -> None:
        """Set email_verified=True and email_verified_at on a user."""
        stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(
                email_verified=True,
                email_verified_at=verified_at,
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
