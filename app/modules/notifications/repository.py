"""Notification repository — data-access layer."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification


class NotificationRepository:
    """Handles all notification-related database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[Notification]:
        """Fetch notifications for a user, newest first."""
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)  # noqa: E712
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_unread(self, user_id: uuid.UUID) -> int:
        """Count unread notifications for a user."""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def mark_as_read(
        self,
        user_id: uuid.UUID,
        notification_ids: list[uuid.UUID],
    ) -> int:
        """Mark specific notifications as read. Returns count updated."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.notification_id.in_(notification_ids),
                Notification.is_read == False,  # noqa: E712
            )
            .values(is_read=True, read_at=now)
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all unread notifications as read for a user."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
            )
            .values(is_read=True, read_at=now)
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def get_by_id(
        self,
        notification_id: uuid.UUID,
    ) -> Notification | None:
        """Fetch a single notification by ID."""
        stmt = select(Notification).where(
            Notification.notification_id == notification_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
