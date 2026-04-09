"""Auth module dependency injection wiring.

Creates repository and service instances via FastAPI Depends() chain.
Exports AuthServiceDep and CurrentUserDep type aliases for clean
controller signatures.
"""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.security import decode_token
from app.modules.auth.exceptions import InvalidCredentialsException
from app.modules.auth.repository import (
    RefreshTokenRepository,
    VerificationTokenRepository,
)
from app.modules.auth.service import AuthService
from app.modules.ngo.repository import NgoRepository
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """Decode JWT access token and return the authenticated User.

    Validates:
    - Token is a valid JWT with a 'sub' claim
    - Token type is 'access' (not refresh)
    - User exists and is active
    """
    try:
        payload = decode_token(token)
    except JWTError:
        raise InvalidCredentialsException()

    subject = payload.get("sub")
    token_type = payload.get("type")

    if subject is None or token_type != "access":
        raise InvalidCredentialsException()

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise InvalidCredentialsException()

    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise InvalidCredentialsException()

    return user


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

