"""Pydantic schemas for disaster management workflow.

This module defines request and response schemas for:
- Admin authentication (create account, login)
- Threshold breach alerts (create, retrieve, acknowledge)
- Risk analysis (request, retrieve, poll)
- Precautionary measures (request, retrieve, approve, poll)

All schemas use Pydantic v2 with Field validators and ConfigDict.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ============================================================================
# Request Schemas - Task 4.1
# ============================================================================

# --- Admin Authentication ---


class AdminCreateRequest(BaseModel):
    """Request schema for creating a new admin account.
    
    Validates:
    - Email format (EmailStr)
    - Password length (8-72 characters per bcrypt limits)
    - Organization name and full name presence
    """

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    org_name: str = Field(..., min_length=1, max_length=255)
    full_name: str = Field(..., min_length=1, max_length=255)


class AdminLoginRequest(BaseModel):
    """Request schema for admin login."""

    email: EmailStr
    password: str


# --- Location Data (Reusable) ---


class LocationData(BaseModel):
    """Location data with coordinate validation.
    
    Validates:
    - Latitude: -90 to 90 degrees
    - Longitude: -180 to 180 degrees
    """

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    location_name: str = Field(..., min_length=1, max_length=255)
    province: str = Field(..., min_length=1, max_length=100)


# --- Threshold Alerts ---


class ThresholdAlertCreate(BaseModel):
    """Request schema for creating a threshold breach alert.
    
    Sent by the Data Collector Agent when sensor readings exceed thresholds.
    
    Validates:
    - sensor_type enum (temperature, rainfall, seismic, wind_speed, water_level)
    - severity enum (LOW, MEDIUM, HIGH, CRITICAL)
    - Location coordinates via LocationData
    """

    sensor_type: Literal["temperature", "rainfall", "seismic", "wind_speed", "water_level"]
    location: LocationData
    current_value: float
    threshold_value: float
    breach_percentage: float
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    data_source: str = Field(..., min_length=1, max_length=255)


class IncomingBreachPayload(BaseModel):
    """Request schema for incoming breach alerts from Data Collection Service.
    
    This schema supports the extended alert format with additional fields for
    different disaster types (earthquakes, floods, weather events).
    
    Validates:
    - Core identifiers (breach_id, source_api, disaster_kind)
    - Location data with coordinates
    - Metrics (observed_value, threshold_value, breach_severity)
    - Timing (observation_time, detected_at, is_forecast, forecast_horizon_h)
    - Specific API foreign keys (seismic_event_id, weather_location_id, gauge_id)
    """

    # Core Identifiers
    breach_id: str = Field(..., description="Unique UUID from the Collection Database")
    source_api: str = Field(..., description="'usgs', 'open_meteo', or 'google_flood_hub'")
    disaster_kind: str = Field(..., description="'earthquake', 'flood', 'heatwave', 'heavy_rain', etc.")
    
    # Location Data
    location_name: str | None = Field(None, description="Human readable city/district name")
    district: str | None = Field(None, description="Pakistan district")
    province: str | None = Field(None, description="Pakistan province enum string")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    
    # Metrics
    metric_name: str = Field(..., description="The type of reading (e.g., 'magnitude', 'temp_max_c')")
    observed_value: float = Field(..., description="The actual reading or forecasted value")
    threshold_value: float = Field(..., description="The limit that was crossed")
    unit: str = Field(..., description="Unit of measurement ('richter', 'celsius', 'mm', 'percent')")
    breach_severity: str = Field(..., description="'watch', 'warning', 'emergency', or 'extreme'")
    
    # Timing
    observation_time: datetime = Field(..., description="When the event happens (or is forecasted to happen)")
    detected_at: datetime = Field(..., description="When the collection service detected the breach")
    is_forecast: bool = Field(False, description="True if this is a future prediction")
    forecast_horizon_h: int | None = Field(None, description="Hours in the future (if is_forecast is true)")
    
    # Specific API Foreign Keys (At least one will be present depending on source_api)
    seismic_event_id: str | None = Field(None, description="USGS specific event ID")
    weather_location_id: str | None = Field(None, description="Open-Meteo internal location ID")
    gauge_id: str | None = Field(None, description="Google Flood Hub specific river gauge ID")


# --- Risk Analysis ---


class SensorData(BaseModel):
    """Sensor data for risk analysis request."""

    sensor_type: str = Field(..., min_length=1, max_length=50)
    current_value: float
    threshold_value: float


class RiskAnalysisRequest(BaseModel):
    """Request schema for requesting risk analysis.
    
    Sent to the Risk Analysis Agent to assess disaster risk.
    """

    alert_id: UUID
    location: LocationData
    sensor_data: SensorData
    historical_data: dict | None = None


# --- Precautionary Measures ---


class RiskAnalysisData(BaseModel):
    """Risk analysis data for precautionary measures request.
    
    Validates:
    - risk_score: 0-100
    """

    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str = Field(..., min_length=1, max_length=20)
    disaster_type: str = Field(..., min_length=1, max_length=50)
    affected_area_km2: float
    estimated_population_affected: int


class PrecautionaryRequest(BaseModel):
    """Request schema for requesting precautionary measures.
    
    Sent to the Precautionary Agent to generate action plans.
    """

    analysis_id: UUID
    risk_analysis_data: RiskAnalysisData
    location: LocationData


# ============================================================================
# Response Schemas - Task 4.2
# ============================================================================

# --- Admin Authentication ---


class AdminAuthResponse(BaseModel):
    """Response schema for admin authentication (create/login).
    
    Returns user details and JWT tokens for immediate authentication.
    """

    user_id: UUID
    email: str
    org_name: str
    role: str
    access_token: str
    refresh_token: str


# --- Threshold Alerts ---


class ThresholdAlertResponse(BaseModel):
    """Response schema for a single threshold breach alert."""

    alert_id: UUID
    sensor_type: str
    latitude: Decimal
    longitude: Decimal
    location_name: str
    province: str
    current_value: Decimal
    threshold_value: Decimal
    breach_percentage: Decimal
    severity: str
    data_source: str
    status: str
    acknowledged_by: UUID | None = None
    acknowledged_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ThresholdAlertListResponse(BaseModel):
    """Response schema for list of threshold breach alerts.
    
    Includes:
    - List of alerts
    - Total count (all alerts matching filters)
    - Unacknowledged count (alerts with status NEW)
    """

    alerts: list[ThresholdAlertResponse]
    total_count: int
    unacknowledged_count: int


class AlertCreatedResponse(BaseModel):
    """Response schema for alert creation endpoint.
    
    Returns alert_id and status to confirm successful creation.
    """

    alert_id: UUID
    status: str
    created_at: datetime


# --- Risk Analysis ---


class RiskAnalysisResponse(BaseModel):
    """Response schema for a single risk analysis.
    
    Validates:
    - risk_score: 0-100
    - confidence_score: 0-100
    
    Note: detailed_analysis and recommended_actions are stored as JSONB in the database
    and returned as dicts to preserve the flexible structure from the Risk Analysis Agent.
    """

    analysis_id: UUID
    alert_id: UUID
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    disaster_type: str
    affected_area_km2: Decimal
    estimated_population_affected: int
    confidence_score: int = Field(..., ge=0, le=100)
    analysis_summary: str
    detailed_analysis: dict  # JSONB field - flexible structure from agent
    recommended_actions: dict  # JSONB field - flexible structure from agent
    status: str
    requested_by: UUID | None = None
    requested_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskAnalysisListResponse(BaseModel):
    """Response schema for list of risk analyses."""

    analyses: list[RiskAnalysisResponse]
    total_count: int


# --- Precautionary Measures ---


class RequiredResources(BaseModel):
    """Required resources for a precautionary measure."""

    personnel: int
    vehicles: int
    supplies: list[str]


class PrecautionaryMeasureDetail(BaseModel):
    """Detailed precautionary measure with implementation steps.
    
    Represents a single actionable measure from the Precautionary Agent.
    """

    measure_id: UUID
    category: str
    priority: str
    title: str
    description: str
    target_population: int
    estimated_duration_hours: int
    required_resources: RequiredResources
    implementation_steps: list[str]


class Timeline(BaseModel):
    """Timeline for implementing precautionary measures.
    
    Organized into:
    - Immediate actions (0-6 hours)
    - Short-term actions (6-24 hours)
    - Long-term actions (24+ hours)
    """

    immediate_actions: list[str]
    short_term_actions: list[str]
    long_term_actions: list[str]


class PrecautionaryResponse(BaseModel):
    """Response schema for a single precautionary measure.
    
    Note: measures and timeline are stored as JSONB in the database and returned
    as dicts to preserve the flexible structure from the Precautionary Agent.
    """

    precaution_id: UUID
    analysis_id: UUID
    disaster_type: str
    risk_level: str
    overall_strategy: str
    measures: dict  # JSONB field - flexible structure from agent
    timeline: dict  # JSONB field - flexible structure from agent
    estimated_cost: Decimal | None = None
    status: str
    requested_by: UUID | None = None
    approved_by: UUID | None = None
    requested_at: datetime
    generated_at: datetime | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrecautionaryListResponse(BaseModel):
    """Response schema for list of precautionary measures."""

    precautions: list[PrecautionaryResponse]
    total_count: int


# --- Generic Responses ---


class SuccessResponse(BaseModel):
    """Generic success response for operations without specific return data."""

    success: bool
    message: str | None = None


class StatusResponse(BaseModel):
    """Status response for asynchronous operations.
    
    Used for:
    - Risk analysis requests (returns 202 Accepted with analysis_id)
    - Precautionary measures requests (returns 202 Accepted with precaution_id)
    """

    id: UUID
    status: str
    message: str | None = None
