"""Notification SQLAlchemy model.

Maps to the 'notifications' table in the database.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base_model import Base


class Notification(Base):
    """User notification record."""

    __tablename__ = "notifications"

    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    notification_type: Mapped[str] = mapped_column(
        ENUM(
            "task_assigned", "task_updated", "urgent_request",
            "disaster_alert", "system",
            name="notification_type", create_type=False,
        ),
        nullable=False,
    )
    related_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id", ondelete="SET NULL"), nullable=True
    )
    related_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("disaster_events.event_id", ondelete="SET NULL"), nullable=True
    )
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
