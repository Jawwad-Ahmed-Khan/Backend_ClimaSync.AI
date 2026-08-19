"""Notification service — business logic layer."""

import uuid

from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import NotificationResponse


class NotificationService:
    """Encapsulates notification business rules."""

    def __init__(self, repo: NotificationRepository) -> None:
        self._repo = repo

    async def list_notifications(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[NotificationResponse]:
        """Return notifications for the authenticated user."""
        rows = await self._repo.list_for_user(
            user_id,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
        )
        return [NotificationResponse.model_validate(r) for r in rows]

    async def count_unread(self, user_id: uuid.UUID) -> int:
        """Return count of unread notifications."""
        return await self._repo.count_unread(user_id)

    async def mark_as_read(
        self,
        user_id: uuid.UUID,
        notification_ids: list[uuid.UUID],
    ) -> dict[str, str | int]:
        """Mark specific notifications as read."""
        count = await self._repo.mark_as_read(user_id, notification_ids)
        return {"message": f"Marked {count} notification(s) as read", "count": count}

    async def mark_all_as_read(self, user_id: uuid.UUID) -> dict[str, str | int]:
        """Mark all notifications as read."""
        count = await self._repo.mark_all_as_read(user_id)
        return {"message": f"Marked {count} notification(s) as read", "count": count}
