"""
Example: Pydantic Schemas
==========================
Reference implementation of Pydantic v2 schemas with Base, Create, Update,
Read, and List patterns. Includes computed fields, custom validators,
and serialization configuration.

Location: app/modules/<module_name>/schemas.py
"""

import math
from datetime import datetime
from typing import Any, Generic, Self, TypeVar
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


# ─── Generic Paginated Response ──────────────────────────────────────────────

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class PaginatedResponse(BaseModel, Generic[SchemaT]):
    """Standard paginated response wrapper.

    Usage:
        PaginatedResponse[UserRead](items=users, total=100, page=1, size=20, pages=5)
    """

    items: list[SchemaT]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(
        cls,
        items: list[Any],
        total: int,
        page: int,
        size: int,
    ) -> "PaginatedResponse[SchemaT]":
        """Factory method for creating paginated responses."""
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size) if size > 0 else 0,
        )


# ─── User Schemas ────────────────────────────────────────────────────────────


class UserBase(BaseModel):
    """Shared user fields — used for inheritance only."""

    email: EmailStr
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        examples=["Jane Doe"],
        description="User's full display name.",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the user account is active.",
    )


class UserCreate(UserBase):
    """Request body for user creation.

    Inherits email, full_name, is_active from UserBase.
    Adds password with validation.
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (min 8 chars, must contain uppercase, lowercase, digit).",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce minimum password complexity."""
        if not any(c.isupper() for c in v):
            msg = "Password must contain at least one uppercase letter"
            raise ValueError(msg)
        if not any(c.islower() for c in v):
            msg = "Password must contain at least one lowercase letter"
            raise ValueError(msg)
        if not any(c.isdigit() for c in v):
            msg = "Password must contain at least one digit"
            raise ValueError(msg)
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()


class UserUpdate(BaseModel):
    """Request body for user update — all fields optional.

    Does NOT inherit from UserBase because all fields must be optional.
    """

    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> Self:
        """Ensure at least one field is provided for update."""
        if all(
            getattr(self, field) is None
            for field in self.model_fields
        ):
            msg = "At least one field must be provided for update"
            raise ValueError(msg)
        return self


class UserRead(UserBase):
    """Response model for a single user.

    Inherits shared fields. Adds id, role, timestamps.
    Never exposes internal fields (password hash, deleted_at).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str = Field(description="User's role (user, admin, etc.)")
    created_at: datetime
    updated_at: datetime


class UserList(PaginatedResponse[UserRead]):
    """Paginated list of users.

    Inherits PaginatedResponse structure with UserRead items.
    """

    pass


# ─── Item Schemas ────────────────────────────────────────────────────────────


class ItemBase(BaseModel):
    """Shared item fields."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        examples=["My Item"],
    )
    description: str | None = Field(
        None,
        max_length=5000,
        description="Optional detailed description.",
    )


class ItemCreate(ItemBase):
    """Request body for item creation."""

    status: str = Field(
        default="draft",
        pattern=r"^(draft|active|archived)$",
        description="Item status: draft, active, or archived.",
    )


class ItemUpdate(BaseModel):
    """Request body for item update — all fields optional."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    status: str | None = Field(None, pattern=r"^(draft|active|archived)$")


class ItemRead(ItemBase):
    """Response model for a single item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class ItemList(PaginatedResponse[ItemRead]):
    """Paginated list of items."""

    pass
