"""Disasters module dependency injection wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.disasters.repository import AlertRepository, DisasterEventRepository
from app.modules.disasters.service import DisasterService


def get_alert_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AlertRepository:
    return AlertRepository(session)


def get_disaster_event_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DisasterEventRepository:
    return DisasterEventRepository(session)


def get_disaster_service(
    alert_repo: Annotated[AlertRepository, Depends(get_alert_repository)],
    event_repo: Annotated[DisasterEventRepository, Depends(get_disaster_event_repository)],
) -> DisasterService:
    return DisasterService(
        alert_repo=alert_repo,
        event_repo=event_repo,
    )


DisasterServiceDep = Annotated[DisasterService, Depends(get_disaster_service)]
