"""Tasks module Schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TaskType = Literal["ambulance", "boat", "medical", "food", "evacuation", "shelter"]
TaskPriority = Literal["low", "medium", "high", "critical"]
TaskStatus = Literal[
    "draft", "pending_approval", "unallocated", "pending_acceptance", 
    "assigned", "in_progress", "completed"
]

class TaskStatusHistoryResponse(BaseModel):
    """Immutable audit trail for task statuses."""
    id: uuid.UUID
    task_id: uuid.UUID
    old_status: TaskStatus | None = None
    new_status: TaskStatus
    changed_by: uuid.UUID | None = None
    change_reason: str | None = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    """Schema for instructing a new assignment."""
    event_id: uuid.UUID | None = None
    task_label: str = Field(..., min_length=1)
    description: str | None = None
    task_type: TaskType
    required_quantity: int | None = Field(None, ge=1)
    priority: TaskPriority = "medium"
    target_location: str | None = Field(None, description="String WKT PostGIS Geography point representation")
    target_location_name: str | None = None
    status: TaskStatus = "unallocated"
    assigned_ngo_id: uuid.UUID | None = Field(None, description="Instantly bypass allocation logic by defining NGO")
    estimated_duration_hours: int | None = Field(None, ge=1)
    deadline: datetime | None = None


class TaskUpdate(BaseModel):
    """NGO and Admin variable modifications."""
    status: TaskStatus | None = None
    progress: int | None = Field(None, ge=0, le=100)
    proof_image_url: str | None = None
    completion_notes: str | None = None
    assigned_ngo_id: uuid.UUID | None = None
    change_reason: str | None = Field(None, description="If updating status, include a loggable reason")


class TaskResponse(BaseModel):
    """Primary fetch object for operational tasks."""
    task_id: uuid.UUID
    event_id: uuid.UUID | None = None
    task_label: str
    description: str | None = None
    task_type: str
    required_quantity: int | None = None
    priority: str
    target_location: str | None = None
    target_location_name: str | None = None
    status: str
    created_by_type: str
    admin_approved_by: uuid.UUID | None = None
    approved_at: datetime | None = None
    assigned_ngo_id: uuid.UUID | None = None
    progress: int
    estimated_duration_hours: int | None = None
    proof_image_url: str | None = None
    assigned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completion_notes: str | None = None
    deadline: datetime | None = None
    created_at: datetime
    updated_at: datetime
    
    # Optionally nested history log
    history: list[TaskStatusHistoryResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
