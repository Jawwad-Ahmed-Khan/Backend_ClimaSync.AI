"""Pydantic schemas for the AI agent pipeline.

All data flowing between agents is strongly typed here.
LLM outputs are parsed and validated against these schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-schemas
# ---------------------------------------------------------------------------


class NgoSummary(BaseModel):
    """Minimal NGO representation used by multiple agents."""

    ngo_id: uuid.UUID
    org_name: str
    base_city: str | None = None
    base_district: str | None = None
    base_province: str | None = None
    service_radius_km: int = 10
    verification_status: str = "pending"
    # Resources snapshot (may be None if NGO has no resource row yet)
    ambulances: int = 0
    rescue_boats: int = 0
    trucks: int = 0
    four_wheel_vehicles: int = 0
    cranes: int = 0
    doctors: int = 0
    paramedics: int = 0
    rescue_divers: int = 0
    volunteers_available: int = 0
    food_packets_capacity: int = 0
    shelter_capacity: int = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Agent 1 output — DisasterContext
# ---------------------------------------------------------------------------


class DisasterContext(BaseModel):
    """Enriched disaster event context assembled by the Data Extraction Agent."""

    event_id: uuid.UUID
    event_type: str  # flood | earthquake | cyclone | drought | heatwave | landslide
    title: str
    location_name: str | None = None
    district: str | None = None
    province: str | None = None
    latitude: float
    longitude: float
    severity_score: float | None = None
    affected_population: int | None = None
    detected_at: datetime
    weather_summary: dict = Field(default_factory=dict)
    sensor_readings: dict = Field(default_factory=dict)
    nearby_ngos: list[NgoSummary] = Field(default_factory=list)
    raw_event: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent 2 output — RiskReport
# ---------------------------------------------------------------------------


class RiskReport(BaseModel):
    """Risk classification produced by the Risk Analysis Agent."""

    risk_level: Literal["low", "medium", "high", "critical"]
    severity_score: float = Field(ge=0.0, le=10.0)
    affected_population_estimate: int
    estimated_damage_pkr: int | None = None
    key_risk_factors: list[str] = Field(default_factory=list)
    recommended_response_window_hours: int
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


# ---------------------------------------------------------------------------
# Agent 3 output — TaskDefinition
# ---------------------------------------------------------------------------


class TaskDefinition(BaseModel):
    """A single mitigation task produced by the Task Definer Agent."""

    task_label: str
    description: str
    task_type: Literal["ambulance", "boat", "medical", "food", "evacuation", "shelter"]
    required_quantity: int = Field(ge=1)
    priority: Literal["low", "medium", "high", "critical"]
    estimated_duration_hours: int = Field(ge=1)
    target_location_name: str
    reasoning: str


class PersistedTask(BaseModel):
    """TaskDefinition after being written to the DB (carries its DB task_id)."""

    task_id: uuid.UUID
    definition: TaskDefinition


# ---------------------------------------------------------------------------
# Agent 4 output — AllocationMap
# ---------------------------------------------------------------------------


class TaskAllocation(BaseModel):
    """Single task → NGO assignment produced by the Task Allocator Agent."""

    task_id: uuid.UUID
    assigned_ngo_id: uuid.UUID
    ngo_name: str
    match_reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class AllocationMap(BaseModel):
    """Full allocation result from the Task Allocator Agent."""

    allocations: list[TaskAllocation] = Field(default_factory=list)
    unallocated_task_ids: list[uuid.UUID] = Field(default_factory=list)
    summary: str


# ---------------------------------------------------------------------------
# Final pipeline result
# ---------------------------------------------------------------------------


class AgentPipelineResult(BaseModel):
    """Summary returned after running the full 4-agent pipeline."""

    event_id: uuid.UUID
    risk_report: RiskReport
    tasks_created: int
    tasks_allocated: int
    unallocated_task_ids: list[uuid.UUID] = Field(default_factory=list)
    allocation_summary: str = ""
