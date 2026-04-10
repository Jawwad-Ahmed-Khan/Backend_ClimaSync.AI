"""Social module dependency injection wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.social.repository import SocialRepository
from app.modules.social.service import SocialService


def get_social_repository(session: Annotated[AsyncSession, Depends(get_db)]) -> SocialRepository:
    return SocialRepository(session)


def get_social_service(
    repo: Annotated[SocialRepository, Depends(get_social_repository)],
) -> SocialService:
    return SocialService(repo=repo)


SocialServiceDep = Annotated[SocialService, Depends(get_social_service)]
