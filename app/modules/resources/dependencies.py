"""Dependency Injection mapping."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.resources.repository import ResourceRepository
from app.modules.resources.service import ResourceService


def get_resource_repository(session: Annotated[AsyncSession, Depends(get_db)]) -> ResourceRepository:
    return ResourceRepository(session)


def get_resource_service(
    repo: Annotated[ResourceRepository, Depends(get_resource_repository)]
) -> ResourceService:
    return ResourceService(repo)


ResourceServiceDep = Annotated[ResourceService, Depends(get_resource_service)]
