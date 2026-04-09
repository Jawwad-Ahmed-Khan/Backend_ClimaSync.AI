"""User repository — data access for the users table.

Provides query methods needed by the auth service during registration,
login, and password management.
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

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Retrieve a user by primary key (non-deleted only)."""
        stmt = select(User).where(
            and_(
                User.user_id == user_id,
                User.deleted_at.is_(None),
            ),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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

    async def update_last_login(
        self,
        user_id: uuid.UUID,
        logged_in_at: datetime,
    ) -> None:
        """Record the timestamp of the most recent successful login."""
        stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(last_login_at=logged_in_at)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def update_password(
        self,
        user_id: uuid.UUID,
        new_hash: str,
        changed_at: datetime,
    ) -> None:
        """Update a user's password hash and password_changed_at timestamp."""
        stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(
                password_hash=new_hash,
                password_changed_at=changed_at,
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

