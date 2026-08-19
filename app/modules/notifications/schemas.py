"""Notification Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NotificationType = Literal[
    "task_assigned", "task_updated", "urgent_request",
    "disaster_alert", "system",
]


class NotificationResponse(BaseModel):
    """Single notification item returned to frontend."""

    notification_id: uuid.UUID
    user_id: uuid.UUID | None = None
    title: str
    message: str | None = None
    notification_type: str
    related_task_id: uuid.UUID | None = None
    related_event_id: uuid.UUID | None = None
    changes: dict | list | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarkReadRequest(BaseModel):
    """Request to mark specific notifications as read."""

    notification_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="IDs of notifications to mark as read"
    )
