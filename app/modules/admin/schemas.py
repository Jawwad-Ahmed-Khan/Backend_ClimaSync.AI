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


# --- Dashboard Stats (NEW) ---

class AdminDashboardStats(BaseModel):
    """Aggregated stats for the admin command center dashboard."""
    active_disasters: int = 0
    total_alerts: int = 0
    new_alerts: int = 0
    total_tasks: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0
    total_ngos: int = 0
    pending_ngos: int = 0
    verified_ngos: int = 0
    total_users: int = 0
    total_social_posts: int = 0


# --- Detailed Report (NEW) ---

class DisasterTypeCount(BaseModel):
    event_type: str
    count: int


class TasksOverTimeEntry(BaseModel):
    month: str
    created: int = 0
    completed: int = 0


class NgoLeaderboardEntry(BaseModel):
    ngo_id: uuid.UUID
    org_name: str
    tasks_completed: int = 0
    rating: float = 0.0


class DetailedReportResponse(BaseModel):
    """Rich analytics for the admin reports page."""
    total_disasters: int = 0
    total_tasks: int = 0
    avg_completion_rate: float = 0.0
    disasters_by_type: list[DisasterTypeCount] = []
    tasks_over_time: list[TasksOverTimeEntry] = []
    ngo_leaderboard: list[NgoLeaderboardEntry] = []


# --- NGO Detailed Response (NEW) ---

class NgoResourceSnapshot(BaseModel):
    resource_type: str
    quantity: int = 0
    description: str | None = None


class NgoDetailedResponse(BaseModel):
    """Full NGO profile with performance metrics."""
    ngo_id: uuid.UUID
    org_name: str
    org_email: str
    registration_number: str
    verification_status: str
    rating: float = 0.0
    province: str | None = None
    city: str | None = None
    address: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    founded_year: int | None = None
    total_members: int | None = None
    description: str | None = None
    is_active: bool = True
    tasks_completed: int = 0
    tasks_in_progress: int = 0
    resources: list[NgoResourceSnapshot] = []
    specializations: list[str] = []
    operational_areas: list[str] = []
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Messaging (NEW) ---

class MessageCreate(BaseModel):
    """Schema for sending a new message in a conversation."""
    receiver_id: uuid.UUID
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    """Single message response."""
    message_id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    receiver_id: uuid.UUID
    content: str
    is_read: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """Conversation summary for the sidebar."""
    conversation_id: uuid.UUID
    participant_id: uuid.UUID
    participant_name: str
    participant_type: str = "ngo_user"
    last_message: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = 0

    model_config = ConfigDict(from_attributes=True)
