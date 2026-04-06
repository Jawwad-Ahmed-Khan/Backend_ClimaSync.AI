"""
Example: Dependency Injection Patterns
=======================================
Reference implementation of FastAPI dependency injection patterns including
database session, auth, pagination, and module-level service wiring.

Location: app/core/dependencies.py (shared)
         app/modules/<module_name>/dependencies.py (module-specific)
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED DEPENDENCIES (app/core/dependencies.py)
# ═══════════════════════════════════════════════════════════════════════════════


# ─── Database Session ────────────────────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a scoped database session.

    Session is committed on success, rolled back on exception,
    and always closed when the request completes.
    """
    from app.core.database import async_session_factory

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Type alias for cleaner signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]


# ─── Authentication ──────────────────────────────────────────────────────────


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=True,
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
):
    """Extract and validate JWT, then return the current user.

    Raises:
        HTTPException(401): If token is invalid, expired, or user not found.
    """
    import jwt

    from app.core.security import decode_token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if user_id is None:
            raise credentials_exception
        if token_type != "access":
            raise credentials_exception

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise credentials_exception

    user = await db.get(type("User", (), {}), user_id)  # Replace with actual model
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user=Depends(get_current_user),
):
    """Ensure the current user's account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )
    return current_user


# ─── Role-Based Access Control ───────────────────────────────────────────────


def require_role(*allowed_roles: str):
    """Factory that creates a dependency requiring specific roles.

    Usage:
        @router.delete("/{id}", dependencies=[Depends(require_role("admin"))])
        async def delete_item(id: UUID) -> None: ...
    """

    async def _role_checker(
        current_user=Depends(get_current_active_user),
    ):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' does not have permission. "
                f"Required: {', '.join(allowed_roles)}",
            )
        return current_user

    return _role_checker


# ─── Pagination ──────────────────────────────────────────────────────────────


class PaginationParams:
    """Injectable pagination parameters with validation.

    Usage:
        @router.get("/")
        async def list_items(pagination: PaginationParams = Depends()) -> ...:
            skip = pagination.skip
            limit = pagination.size
    """

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    ) -> None:
        self.page = page
        self.size = size

    @property
    def skip(self) -> int:
        """Calculate the offset for database queries."""
        return (self.page - 1) * self.size


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL DEPENDENCIES (app/modules/<module_name>/dependencies.py)
# ═══════════════════════════════════════════════════════════════════════════════


def get_user_repository(
    db: DbSession,
):
    """Create a UserRepository scoped to the current request's DB session."""
    from app.modules.users.repository import UserRepository

    return UserRepository(session=db)


def get_user_service(
    repo=Depends(get_user_repository),
):
    """Create a UserService with the injected repository.

    Dependency chain: get_db → get_user_repository → get_user_service
    """
    from app.modules.users.service import UserService

    return UserService(repository=repo)
