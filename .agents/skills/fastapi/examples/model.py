"""
Example: SQLAlchemy ORM Model
==============================
Reference implementation of a SQLAlchemy 2.0 async model with typed columns,
mixins (TimestampMixin, SoftDeleteMixin), relationships, and indexes.

Location: app/modules/<module_name>/models.py
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_model import BaseModel, SoftDeleteMixin


# ─── User Model ──────────────────────────────────────────────────────────────


class User(BaseModel, SoftDeleteMixin):
    """User account model.

    Inherits:
        BaseModel: UUID primary key + created_at/updated_at timestamps.
        SoftDeleteMixin: deleted_at column for soft-delete support.
    """

    __tablename__ = "users"

    # ── Core fields ──────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="user",
        server_default="user",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        server_default="true",
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────────────────
    items: Mapped[list["Item"]] = relationship(
        "Item",
        back_populates="owner",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # ── Table configuration ──────────────────────────────────────────────
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        {"comment": "User accounts table"},
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email!r})>"


# ─── Item Model ──────────────────────────────────────────────────────────────


class Item(BaseModel):
    """Domain item model — example of a child entity with a foreign key.

    Inherits:
        BaseModel: UUID primary key + created_at/updated_at timestamps.
    """

    __tablename__ = "items"

    # ── Core fields ──────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    # ── Foreign keys ─────────────────────────────────────────────────────
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Relationships ────────────────────────────────────────────────────
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="items",
        lazy="joined",
    )

    # ── Table configuration ──────────────────────────────────────────────
    __table_args__ = (
        Index("ix_items_owner_status", "owner_id", "status"),
        {"comment": "Domain items table"},
    )

    def __repr__(self) -> str:
        return f"<Item(id={self.id}, title={self.title!r})>"
