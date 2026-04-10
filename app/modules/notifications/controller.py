"""Notification controller — HTTP endpoints for user notifications."""

import uuid

from fastapi import APIRouter, Query

from app.common.base_schemas import MessageResponse
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.notifications.dependencies import NotificationServiceDep
from app.modules.notifications.schemas import (
    MarkReadRequest,
    NotificationResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="List notifications for current user",
    description="Returns notifications newest first. Use unread_only=true to filter.",
)
async def list_notifications(
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
) -> list[NotificationResponse]:
    """Fetch notifications for the authenticated user."""
    return await service.list_notifications(
        current_user.user_id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )


@router.get(
    "/unread-count",
    summary="Get unread notification count",
)
async def unread_count(
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
):
    """Return the current unread count."""
    count = await service.count_unread(current_user.user_id)
    return {"unread_count": count}


@router.post(
    "/mark-read",
    response_model=MessageResponse,
    summary="Mark specific notifications as read",
)
async def mark_read(
    data: MarkReadRequest,
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
) -> MessageResponse:
    """Mark selected notifications as read."""
    result = await service.mark_as_read(current_user.user_id, data.notification_ids)
    return MessageResponse(message=result["message"])


@router.post(
    "/read-all",
    response_model=MessageResponse,
    summary="Mark all notifications as read",
)
async def mark_all_read(
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
) -> MessageResponse:
    """Mark all notifications as read for the current user."""
    result = await service.mark_all_as_read(current_user.user_id)
    return MessageResponse(message=result["message"])
