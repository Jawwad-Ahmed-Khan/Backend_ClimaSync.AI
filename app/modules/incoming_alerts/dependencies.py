"""Dependency injection wiring for the incoming_alerts module."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.incoming_alerts.repository import IncomingAlertRepository
from app.modules.incoming_alerts.service import IncomingAlertService
from app.websockets.manager import admin_ws_manager


def get_incoming_alert_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> IncomingAlertRepository:
    return IncomingAlertRepository(session)


def get_incoming_alert_service(
    repo: Annotated[IncomingAlertRepository, Depends(get_incoming_alert_repository)],
) -> IncomingAlertService:
    return IncomingAlertService(repo=repo, ws_manager=admin_ws_manager)


IncomingAlertServiceDep = Annotated[IncomingAlertService, Depends(get_incoming_alert_service)]
