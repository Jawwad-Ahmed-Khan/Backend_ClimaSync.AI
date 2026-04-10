"""Admin controller — HTTP endpoints for reporting, ngo validation, and audit logs.

Handles ONLY HTTP concerns.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Path, Query, Request

from app.core.limiter import limiter
from app.modules.admin.dependencies import AdminServiceDep, CurrentAdminDep
from app.modules.admin.schemas import (
    AdminReportResponse,
    AuditLogResponse,
    NgoVerificationUpdate,
)

# Ngo profiles schema should be imported from somewhere, but we didn't create NgoProfileResponse in admin.
# Let's import Any or dict for now if needed, or define a simplistic one.
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


@router.get(
    "/ngos",
    response_model=list[NgoProfileSnapshot],
    summary="List all NGOs",
    description="Retrieve NGOs. Can optionally filter by verification status (e.g. pending).",
)
async def list_ngos(
    current_admin: CurrentAdminDep,
    service: AdminServiceDep,
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
    service: AdminServiceDep,
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
    "/audit-logs",
    response_model=list[AuditLogResponse],
    summary="View system audit logs",
)
async def get_audit_logs(
    current_admin: CurrentAdminDep,
    service: AdminServiceDep,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve immutable audit traces of admin activities."""
    return await service.list_audit_logs(limit=limit, offset=offset)


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
    service: AdminServiceDep,
):
    """Get metrics and system aggregate stats."""
    return await service.generate_global_report()
