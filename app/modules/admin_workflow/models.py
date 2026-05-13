"""SQLAlchemy models for disaster management workflow.

This module defines the four core models for the disaster management system:
- AdminUser: Admin accounts for disaster management personnel
- ThresholdBreachAlert: Threshold breach alerts from Data Collector Agent
- RiskAnalysis: Risk analysis results from Risk Analysis Agent
- PrecautionaryMeasure: Precautionary measures from Precautionary Agent
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_model import BaseModel


class AdminUser(BaseModel):
    """Admin user model for disaster management personnel.
    
    Represents authenticated administrators who can:
    - Acknowledge threshold breach alerts
    - Request risk analyses
    - Request and approve precautionary measures
    
    Maps to the 'admin_users' table in the database.
    """

    __tablename__ = "admin_users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    org_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'admin'"),
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    # Relationships
    acknowledged_alerts: Mapped[list[ThresholdBreachAlert]] = relationship(
        "ThresholdBreachAlert",
        back_populates="acknowledged_by_user",
        foreign_keys="ThresholdBreachAlert.acknowledged_by",
    )
    requested_analyses: Mapped[list[RiskAnalysis]] = relationship(
        "RiskAnalysis",
        back_populates="requested_by_user",
        foreign_keys="RiskAnalysis.requested_by",
    )
    requested_precautions: Mapped[list[PrecautionaryMeasure]] = relationship(
        "PrecautionaryMeasure",
        back_populates="requested_by_user",
        foreign_keys="PrecautionaryMeasure.requested_by",
    )
    approved_precautions: Mapped[list[PrecautionaryMeasure]] = relationship(
        "PrecautionaryMeasure",
        back_populates="approved_by_user",
        foreign_keys="PrecautionaryMeasure.approved_by",
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'super_admin')",
            name="admin_users_role_check",
        ),
    )


class ThresholdBreachAlert(BaseModel):
    """Threshold breach alert model.
    
    Represents alerts received from the Data Collector Agent when
    environmental sensor readings exceed predefined safety thresholds.
    
    Maps to the 'threshold_breach_alerts' table in the database.
    """

    __tablename__ = "threshold_breach_alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    sensor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    latitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 8),
        nullable=False,
    )
    longitude: Mapped[Decimal] = mapped_column(
        Numeric(11, 8),
        nullable=False,
    )
    location_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    province: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    current_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    threshold_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    breach_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    data_source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'NEW'"),
        index=True,
    )
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.user_id", name="fk_alerts_acknowledged_by"),
        nullable=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    # Relationships
    acknowledged_by_user: Mapped[AdminUser | None] = relationship(
        "AdminUser",
        back_populates="acknowledged_alerts",
        foreign_keys=[acknowledged_by],
    )
    risk_analyses: Mapped[list[RiskAnalysis]] = relationship(
        "RiskAnalysis",
        back_populates="alert",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "sensor_type IN ('temperature', 'rainfall', 'seismic', 'wind_speed', 'water_level')",
            name="alerts_sensor_type_check",
        ),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="alerts_severity_check",
        ),
        CheckConstraint(
            "status IN ('NEW', 'ACKNOWLEDGED', 'ANALYZING', 'RESOLVED')",
            name="alerts_status_check",
        ),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="alerts_latitude_check",
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="alerts_longitude_check",
        ),
    )


class RiskAnalysis(BaseModel):
    """Risk analysis model.
    
    Represents risk assessment results from the Risk Analysis Agent,
    including risk scores, disaster types, and recommended actions.
    
    Maps to the 'risk_analyses' table in the database.
    """

    __tablename__ = "risk_analyses"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "threshold_breach_alerts.alert_id",
            name="fk_risk_analyses_alert_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    risk_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    disaster_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    affected_area_km2: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    estimated_population_affected: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    confidence_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    analysis_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    detailed_analysis: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    recommended_actions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'PENDING'"),
        index=True,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.user_id", name="fk_risk_analyses_requested_by"),
        nullable=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    # Relationships
    alert: Mapped[ThresholdBreachAlert] = relationship(
        "ThresholdBreachAlert",
        back_populates="risk_analyses",
    )
    requested_by_user: Mapped[AdminUser | None] = relationship(
        "AdminUser",
        back_populates="requested_analyses",
        foreign_keys=[requested_by],
    )
    precautionary_measures: Mapped[list[PrecautionaryMeasure]] = relationship(
        "PrecautionaryMeasure",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="risk_analyses_risk_score_check",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="risk_analyses_confidence_score_check",
        ),
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="risk_analyses_risk_level_check",
        ),
        CheckConstraint(
            "disaster_type IN ('FLOOD', 'EARTHQUAKE', 'HEATWAVE', 'STORM', 'DROUGHT')",
            name="risk_analyses_disaster_type_check",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'FAILED')",
            name="risk_analyses_status_check",
        ),
    )


class PrecautionaryMeasure(BaseModel):
    """Precautionary measure model.
    
    Represents precautionary measures and action plans generated by
    the Precautionary Agent based on risk analysis results.
    
    Maps to the 'precautionary_measures' table in the database.
    """

    __tablename__ = "precautionary_measures"

    precaution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "risk_analyses.analysis_id",
            name="fk_precautionary_measures_analysis_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    disaster_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    overall_strategy: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    measures: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    timeline: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    estimated_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'PENDING'"),
        index=True,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.user_id", name="fk_precautionary_measures_requested_by"),
        nullable=True,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.user_id", name="fk_precautionary_measures_approved_by"),
        nullable=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )
    generated_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    # Relationships
    analysis: Mapped[RiskAnalysis] = relationship(
        "RiskAnalysis",
        back_populates="precautionary_measures",
    )
    requested_by_user: Mapped[AdminUser | None] = relationship(
        "AdminUser",
        back_populates="requested_precautions",
        foreign_keys=[requested_by],
    )
    approved_by_user: Mapped[AdminUser | None] = relationship(
        "AdminUser",
        back_populates="approved_precautions",
        foreign_keys=[approved_by],
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'GENERATED', 'APPROVED', 'IMPLEMENTED')",
            name="precautionary_measures_status_check",
        ),
    )

