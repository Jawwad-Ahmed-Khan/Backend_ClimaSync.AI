"""Service for incoming alerts — orchestrates persistence and WebSocket broadcast."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from app.modules.incoming_alerts.repository import IncomingAlertRepository
from app.modules.incoming_alerts.schemas import IncomingBreachPayload
from app.websockets.manager import AdminAlertConnectionManager

logger = logging.getLogger(__name__)


class IncomingAlertService:
    """Handles idempotent persistence and real-time broadcast of breach payloads."""

    def __init__(
        self,
        repo: IncomingAlertRepository,
        ws_manager: AdminAlertConnectionManager,
    ) -> None:
        self._repo = repo
        self._ws_manager = ws_manager

    async def process(self, payload: IncomingBreachPayload) -> None:
        """Persist the payload (idempotent) and broadcast to all admin clients.

        Raises HTTP 409 if the breach_id was already processed.
        """
        already_exists = await self._repo.exists(payload.breach_id)
        if already_exists:
            logger.info(
                "Duplicate breach_id received, skipping: %s", payload.breach_id
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Alert '{payload.breach_id}' has already been processed.",
            )

        await self._repo.save(payload)
        logger.info(
            "Saved incoming alert breach_id=%s source=%s kind=%s",
            payload.breach_id,
            payload.source_api,
            payload.disaster_kind,
        )

        await self._ws_manager.broadcast_alert(payload.model_dump(mode="json"))
        logger.info(
            "Broadcasted alert breach_id=%s to %d admin client(s)",
            payload.breach_id,
            len(self._ws_manager.active_admin_connections),
        )
