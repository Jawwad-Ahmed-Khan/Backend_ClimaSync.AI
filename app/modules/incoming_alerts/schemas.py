"""Pydantic schemas for incoming alert payloads from the Data Collection Service.

Validates the three source-specific payload shapes (USGS, Open-Meteo,
Google Flood Hub) and defines the success response format.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IncomingBreachPayload(BaseModel):
    """Incoming breach notification from the Data Collection Service.

    Exactly one of seismic_event_id / weather_location_id / gauge_id
    will be present, determined by source_api.
    """

    # Core identifiers
    breach_id: str = Field(..., description="Unique UUID from the Collection Database")
    source_api: str = Field(
        ..., description="'usgs', 'open_meteo', or 'google_flood_hub'"
    )
    disaster_kind: str = Field(
        ...,
        description="'earthquake', 'flood', 'heatwave', 'heavy_rain', etc.",
    )

    # Location
    location_name: Optional[str] = Field(None, description="Human-readable city/district name")
    district: Optional[str] = Field(None, description="Pakistan district slug")
    province: Optional[str] = Field(None, description="Pakistan province enum string")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")

    # Metrics
    metric_name: str = Field(
        ..., description="The type of reading, e.g. 'magnitude', 'temp_max_c'"
    )
    observed_value: float = Field(..., description="The actual or forecasted reading")
    threshold_value: float = Field(..., description="The limit that was crossed")
    unit: str = Field(
        ..., description="Unit of measurement: 'richter', 'celsius', 'mm', 'percent'"
    )
    breach_severity: str = Field(
        ..., description="'watch', 'warning', 'emergency', or 'extreme'"
    )

    # Timing
    observation_time: datetime = Field(
        ..., description="When the event occurs / is forecasted to occur"
    )
    detected_at: datetime = Field(
        ..., description="When the collection service detected the breach"
    )
    is_forecast: bool = Field(False, description="True if this is a future prediction")
    forecast_horizon_h: Optional[int] = Field(
        None, description="Hours in the future (only when is_forecast is True)"
    )

    # Source-specific foreign keys — exactly one present per payload
    seismic_event_id: Optional[str] = Field(None, description="USGS event ID")
    weather_location_id: Optional[str] = Field(
        None, description="Open-Meteo internal location ID"
    )
    gauge_id: Optional[str] = Field(
        None, description="Google Flood Hub river gauge ID"
    )


class IncomingAlertResponse(BaseModel):
    """Response sent back to the Data Collection Service on success."""

    status: str
    alert_id: str
    message: str
