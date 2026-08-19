"""Notification module dependency injection."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.service import NotificationService


def get_notification_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationRepository:
    """Provide a NotificationRepository instance."""
    return NotificationRepository(session)


def get_notification_service(
    repo: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> NotificationService:
    """Provide a NotificationService."""
    return NotificationService(repo)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
