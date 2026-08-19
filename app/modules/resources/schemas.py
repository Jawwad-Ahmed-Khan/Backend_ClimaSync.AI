"""Resources and Capabilities API Schemas."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SpecializationCreate(BaseModel):
    """Schema to attach a single operational discipline."""
    specialization: str = Field(..., min_length=2, max_length=50)


class SpecializationResponse(SpecializationCreate):
    id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)


class AreaCreate(BaseModel):
    """Schema to attach an operations zone."""
    province: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=100)


class AreaResponse(AreaCreate):
    id: uuid.UUID
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class ResourcePatch(BaseModel):
    """Selectively bump up or decrease integer tracking counts."""
    ambulances: int | None = Field(None, ge=0)
    rescue_boats: int | None = Field(None, ge=0)
    trucks: int | None = Field(None, ge=0)
    four_wheel_vehicles: int | None = Field(None, ge=0)
    cranes: int | None = Field(None, ge=0)
    doctors: int | None = Field(None, ge=0)
    paramedics: int | None = Field(None, ge=0)
    rescue_divers: int | None = Field(None, ge=0)
    volunteers_available: int | None = Field(None, ge=0)
    food_packets_capacity: int | None = Field(None, ge=0)
    shelter_capacity: int | None = Field(None, ge=0)


class ResourceResponse(BaseModel):
    """Reflects current operational capacity."""
    ngo_id: uuid.UUID
    ambulances: int
    rescue_boats: int
    trucks: int
    four_wheel_vehicles: int
    cranes: int
    doctors: int
    paramedics: int
    rescue_divers: int
    volunteers_available: int
    food_packets_capacity: int
    shelter_capacity: int
    
    model_config = ConfigDict(from_attributes=True)


class NGOFullResourceProfile(BaseModel):
    """Aggregated output combining physical units and mapped area coverage."""
    ngo_id: uuid.UUID
    capabilities: ResourceResponse | dict = Field(default_factory=dict)
    areas: list[AreaResponse] = Field(default_factory=list)
    specializations: list[SpecializationResponse] = Field(default_factory=list)


class AdminSearchPayload(BaseModel):
    """Advanced querying payload for dispatcher mapping."""
    province: str | None = None
    district: str | None = None
    specialization: str | None = None
    
    # Minimum requirement capacities
    min_ambulances: int | None = None
    min_rescue_boats: int | None = None
    min_doctors: int | None = None
    min_volunteers: int | None = None
    min_shelter_capacity: int | None = None
    
    limit: int = Field(50, ge=1, le=100)


class NGOSearchResult(BaseModel):
    """Dispatcher response identifying responders."""
    ngo_id: uuid.UUID
    ngo_name: str
    contact_email: str | None = None
    contact_phone: str | None = None
    rating: float | None = None
    # Matching resource block included for confirmation
    resources: ResourceResponse | None = None
    
    model_config = ConfigDict(from_attributes=True)
