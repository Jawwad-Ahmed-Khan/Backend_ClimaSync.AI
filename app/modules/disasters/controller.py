"""Disasters controller — HTTP endpoints for alerts and incidents.

Handles ONLY HTTP concerns: request parsing, dependency injection,
response shaping, and status codes.
"""

import uuid
import logging
from decimal import Decimal

from fastapi import APIRouter, Path, Query, Request, Header, HTTPException, status

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
    IncomingBreachPayload,
    DisasterType,
    AlertSourceEnum,
)
from app.websockets.manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/disasters", tags=["Disasters"])
alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])

EXPECTED_API_KEY = "your_secret_key_here"



# --- Alerts Endpoints ---

@alerts_router.post(
    "/incoming",
    status_code=status.HTTP_201_CREATED,
    summary="Receive incoming breach payload from Data Collection Service"
)
async def receive_incoming_alert(
    payload: IncomingBreachPayload,
    service: DisasterServiceDep,
    x_api_key: str = Header(None)
):
    if x_api_key and x_api_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    try:
        # 1. Map to AlertCreate
        try:
            mapped_disaster_kind = DisasterType(payload.disaster_kind.lower())
        except ValueError:
            mapped_disaster_kind = DisasterType.flood  # Default if unknown
            for t in DisasterType:
                if t.value == payload.disaster_kind.lower():
                    mapped_disaster_kind = t
                    break

        severity_map = {
            "watch": Decimal("3.0"),
            "warning": Decimal("5.0"),
            "emergency": Decimal("8.0"),
            "extreme": Decimal("10.0")
        }
        severity_score = severity_map.get(payload.breach_severity.lower(), Decimal("5.0"))

        alert_create = AlertCreate(
            external_ref_id=payload.breach_id,
            alert_type=mapped_disaster_kind,
            title=f"{payload.disaster_kind.capitalize()} Alert: {payload.location_name or 'Unknown Location'}",
            description=f"Observed: {payload.observed_value} {payload.unit} (Threshold: {payload.threshold_value})",
            source_type=AlertSourceEnum.sensor,
            source_name=payload.source_api,
            location=f"POINT({payload.longitude} {payload.latitude})",
            location_name=payload.location_name,
            district=payload.district,
            province=payload.province,
            severity_score=severity_score
        )

        # 2. Save to Main Database
        await service.create_alert(alert_create, None)

        # 3. Broadcast to Frontend via WebSockets
        await ws_manager.broadcast_alert(payload.model_dump(mode='json'))

        return {
            "status": "success",
            "alert_id": payload.breach_id,
            "message": "Alert received and broadcasted"
        }
    except Exception as e:
        logger.error(f"Error processing incoming alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
