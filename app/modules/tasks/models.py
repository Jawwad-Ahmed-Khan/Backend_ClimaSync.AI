"""Tasks and operational assignments SQLAlchemy models.

Maps to the 'tasks' and 'task_status_history' tables in the database.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_model import BaseModel, SoftDeleteMixin

try:
    from geoalchemy2 import Geography
except ImportError:
    # Safe fallback if geoalchemy2 isn't installed
    class Geography(Text):
        def __init__(self, geometry_type="GEOMETRY", srid=4326, **kwargs):
            super().__init__()


class Task(BaseModel, SoftDeleteMixin):
    """Operational task assigned to an NGO."""

    __tablename__ = "tasks"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("disaster_events.event_id", ondelete="RESTRICT"), nullable=True
    )
    task_label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    task_type: Mapped[str] = mapped_column(
        ENUM("ambulance", "boat", "medical", "food", "evacuation", "shelter", name="task_type", create_type=False),
        nullable=False,
    )
    required_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[str] = mapped_column(
        ENUM("low", "medium", "high", "critical", name="task_priority", create_type=False),
        nullable=False,
        server_default="medium"
    )
    
    target_location: Mapped[str | None] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    target_location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    status: Mapped[str] = mapped_column(
        ENUM("draft", "pending_approval", "unallocated", "pending_acceptance", "assigned", "in_progress", "completed", name="task_status", create_type=False),
        nullable=False,
        server_default="draft"
    )
    
    created_by_type: Mapped[str] = mapped_column(String(10), nullable=False, server_default="admin")
    admin_approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    assigned_ngo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ngo_profiles.ngo_id", ondelete="SET NULL"), nullable=True
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    estimated_duration_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    proof_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    # Relationships mapping
    history: Mapped[list[TaskStatusHistory]] = relationship(
        "TaskStatusHistory", back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )


class TaskStatusHistory(BaseModel):
    """Immutable log of task state transitions."""

    __tablename__ = "task_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False
    )
    old_status: Mapped[str | None] = mapped_column(
        ENUM("draft", "pending_approval", "unallocated", "pending_acceptance", "assigned", "in_progress", "completed", name="task_status", create_type=False),
        nullable=True
    )
    new_status: Mapped[str] = mapped_column(
        ENUM("draft", "pending_approval", "unallocated", "pending_acceptance", "assigned", "in_progress", "completed", name="task_status", create_type=False),
        nullable=False
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    # Relationships
    task: Mapped[Task] = relationship("Task", back_populates="history")
