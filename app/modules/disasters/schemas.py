"""Disasters and Alerts Pydantic schemas."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, confloat, conint


class DisasterType(str, Enum):
    flood = "flood"
    earthquake = "earthquake"
    cyclone = "cyclone"
    drought = "drought"
    heatwave = "heatwave"
    landslide = "landslide"


class AlertStatus(str, Enum):
    new = "new"
    verified = "verified"
    analyzing = "analyzing"
    active = "active"
    monitoring = "monitoring"
    resolved = "resolved"
    false_alarm = "false_alarm"


class AlertSourceEnum(str, Enum):
    sensor = "sensor"
    social_media = "social_media"
    news = "news"
    government = "government"
    citizen = "citizen"
    ai = "ai"
    manual = "manual"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class DisasterEventStatus(str, Enum):
    active = "active"
    monitoring = "monitoring"
    resolved = "resolved"


# --- Alerts ---

class AlertBase(BaseModel):
    external_ref_id: str | None = None
    alert_type: DisasterType
    title: str = Field(..., min_length=1)
    description: str | None = None
    source_type: AlertSourceEnum
    source_name: str | None = None
    status: AlertStatus = AlertStatus.new
    severity_score: Decimal | None = Field(default=None, ge=0, le=10)
    confidence_score: Decimal | None = Field(default=None, ge=0, le=100)
    location: str  # WKT representation like "POINT(lon lat)"
    location_name: str | None = None
    district: str | None = None
    province: str | None = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    status: AlertStatus | None = None
    severity_score: Decimal | None = Field(default=None, ge=0, le=10)
    confidence_score: Decimal | None = Field(default=None, ge=0, le=100)


class AlertResponse(AlertBase):
    alert_id: uuid.UUID
    created_by: uuid.UUID | None
    verified_by: uuid.UUID | None
    detected_at: datetime
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Disaster Events ---

class DisasterEventBase(BaseModel):
    source_alert_id: uuid.UUID | None = None
    external_ref_id: str | None = None
    event_type: DisasterType
    title: str = Field(..., min_length=1)
    description: str | None = None
    location_name: str | None = None
    district: str | None = None
    province: str | None = None
    location: str
    affected_area: str | None = None
    affected_population: int | None = Field(default=None, ge=0)
    severity_score: Decimal | None = Field(default=None, ge=0, le=10)
    risk_level: RiskLevel | None = None
    source_type: AlertSourceEnum | None = None
    event_status: DisasterEventStatus = DisasterEventStatus.active
    precautions: list[str] | None = None
    estimated_damage_pkr: int | None = Field(default=None, ge=0)


class DisasterEventCreate(DisasterEventBase):
    pass


class DisasterEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    affected_population: int | None = Field(default=None, ge=0)
    severity_score: Decimal | None = Field(default=None, ge=0, le=10)
    risk_level: RiskLevel | None = None
    event_status: DisasterEventStatus | None = None
    precautions: list[str] | None = None
    estimated_damage_pkr: int | None = Field(default=None, ge=0)


class DisasterEventResponse(DisasterEventBase):
    event_id: uuid.UUID
    created_by: uuid.UUID | None
    verified_by: uuid.UUID | None
    detected_at: datetime
    verified_at: datetime | None
    analyzed_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Incoming Data Schema ---

class IncomingBreachPayload(BaseModel):
    # Core Identifiers
    breach_id: str = Field(..., description="Unique UUID from the Collection Database")
    source_api: str = Field(..., description="'usgs', 'open_meteo', or 'google_flood_hub'")
    disaster_kind: str = Field(..., description="'earthquake', 'flood', 'heatwave', 'heavy_rain', etc.")
    
    # Location Data
    location_name: str | None = Field(default=None, description="Human readable city/district name")
    district: str | None = Field(default=None, description="Pakistan district")
    province: str | None = Field(default=None, description="Pakistan province enum string")
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
    is_forecast: bool = Field(default=False, description="True if this is a future prediction")
    forecast_horizon_h: int | None = Field(default=None, description="Hours in the future (if is_forecast is true)")
    
    # Specific API Foreign Keys (At least one will be present depending on source_api)
    seismic_event_id: str | None = Field(default=None, description="USGS specific event ID")
    weather_location_id: str | None = Field(default=None, description="Open-Meteo internal location ID")
    gauge_id: str | None = Field(default=None, description="Google Flood Hub specific river gauge ID")
