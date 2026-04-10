"""Disasters controller — HTTP endpoints for alerts and incidents.

Handles ONLY HTTP concerns: request parsing, dependency injection,
response shaping, and status codes.
"""

import uuid

from fastapi import APIRouter, Path, Query, Request

from app.common.base_schemas import MessageResponse
from app.core.limiter import limiter
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.disasters.dependencies import DisasterServiceDep
from app.modules.disasters.schemas import (
    AlertCreate,
    AlertResponse,
    AlertUpdate,
    DisasterEventCreate,
    DisasterEventResponse,
    DisasterEventUpdate,
)

router = APIRouter(prefix="/disasters", tags=["Disasters"])
alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])


# --- Alerts Endpoints ---

@alerts_router.post(
    "",
    status_code=201,
    response_model=AlertResponse,
    summary="Create a new alert",
    description="Allows authorized roles/system integrations to post incoming alerts regarding a possible disaster.",
)
@limiter.limit("20/minute")
async def create_alert(
    request: Request,
    data: AlertCreate,
    current_user: CurrentUserDep,
    service: DisasterServiceDep,
) -> AlertResponse:
    # Role checker could be used here to restrict to admin if needed.
    return await service.create_alert(data, current_user.user_id)


@alerts_router.get(
    "",
    response_model=list[AlertResponse],
    summary="List active alerts",
)
async def list_alerts(
    current_user: CurrentUserDep,
    service: DisasterServiceDep,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[AlertResponse]:
    return await service.list_alerts(limit=limit, offset=offset)


@alerts_router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert details",
)
async def get_alert(
    current_user: CurrentUserDep,
    service: DisasterServiceDep,
    alert_id: uuid.UUID = Path(...),
) -> AlertResponse:
    return await service.get_alert(alert_id)


@alerts_router.patch(
    "/{alert_id}/status",
    response_model=AlertResponse,
    summary="Update alert (status verification)",
)
async def update_alert(
    data: AlertUpdate,
    current_user: CurrentUserDep,
    service: DisasterServiceDep,
    alert_id: uuid.UUID = Path(...),
) -> AlertResponse:
    return await service.update_alert(alert_id, data, current_user.user_id)


# --- Disaster Events Endpoints ---

@router.post(
    "",
    status_code=201,
    response_model=DisasterEventResponse,
    summary="Create a new disaster event",
    description="Promotes a verified alert to a full disaster event (Admin-only).",
)
@limiter.limit("10/minute")
async def create_event(
    request: Request,
    data: DisasterEventCreate,
    current_user: CurrentUserDep,
    service: DisasterServiceDep,
) -> DisasterEventResponse:
    return await service.create_event(data, current_user.user_id)


@router.get(
    "",
    response_model=list[DisasterEventResponse],
    summary="List active disaster events",
)
async def list_events(
    current_user: CurrentUserDep,
    service: DisasterServiceDep,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[DisasterEventResponse]:
    return await service.list_events(limit=limit, offset=offset)


@router.get(
    "/{event_id}",
    response_model=DisasterEventResponse,
    summary="Get disaster event details",
)
async def get_event(
    current_user: CurrentUserDep,
    service: DisasterServiceDep,
    event_id: uuid.UUID = Path(...),
) -> DisasterEventResponse:
    return await service.get_event(event_id)


@router.patch(
    "/{event_id}",
    response_model=DisasterEventResponse,
    summary="Update a disaster event",
)
async def update_event(
    data: DisasterEventUpdate,
    current_user: CurrentUserDep,
    service: DisasterServiceDep,
    event_id: uuid.UUID = Path(...),
) -> DisasterEventResponse:
    return await service.update_event(event_id, data, current_user.user_id)


@router.delete(
    "/{event_id}",
    response_model=MessageResponse,
    summary="Soft delete a disaster event",
)
async def delete_event(
    current_user: CurrentUserDep,
    service: DisasterServiceDep,
    event_id: uuid.UUID = Path(...),
) -> MessageResponse:
    return await service.soft_delete_event(event_id)
