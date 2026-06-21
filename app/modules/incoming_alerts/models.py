"""SQLAlchemy model for incoming breach alerts from the Data Collection Service.

Maps to the 'incoming_alerts' table which persists every payload received
at POST /api/v1/alerts/incoming before it is broadcast over WebSockets.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base_model import BaseModel


class IncomingAlert(BaseModel):
    """Raw breach payload persisted as received from the Data Collection Service."""

    __tablename__ = "incoming_alerts"

    # Primary key — the breach_id provided by the collection service
    breach_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Source metadata
    source_api: Mapped[str] = mapped_column(String(50), nullable=False)
    disaster_kind: Mapped[str] = mapped_column(String(50), nullable=False)

    # Location
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Metrics
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    breach_severity: Mapped[str] = mapped_column(String(20), nullable=False)

    # Timing
    observation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_forecast: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    forecast_horizon_h: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Source-specific foreign keys (nullable — only one present per row)
    seismic_event_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    weather_location_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gauge_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Timestamp when our backend received the payload
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
