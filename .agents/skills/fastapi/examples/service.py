"""
Example: Service Layer
=======================
Reference implementation of the service/business logic layer with
transaction management, validation rules, and structured error handling.

Location: app/modules/<module_name>/service.py
"""

import logging
from uuid import UUID

from app.common.pagination import PaginatedResponse
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserRead, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    """User business logic layer.

    Responsibilities:
    - Orchestrate repository calls.
    - Enforce business rules and validations.
    - Transform between schemas and models.
    - Handle cross-cutting concerns (hashing, events).

    Rules:
    - NEVER access the database directly — always go through the repository.
    - Raise AppException subclasses (NotFoundError, ConflictError, etc.)
      for error cases — never raise HTTPException here.
    - Keep methods focused and composable.
    """

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def get_by_id(self, user_id: UUID) -> UserRead:
        """Retrieve a user by ID.

        Raises:
            NotFoundError: If no user exists with the given ID.
        """
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError(resource="User", id=user_id)
        return UserRead.model_validate(user)

    async def list(self, *, page: int = 1, size: int = 20) -> PaginatedResponse[UserRead]:
        """List users with pagination.

        Args:
            page: Page number (1-indexed).
            size: Number of items per page.

        Returns:
            Paginated response with user data.
        """
        skip = (page - 1) * size
        users = await self.repository.get_all(skip=skip, limit=size)
        total = await self.repository.count()

        return PaginatedResponse[UserRead].create(
            items=[UserRead.model_validate(u) for u in users],
            total=total,
            page=page,
            size=size,
        )

    async def create(self, user_data: UserCreate) -> UserRead:
        """Create a new user.

        Business Rules:
        1. Email must be unique.
        2. Password is hashed before storage.

        Raises:
            ConflictError: If a user with the same email already exists.
        """
        # Check uniqueness
        existing = await self.repository.get_by_email(user_data.email)
        if existing is not None:
            raise ConflictError(message=f"User with email {user_data.email} already exists")

        # Hash password
        hashed_pw = hash_password(user_data.password)

        # Create user
        user = await self.repository.create(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_pw,
            is_active=user_data.is_active,
        )

        logger.info("User created: %s (id=%s)", user.email, user.id)
        return UserRead.model_validate(user)

    async def update(self, user_id: UUID, user_data: UserUpdate) -> UserRead:
        """Update an existing user.

        Args:
            user_id: The UUID of the user to update.
            user_data: Partial update data (only non-None fields are applied).

        Raises:
            NotFoundError: If no user exists with the given ID.
            ConflictError: If updating email to one that already exists.
        """
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError(resource="User", id=user_id)

        # Check email uniqueness if email is being changed
        update_dict = user_data.model_dump(exclude_unset=True)
        if "email" in update_dict and update_dict["email"] != user.email:
            existing = await self.repository.get_by_email(update_dict["email"])
            if existing is not None:
                raise ConflictError(
                    message=f"User with email {update_dict['email']} already exists"
                )

        # Apply update
        user = await self.repository.update(user, **update_dict)

        logger.info("User updated: %s (id=%s)", user.email, user.id)
        return UserRead.model_validate(user)

    async def delete(self, user_id: UUID) -> None:
        """Delete a user by ID.

        Raises:
            NotFoundError: If no user exists with the given ID.
        """
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError(resource="User", id=user_id)

        await self.repository.delete(user)
        logger.info("User deleted: id=%s", user_id)
