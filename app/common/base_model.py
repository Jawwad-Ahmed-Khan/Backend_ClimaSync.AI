"""SQLAlchemy base model with timestamp and soft-delete mixins.

All ORM models inherit from BaseModel which provides created_at
and updated_at. Models with soft-delete also mix in SoftDeleteMixin.

NOTE: The existing database uses entity-specific primary key names
(user_id, ngo_id, etc.) rather than a generic 'id'. Each model
defines its own PK column. BaseModel provides only the timestamps.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimestampMixin:
    """Provides created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Provides deleted_at column for soft-delete support."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Check whether this record has been soft-deleted."""
        return self.deleted_at is not None


class BaseModel(Base, TimestampMixin):
    """Abstract base model with timestamps.

    All application models should inherit from this class.
    Each model defines its own primary key matching the existing DB schema.
    """

    __abstract__ = True
