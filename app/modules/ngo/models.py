"""NGO profile and resource SQLAlchemy models.

Maps to the existing 'ngo_profiles' and 'ngo_resources' tables
in the Supabase database.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_model import BaseModel, SoftDeleteMixin


class NgoProfile(BaseModel, SoftDeleteMixin):
    """NGO organisation profile model."""

    __tablename__ = "ngo_profiles"

    ngo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    org_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    org_email: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    registration_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )
    head_of_operations: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    base_district: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    base_province: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    service_radius_km: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("10"),
    )
    verification_status: Mapped[str] = mapped_column(
        ENUM("pending", "verified", "rejected", "suspended", name="verification_status", create_type=False),
        nullable=False,
        server_default=text("'pending'::verification_status"),
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    suspended_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    rating: Mapped[Decimal] = mapped_column(
        Numeric(2, 1),
        nullable=False,
        server_default=text("0.0"),
    )

    # Relationships — string references avoid circular imports
    user: Mapped[User] = relationship(
        "User",
        back_populates="ngo_profile",
        foreign_keys=[ngo_id],
    )
    resources: Mapped[NgoResource | None] = relationship(
        "NgoResource",
        back_populates="ngo_profile",
        uselist=False,
        cascade="all, delete-orphan",
    )


class NgoResource(BaseModel):
    """NGO operational resources (1:1 with ngo_profiles)."""

    __tablename__ = "ngo_resources"

    ngo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ngo_profiles.ngo_id", ondelete="CASCADE"),
        primary_key=True,
    )
    ambulances: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    rescue_boats: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    trucks: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    four_wheel_vehicles: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    cranes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    doctors: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    paramedics: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    rescue_divers: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    volunteers_available: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    food_packets_capacity: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    shelter_capacity: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )

    # Relationships
    ngo_profile: Mapped[NgoProfile] = relationship(
        "NgoProfile",
        back_populates="resources",
    )
