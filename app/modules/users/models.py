"""User SQLAlchemy model mapping to the 'users' table.

This model maps exactly to the existing Supabase 'users' table schema
including all columns, constraints, and relationships.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_model import BaseModel, SoftDeleteMixin


class User(BaseModel, SoftDeleteMixin):
    """Central authentication user model."""

    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        ENUM("ngo_user", "admin", name="user_role", create_type=False),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships — use string references to avoid circular imports
    ngo_profile: Mapped[NgoProfile | None] = relationship(
        "NgoProfile",
        back_populates="user",
        uselist=False,
        foreign_keys="NgoProfile.ngo_id",
    )
    verification_tokens: Mapped[list[AuthVerificationToken]] = relationship(
        "AuthVerificationToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list["AuthRefreshToken"]] = relationship(
        "AuthRefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    admin_profile: Mapped["AdminProfile"] = relationship(
        "AdminProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="AdminProfile.admin_id",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="AuditLog.user_id",
    )
