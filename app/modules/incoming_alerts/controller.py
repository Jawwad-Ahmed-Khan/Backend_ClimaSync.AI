"""Incoming alerts controller.

Exposes two endpoints:

  POST /api/v1/alerts/incoming
      Accepts machine-to-machine breach payloads from the Data Collection
      Service, persists them, and broadcasts to connected admin clients.
      Secured with an optional X-API-Key header (enforced when the env
      variable INCOMING_ALERT_API_KEY is set).

  WebSocket /ws/alerts?token=<jwt>
      Real-time stream of disaster alerts for authenticated admin users.
      Non-admin tokens are rejected with WS_1008_POLICY_VIOLATION.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect, status

from app.core.config import settings
from app.core.ws_auth import verify_admin_ws_token
from app.modules.incoming_alerts.dependencies import IncomingAlertServiceDep
from app.modules.incoming_alerts.schemas import IncomingAlertResponse, IncomingBreachPayload
from app.websockets.manager import admin_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Incoming Alerts"])
ws_router = APIRouter(tags=["WebSocket Alerts"])


# ---------------------------------------------------------------------------
# REST — receive breach payload from Data Collection Service
# ---------------------------------------------------------------------------


@router.post(
    "/incoming",
    status_code=status.HTTP_201_CREATED,
    response_model=IncomingAlertResponse,
    summary="Receive incoming breach alert from Data Collection Service",
    description=(
        "Machine-to-machine endpoint called by the Data Collection Service "
        "when a disaster threshold is breached. Persists the payload and "
        "broadcasts it to all connected admin WebSocket clients. "
        "Secured via optional X-API-Key header."
    ),
)
async def receive_incoming_alert(
    payload: IncomingBreachPayload,
    service: IncomingAlertServiceDep,
    x_api_key: str | None = Header(default=None),
) -> IncomingAlertResponse:
    """Validate API key (if configured), persist, and broadcast the alert."""
    expected_key = settings.INCOMING_ALERT_API_KEY
    if expected_key and x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-API-Key",
        )

    await service.process(payload)

    return IncomingAlertResponse(
        status="success",
        alert_id=payload.breach_id,
        message="Alert received and broadcasted to admin clients",
    )


# ---------------------------------------------------------------------------
# WebSocket — real-time stream for admin clients
# ---------------------------------------------------------------------------


@ws_router.websocket("/ws/alerts")
async def websocket_alerts_endpoint(
    websocket: WebSocket,
    admin_data: dict = Depends(verify_admin_ws_token),
) -> None:
    """Secure WebSocket endpoint — admin-only real-time disaster alerts.

    The frontend connects with:
        ws://host/ws/alerts?token=<access_jwt>

    The connection is rejected immediately if the token is absent,
    invalid, or carries a non-admin role.
    """
    await admin_ws_manager.connect(websocket)
    admin_sub = admin_data.get("sub", "unknown")
    logger.info("Admin '%s' connected to WS alert stream", admin_sub)

    try:
        while True:
            # Keep the connection alive; the server pushes data, no client messages needed.
            await websocket.receive_text()
    except WebSocketDisconnect:
        admin_ws_manager.disconnect(websocket)
        logger.info("Admin '%s' disconnected from WS alert stream", admin_sub)
