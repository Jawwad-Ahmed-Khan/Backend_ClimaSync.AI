"""
Example: FastAPI Module Router
===============================
Reference implementation of a module router with full CRUD endpoints,
dependency injection, type-safe responses, error handling, and pagination.

Location: app/modules/<module_name>/router.py
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.common.pagination import PaginatedResponse, PaginationParams
from app.core.dependencies import get_current_user
from app.modules.users.dependencies import get_user_service
from app.modules.users.schemas import UserCreate, UserRead, UserUpdate
from app.modules.users.service import UserService

# ─── Router Setup ────────────────────────────────────────────────────────────

router = APIRouter()

# Type aliases for cleaner signatures
CurrentUser = Annotated["User", Depends(get_current_user)]
Service = Annotated[UserService, Depends(get_user_service)]
Pagination = Annotated[PaginationParams, Depends()]


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get(
    "/",
    response_model=PaginatedResponse[UserRead],
    status_code=status.HTTP_200_OK,
    summary="List users",
    description="Retrieve a paginated list of users.",
)
async def list_users(
    service: Service,
    pagination: Pagination,
    current_user: CurrentUser,
) -> PaginatedResponse[UserRead]:
    """List all users with pagination."""
    return await service.list(page=pagination.page, size=pagination.size)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
)
async def get_user(
    user_id: UUID,
    service: Service,
    current_user: CurrentUser,
) -> UserRead:
    """Retrieve a single user by their UUID."""
    return await service.get_by_id(user_id)


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
async def create_user(
    user_in: UserCreate,
    service: Service,
) -> UserRead:
    """Create a new user account."""
    return await service.create(user_in)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update user",
)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    service: Service,
    current_user: CurrentUser,
) -> UserRead:
    """Partially update a user's information."""
    return await service.update(user_id, user_in)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
)
async def delete_user(
    user_id: UUID,
    service: Service,
    current_user: CurrentUser,
) -> None:
    """Delete a user by UUID."""
    await service.delete(user_id)
