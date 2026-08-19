"""Risk Analysis SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base_model import BaseModel


class RiskAnalysis(BaseModel):
    """Stores high-fidelity risk assessment reports from the AI Agent."""

    __tablename__ = "risk_analyses"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.alert_id", ondelete="CASCADE"), nullable=False
    )
    
    # Core scoring
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False) # Store rounded score
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Metadata
    disaster_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="completed")
    
    # Metrics extracted for quick access
    affected_area_km2: Mapped[Decimal] = mapped_column(Numeric, nullable=False, server_default=text("0"))
    estimated_population_affected: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    
    # Large payloads
    analysis_summary: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_analysis: Mapped[dict] = mapped_column(JSONB, nullable=False)
    recommended_actions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    
    # Audit
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
