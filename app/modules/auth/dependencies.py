"""Auth module dependency injection wiring.

Creates repository and service instances via FastAPI Depends() chain.
Exports AuthServiceDep type alias for clean controller signatures.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.auth.repository import (
    RefreshTokenRepository,
    VerificationTokenRepository,
)
from app.modules.auth.service import AuthService
from app.modules.ngo.repository import NgoRepository
from app.modules.users.repository import UserRepository


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserRepository:
    """Provide a UserRepository instance."""
    return UserRepository(session)


def get_verification_token_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> VerificationTokenRepository:
    """Provide a VerificationTokenRepository instance."""
    return VerificationTokenRepository(session)


def get_refresh_token_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RefreshTokenRepository:
    """Provide a RefreshTokenRepository instance."""
    return RefreshTokenRepository(session)


def get_ngo_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NgoRepository:
    """Provide an NgoRepository instance."""
    return NgoRepository(session)


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    token_repo: Annotated[
        VerificationTokenRepository,
        Depends(get_verification_token_repository),
    ],
    refresh_repo: Annotated[
        RefreshTokenRepository,
        Depends(get_refresh_token_repository),
    ],
    ngo_repo: Annotated[NgoRepository, Depends(get_ngo_repository)],
) -> AuthService:
    """Provide an AuthService with all repositories injected."""
    return AuthService(
        user_repo=user_repo,
        token_repo=token_repo,
        refresh_repo=refresh_repo,
        ngo_repo=ngo_repo,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
