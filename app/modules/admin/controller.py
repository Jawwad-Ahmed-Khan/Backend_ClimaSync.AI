"""Admin controller — HTTP endpoints for reporting, ngo validation, audit logs,
dashboard stats, detailed reports, and messaging.

Handles ONLY HTTP concerns.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Path, Query, Request

from app.core.limiter import limiter
from app.modules.admin.dependencies import (
    AdminNgoServiceDep,
    AdminReportServiceDep,
    AdminAuditServiceDep,
    AdminMessageServiceDep,
    CurrentAdminDep,
)
from app.modules.admin.schemas import (
    AdminDashboardStats,
    AdminReportResponse,
    AuditLogResponse,
    ConversationResponse,
    DetailedReportResponse,
    MessageCreate,
    MessageResponse,
    NgoDetailedResponse,
    NgoVerificationUpdate,
)

# Ngo profiles schema
from pydantic import BaseModel, ConfigDict

class NgoProfileSnapshot(BaseModel):
    ngo_id: uuid.UUID
    org_name: str
    org_email: str
    registration_number: str
    verification_status: str
    rating: float
    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/admin", tags=["Admin"])


# --- NGO Management ---

@router.get(
    "/ngos",
    response_model=list[NgoProfileSnapshot],
    summary="List all NGOs",
    description="Retrieve NGOs. Can optionally filter by verification status (e.g. pending).",
)
async def list_ngos(
    current_admin: CurrentAdminDep,
    service: AdminNgoServiceDep,
    status: Literal["pending", "verified", "rejected", "suspended"] | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get NGOs."""
    return await service.list_ngos(status=status, limit=limit, offset=offset)


@router.patch(
    "/ngos/{ngo_id}/status",
    response_model=NgoProfileSnapshot,
    summary="Update NGO verification status",
)
async def verify_ngo(
    request: Request,
    data: NgoVerificationUpdate,
    current_admin: CurrentAdminDep,
    service: AdminNgoServiceDep,
    ngo_id: uuid.UUID = Path(...),
):
    """Approve, Reject, or Suspend an NGO."""
    ip_address = request.client.host if request.client else None
    return await service.verify_ngo(
        ngo_id=ngo_id,
        admin_id=current_admin.user_id,
        data=data,
        ip_address=ip_address,
    )


@router.get(
    "/ngos/{ngo_id}/details",
    response_model=NgoDetailedResponse,
    summary="Get detailed NGO profile with performance metrics",
)
async def get_ngo_details(
    current_admin: CurrentAdminDep,
    service: AdminNgoServiceDep,
    ngo_id: uuid.UUID = Path(...),
):
    """Get full NGO profile with resources, specializations, and task counts."""
    result = await service.get_ngo_details(ngo_id)
    return result


# --- Audit Logs ---

@router.get(
    "/audit-logs",
    response_model=list[AuditLogResponse],
    summary="View system audit logs",
)
async def get_audit_logs(
    current_admin: CurrentAdminDep,
    service: AdminAuditServiceDep,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve immutable audit traces of admin activities."""
    return await service.list_audit_logs(limit=limit, offset=offset)


# --- Reports ---

@router.get(
    "/reports",
    response_model=AdminReportResponse,
    summary="Generate Global Admin Report",
    description="Fetches analytical data about active users, events, and metrics.",
)
@limiter.limit("5/minute")
async def generate_global_report(
    request: Request,
    current_admin: CurrentAdminDep,
    service: AdminReportServiceDep,
):
    """Get metrics and system aggregate stats."""
    return await service.generate_global_report()


# --- Dashboard Stats (NEW) ---

@router.get(
    "/stats",
    response_model=AdminDashboardStats,
    summary="Get dashboard stats for command center",
)
async def get_dashboard_stats(
    current_admin: CurrentAdminDep,
    service: AdminReportServiceDep,
):
    """Aggregated counts for the admin dashboard stat cards."""
    return await service.get_dashboard_stats()


# --- Detailed Report (NEW) ---

@router.get(
    "/reports/detailed",
    response_model=DetailedReportResponse,
    summary="Generate detailed analytics report",
)
@limiter.limit("5/minute")
async def generate_detailed_report(
    request: Request,
    current_admin: CurrentAdminDep,
    service: AdminReportServiceDep,
):
    """Rich analytics: disasters by type, tasks over time, NGO leaderboard."""
    return await service.generate_detailed_report()


# --- Messaging (NEW) ---

@router.get(
    "/messages/conversations",
    response_model=list[ConversationResponse],
    summary="List admin conversations",
)
async def list_conversations(
    current_admin: CurrentAdminDep,
    service: AdminMessageServiceDep,
):
    """Get all conversations for the current admin."""
    return await service.get_conversations(current_admin.user_id)


@router.get(
    "/messages/conversations/{conversation_id}",
    response_model=list[MessageResponse],
    summary="Get messages in a conversation",
)
async def get_conversation_messages(
    current_admin: CurrentAdminDep,
    service: AdminMessageServiceDep,
    conversation_id: uuid.UUID = Path(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Fetch messages and mark them as read."""
    return await service.get_messages(conversation_id, current_admin.user_id, limit=limit, offset=offset)


@router.post(
    "/messages/send",
    response_model=MessageResponse,
    status_code=201,
    summary="Send a message",
)
async def send_message(
    data: MessageCreate,
    current_admin: CurrentAdminDep,
    service: AdminMessageServiceDep,
):
    """Send a message to another user."""
    return await service.send_message(
        sender_id=current_admin.user_id,
        receiver_id=data.receiver_id,
        content=data.content,
    )


@router.post(
    "/messages/conversations/{conversation_id}/read",
    summary="Mark conversation as read",
)
async def mark_conversation_read(
    current_admin: CurrentAdminDep,
    service: AdminMessageServiceDep,
    conversation_id: uuid.UUID = Path(...),
):
    """Mark all messages in a conversation as read."""
    count = await service.mark_read(conversation_id, current_admin.user_id)
    return {"marked_read": count}
