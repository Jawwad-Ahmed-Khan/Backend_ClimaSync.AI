"""Risk Analysis module — schemas for request/response."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DisasterKindEnum(str, Enum):
    earthquake = "earthquake"
    flood = "flood"
    flash_flood = "flash_flood"
    heatwave = "heatwave"
    cyclone = "cyclone"
    heavy_rain = "heavy_rain"
    drought = "drought"
    landslide = "landslide"
    dust_storm = "dust_storm"
    cold_wave = "cold_wave"


class BreachSeverityEnum(str, Enum):
    watch = "watch"
    warning = "warning"
    emergency = "emergency"
    extreme = "extreme"


class ProvinceEnum(str, Enum):
    punjab = "punjab"
    sindh = "sindh"
    khyber_pakhtunkhwa = "khyber_pakhtunkhwa"
    balochistan = "balochistan"
    gilgit_baltistan = "gilgit_baltistan"
    azad_kashmir = "azad_kashmir"
    islamabad_capital_territory = "islamabad_capital_territory"


class SourceAPIEnum(str, Enum):
    usgs = "usgs"
    open_meteo = "open_meteo"
    google_flood_hub = "google_flood_hub"


class RiskAnalysisRequest(BaseModel):
    """Request body for triggering a risk analysis assessment."""

    breach_id: str = Field(..., description="UUID of the breach record")
    disaster_kind: DisasterKindEnum
    location_name: str = Field(..., min_length=1)
    district: str = Field(..., min_length=1)
    province: ProvinceEnum
    latitude: float = Field(..., ge=23.0, le=38.0)
    longitude: float = Field(..., ge=60.0, le=78.0)
    observed_value: float
    threshold_value: float
    breach_severity: BreachSeverityEnum
    metric_name: str = Field(..., min_length=1)
    observation_time: str
    source_api: SourceAPIEnum
    is_forecast_breach: bool = False
    forecast_horizon_h: int | None = None
    gauge_id: str | None = None
    usgs_event_id: str | None = None
    weather_location_id: str | None = None


class RiskAnalysisResponse(BaseModel):
    """Proxied response from the Risk Analysis Agent service."""

    assessment_id: str
    breach_id: str
    disaster_kind: str
    breach_severity_received: str
    location_name: str
    district: str
    province: str
    latitude: float
    longitude: float
    observation_time: str
    is_forecast_breach: bool
    forecast_horizon_h: int | None
    assessment_timestamp: str
    agent_version: str
    risk_level: str | None
    composite_risk_score: float | None
    risk_level_justification: str | None
    recommended_response_urgency: str | None
    situation_trajectory: str
    critical_actions_needed: list[str]
    time_sensitive_actions: list[str]
    escalation_triggers: list[str]
    data_confidence: str | None
    data_gaps: list[str]
    # Full detail objects
    terrain_assessment: dict[str, Any]
    hazard_severity: dict[str, Any]
    exposure: dict[str, Any]
    vulnerability: dict[str, Any]
    escalation_risk: dict[str, Any]
    response_capacity: dict[str, Any]
    impact_estimates: dict[str, Any]
    web_search_findings: dict[str, Any]
    score_breakdown: dict[str, float]
    composite_score_before_terrain: float | None = None
    terrain_multiplier_applied: float | None = None
    override_applied: bool | None = False
    override_reason: str | None = None
    assumptions_made: list[str]
