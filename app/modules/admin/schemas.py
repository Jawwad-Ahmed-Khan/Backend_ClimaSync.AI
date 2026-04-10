"""Admin module Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# --- Admin Profiles ---

class AdminProfileBase(BaseModel):
    full_name: str = Field(..., max_length=255)
    avatar_url: str | None = None
    admin_role: Literal["super_admin", "admin", "moderator"] = "admin"
    phone: str | None = Field(None, max_length=20)
    department: str | None = Field(None, max_length=100)
    is_online: bool = False


class AdminProfileCreate(AdminProfileBase):
    pass


class AdminProfileResponse(AdminProfileBase):
    admin_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Audit Logs ---

class AuditLogResponse(BaseModel):
    log_id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    old_values: dict | None = None
    new_values: dict | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- NGO Verification Update ---

class NgoVerificationUpdate(BaseModel):
    """Schema for admins to verify, reject, or suspend an NGO."""
    verification_status: Literal["pending", "verified", "rejected", "suspended"]
    suspended_reason: str | None = Field(None, description="Required only if suspended or rejected")


# --- Reports & Metrics ---

class DisasterMetricsResponse(BaseModel):
    event_id: uuid.UUID
    total_tasks: int = 0
    completed_tasks: int = 0
    in_progress_tasks: int = 0
    unallocated_tasks: int = 0
    assigned_ngos: int = 0

    model_config = ConfigDict(from_attributes=True)


class AdminReportResponse(BaseModel):
    active_users_count: int
    active_ngos_count: int
    pending_ngos_count: int
    active_alerts_count: int
    active_disasters_count: int
    disaster_metrics: list[DisasterMetricsResponse] = []
