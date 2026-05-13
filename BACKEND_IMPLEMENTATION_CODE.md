# Backend Implementation Code
## Complete Python/FastAPI Code for Disaster Management Workflow

This document contains all the backend code files needed to implement the disaster management workflow.

---

## File Structure
```
F:\ClimasyncAI_backend\
├── app/
│   ├── modules/
│   │   ├── admin_workflow/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   ├── services.py
│   │   │   └── agent_client.py
│   │   └── admin/
│   │       ├── auth_routes.py (new)
│   │       └── auth_service.py (new)
├── migrations/
│   └── versions/
│       └── xxx_add_disaster_workflow_tables.py
└── .env.local
```

---

## 1. Database Migration Script

**File:** `migrations/versions/xxx_add_disaster_workflow_tables.py`

```python
"""Add disaster management workflow tables

Revision ID: xxx
Revises: previous_revision
Create Date: 2026-05-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'xxx'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade():
    # Create admin_users table
    op.create_table(
        'admin_users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('org_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='admin'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("role IN ('admin', 'super_admin')", name='admin_users_role_check')
    )
    op.create_index('idx_admin_users_email', 'admin_users', ['email'])
    op.create_index('idx_admin_users_role', 'admin_users', ['role'])

    # Create threshold_breach_alerts table
    op.create_table(
        'threshold_breach_alerts',
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('sensor_type', sa.String(50), nullable=False),
        sa.Column('latitude', sa.Numeric(10, 8), nullable=False),
        sa.Column('longitude', sa.Numeric(11, 8), nullable=False),
        sa.Column('location_name', sa.String(255), nullable=False),
        sa.Column('province', sa.String(100), nullable=False),
        sa.Column('current_value', sa.Numeric(10, 2), nullable=False),
        sa.Column('threshold_value', sa.Numeric(10, 2), nullable=False),
        sa.Column('breach_percentage', sa.Numeric(5, 2), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('data_source', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='NEW'),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('admin_users.user_id'), nullable=True),
        sa.Column('acknowledged_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("sensor_type IN ('temperature', 'rainfall', 'seismic', 'wind_speed', 'water_level')", name='alerts_sensor_type_check'),
        sa.CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name='alerts_severity_check'),
        sa.CheckConstraint("status IN ('NEW', 'ACKNOWLEDGED', 'ANALYZING', 'RESOLVED')", name='alerts_status_check')
    )
    op.create_index('idx_alerts_status', 'threshold_breach_alerts', ['status'])
    op.create_index('idx_alerts_severity', 'threshold_breach_alerts', ['severity'])
    op.create_index('idx_alerts_created_at', 'threshold_breach_alerts', [sa.text('created_at DESC')])
    op.create_index('idx_alerts_location', 'threshold_breach_alerts', ['latitude', 'longitude'])

    # Create risk_analyses table
    op.create_table(
        'risk_analyses',
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('threshold_breach_alerts.alert_id', ondelete='CASCADE'), nullable=False),
        sa.Column('risk_score', sa.Integer(), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=False),
        sa.Column('disaster_type', sa.String(50), nullable=False),
        sa.Column('affected_area_km2', sa.Numeric(10, 2), nullable=False),
        sa.Column('estimated_population_affected', sa.Integer(), nullable=False),
        sa.Column('confidence_score', sa.Integer(), nullable=False),
        sa.Column('analysis_summary', sa.Text(), nullable=False),
        sa.Column('detailed_analysis', postgresql.JSONB(), nullable=False),
        sa.Column('recommended_actions', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('admin_users.user_id'), nullable=True),
        sa.Column('requested_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("risk_score >= 0 AND risk_score <= 100", name='risk_analyses_risk_score_check'),
        sa.CheckConstraint("confidence_score >= 0 AND confidence_score <= 100", name='risk_analyses_confidence_score_check'),
        sa.CheckConstraint("risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name='risk_analyses_risk_level_check'),
        sa.CheckConstraint("disaster_type IN ('FLOOD', 'EARTHQUAKE', 'HEATWAVE', 'STORM', 'DROUGHT')", name='risk_analyses_disaster_type_check'),
        sa.CheckConstraint("status IN ('PENDING', 'COMPLETED', 'FAILED')", name='risk_analyses_status_check')
    )
    op.create_index('idx_risk_analyses_alert_id', 'risk_analyses', ['alert_id'])
    op.create_index('idx_risk_analyses_status', 'risk_analyses', ['status'])
    op.create_index('idx_risk_analyses_created_at', 'risk_analyses', [sa.text('created_at DESC')])

    # Create precautionary_measures table
    op.create_table(
        'precautionary_measures',
        sa.Column('precaution_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('risk_analyses.analysis_id', ondelete='CASCADE'), nullable=False),
        sa.Column('disaster_type', sa.String(50), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=False),
        sa.Column('overall_strategy', sa.Text(), nullable=False),
        sa.Column('measures', postgresql.JSONB(), nullable=False),
        sa.Column('timeline', postgresql.JSONB(), nullable=False),
        sa.Column('estimated_cost', sa.Numeric(15, 2), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('admin_users.user_id'), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('admin_users.user_id'), nullable=True),
        sa.Column('requested_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('generated_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('approved_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("status IN ('PENDING', 'GENERATED', 'APPROVED', 'IMPLEMENTED')", name='precautionary_measures_status_check')
    )
    op.create_index('idx_precautionary_analysis_id', 'precautionary_measures', ['analysis_id'])
    op.create_index('idx_precautionary_status', 'precautionary_measures', ['status'])
    op.create_index('idx_precautionary_created_at', 'precautionary_measures', [sa.text('created_at DESC')])


def downgrade():
    op.drop_table('precautionary_measures')
    op.drop_table('risk_analyses')
    op.drop_table('threshold_breach_alerts')
    op.drop_table('admin_users')
```

---

## 2. Models (SQLAlchemy)

**File:** `app/modules/admin_workflow/models.py`

```python
"""
Admin Workflow Models
SQLAlchemy models for disaster management workflow
"""

from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    org_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="admin")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    acknowledged_alerts = relationship("ThresholdBreachAlert", back_populates="acknowledged_by_user", foreign_keys="ThresholdBreachAlert.acknowledged_by")
    requested_analyses = relationship("RiskAnalysis", back_populates="requested_by_user", foreign_keys="RiskAnalysis.requested_by")
    requested_precautions = relationship("PrecautionaryMeasure", back_populates="requested_by_user", foreign_keys="PrecautionaryMeasure.requested_by")
    approved_precautions = relationship("PrecautionaryMeasure", back_populates="approved_by_user", foreign_keys="PrecautionaryMeasure.approved_by")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'super_admin')", name='admin_users_role_check'),
    )


class ThresholdBreachAlert(Base):
    __tablename__ = "threshold_breach_alerts"

    alert_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sensor_type = Column(String(50), nullable=False)
    latitude = Column(Numeric(10, 8), nullable=False)
    longitude = Column(Numeric(11, 8), nullable=False)
    location_name = Column(String(255), nullable=False)
    province = Column(String(100), nullable=False)
    current_value = Column(Numeric(10, 2), nullable=False)
    threshold_value = Column(Numeric(10, 2), nullable=False)
    breach_percentage = Column(Numeric(5, 2), nullable=False)
    severity = Column(String(20), nullable=False)
    data_source = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="NEW", index=True)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.user_id"), nullable=True)
    acknowledged_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    acknowledged_by_user = relationship("AdminUser", back_populates="acknowledged_alerts", foreign_keys=[acknowledged_by])
    risk_analyses = relationship("RiskAnalysis", back_populates="alert", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("sensor_type IN ('temperature', 'rainfall', 'seismic', 'wind_speed', 'water_level')", name='alerts_sensor_type_check'),
        CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name='alerts_severity_check'),
        CheckConstraint("status IN ('NEW', 'ACKNOWLEDGED', 'ANALYZING', 'RESOLVED')", name='alerts_status_check'),
    )


class RiskAnalysis(Base):
    __tablename__ = "risk_analyses"

    analysis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("threshold_breach_alerts.alert_id", ondelete="CASCADE"), nullable=False, index=True)
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    disaster_type = Column(String(50), nullable=False)
    affected_area_km2 = Column(Numeric(10, 2), nullable=False)
    estimated_population_affected = Column(Integer, nullable=False)
    confidence_score = Column(Integer, nullable=False)
    analysis_summary = Column(Text, nullable=False)
    detailed_analysis = Column(JSONB, nullable=False)
    recommended_actions = Column(JSONB, nullable=False)
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    requested_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.user_id"), nullable=True)
    requested_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    completed_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    alert = relationship("ThresholdBreachAlert", back_populates="risk_analyses")
    requested_by_user = relationship("AdminUser", back_populates="requested_analyses", foreign_keys=[requested_by])
    precautionary_measures = relationship("PrecautionaryMeasure", back_populates="analysis", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name='risk_analyses_risk_score_check'),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 100", name='risk_analyses_confidence_score_check'),
        CheckConstraint("risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name='risk_analyses_risk_level_check'),
        CheckConstraint("disaster_type IN ('FLOOD', 'EARTHQUAKE', 'HEATWAVE', 'STORM', 'DROUGHT')", name='risk_analyses_disaster_type_check'),
        CheckConstraint("status IN ('PENDING', 'COMPLETED', 'FAILED')", name='risk_analyses_status_check'),
    )


class PrecautionaryMeasure(Base):
    __tablename__ = "precautionary_measures"

    precaution_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("risk_analyses.analysis_id", ondelete="CASCADE"), nullable=False, index=True)
    disaster_type = Column(String(50), nullable=False)
    risk_level = Column(String(20), nullable=False)
    overall_strategy = Column(Text, nullable=False)
    measures = Column(JSONB, nullable=False)
    timeline = Column(JSONB, nullable=False)
    estimated_cost = Column(Numeric(15, 2), nullable=True)
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    requested_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.user_id"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.user_id"), nullable=True)
    requested_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    generated_at = Column(TIMESTAMP, nullable=True)
    approved_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    analysis = relationship("RiskAnalysis", back_populates="precautionary_measures")
    requested_by_user = relationship("AdminUser", back_populates="requested_precautions", foreign_keys=[requested_by])
    approved_by_user = relationship("AdminUser", back_populates="approved_precautions", foreign_keys=[approved_by])

    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'GENERATED', 'APPROVED', 'IMPLEMENTED')", name='precautionary_measures_status_check'),
    )
```

---

## 3. Pydantic Schemas

**File:** `app/modules/admin_workflow/schemas.py`

```python
"""
Admin Workflow Schemas
Pydantic models for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal


# ============================================================================
# Admin Authentication Schemas
# ============================================================================

class AdminCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    org_name: str = Field(..., min_length=1, max_length=255)
    full_name: str = Field(..., min_length=1, max_length=255)


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminAuthResponse(BaseModel):
    user_id: UUID
    email: str
    org_name: str
    role: str
    access_token: str
    refresh_token: str


# ============================================================================
# Threshold Breach Alert Schemas
# ============================================================================

class LocationData(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    location_name: str
    province: str


class ThresholdAlertCreate(BaseModel):
    sensor_type: str = Field(..., pattern="^(temperature|rainfall|seismic|wind_speed|water_level)$")
    location: LocationData
    current_value: float
    threshold_value: float
    breach_percentage: float
    severity: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    data_source: str


class ThresholdAlertResponse(BaseModel):
    alert_id: UUID
    sensor_type: str
    location: LocationData
    current_value: float
    threshold_value: float
    breach_percentage: float
    severity: str
    timestamp: datetime
    data_source: str
    status: str

    class Config:
        from_attributes = True


class ThresholdAlertListResponse(BaseModel):
    alerts: List[ThresholdAlertResponse]
    total_count: int
    unacknowledged_count: int


# ============================================================================
# Risk Analysis Schemas
# ============================================================================

class SensorData(BaseModel):
    sensor_type: str
    current_value: float
    threshold_value: float


class RiskAnalysisRequest(BaseModel):
    alert_id: UUID
    location: LocationData
    sensor_data: SensorData
    historical_data: Optional[Dict[str, Any]] = None


class DetailedAnalysis(BaseModel):
    severity_factors: List[str]
    vulnerability_assessment: str
    historical_comparison: str
    prediction_model_output: Dict[str, Any]


class RiskAnalysisResponse(BaseModel):
    analysis_id: UUID
    alert_id: UUID
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    disaster_type: str
    affected_area_km2: float
    estimated_population_affected: int
    confidence_score: int = Field(..., ge=0, le=100)
    analysis_summary: str
    detailed_analysis: DetailedAnalysis
    recommended_actions: List[str]
    timestamp: datetime
    status: str

    class Config:
        from_attributes = True


class RiskAnalysisListResponse(BaseModel):
    analyses: List[RiskAnalysisResponse]
    total_count: int


# ============================================================================
# Precautionary Measures Schemas
# ============================================================================

class RiskAnalysisData(BaseModel):
    risk_score: int
    risk_level: str
    disaster_type: str
    affected_area_km2: float
    estimated_population_affected: int


class PrecautionaryRequest(BaseModel):
    analysis_id: UUID
    risk_analysis_data: RiskAnalysisData
    location: LocationData


class RequiredResources(BaseModel):
    personnel: int
    vehicles: int
    supplies: List[str]


class PrecautionaryMeasureDetail(BaseModel):
    measure_id: UUID
    category: str
    priority: str
    title: str
    description: str
    target_population: int
    estimated_duration_hours: int
    required_resources: RequiredResources
    implementation_steps: List[str]


class Timeline(BaseModel):
    immediate_actions: List[str]
    short_term_actions: List[str]
    long_term_actions: List[str]


class PrecautionaryResponse(BaseModel):
    precaution_id: UUID
    analysis_id: UUID
    disaster_type: str
    risk_level: str
    measures: List[PrecautionaryMeasureDetail]
    overall_strategy: str
    timeline: Timeline
    estimated_cost: Optional[float]
    generated_at: datetime
    status: str

    class Config:
        from_attributes = True


class PrecautionaryListResponse(BaseModel):
    precautions: List[PrecautionaryResponse]
    total_count: int


# ============================================================================
# Generic Response Schemas
# ============================================================================

class SuccessResponse(BaseModel):
    success: bool


class StatusResponse(BaseModel):
    id: UUID
    status: str
```

---

## 4. Agent Client (HTTP Communication)

**File:** `app/modules/admin_workflow/agent_client.py`

```python
"""
Agent Client
HTTP client for communicating with microservice agents
"""

import httpx
import logging
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentClient:
    """Client for communicating with external agent microservices"""

    def __init__(self):
        self.risk_analysis_url = settings.RISK_ANALYSIS_AGENT_URL
        self.precautionary_url = settings.PRECAUTIONARY_AGENT_URL
        self.timeout = 60.0

    async def request_risk_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send risk analysis request to Risk Analysis Agent
        
        Args:
            data: Risk analysis request data
            
        Returns:
            Risk analysis result from agent
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.risk_analysis_url}/api/analyze",
                    json=data
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Risk Analysis Agent request failed: {str(e)}")
            raise Exception(f"Failed to communicate with Risk Analysis Agent: {str(e)}")

    async def request_precautionary_measures(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send precautionary measures request to Precautionary Agent
        
        Args:
            data: Precautionary measures request data
            
        Returns:
            Precautionary measures result from agent
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.precautionary_url}/api/generate-measures",
                    json=data
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Precautionary Agent request failed: {str(e)}")
            raise Exception(f"Failed to communicate with Precautionary Agent: {str(e)}")


# Singleton instance
agent_client = AgentClient()
```

---

**(Continued in next message due to length...)**
