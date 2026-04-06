"""
Example: Repository Layer (Data Access)
========================================
Reference implementation of a generic async repository with CRUD operations,
filtering, pagination, soft-delete support, and count queries.

Location: app/common/base_repository.py (generic base)
         app/modules/<module_name>/repository.py (concrete implementation)
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_model import BaseModel, SoftDeleteMixin

ModelT = TypeVar("ModelT", bound=BaseModel)


# ─── Generic Base Repository ────────────────────────────────────────────────


class BaseRepository(Generic[ModelT]):
    """Generic async CRUD repository.

    Provides standard data access operations for any SQLAlchemy model.
    Extend this class in module-specific repositories to add custom queries.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession) -> None:
                super().__init__(User, session)

            async def get_by_email(self, email: str) -> User | None:
                ...
    """

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    # ── Read operations ──────────────────────────────────────────────────

    async def get_by_id(self, id: UUID) -> ModelT | None:
        """Fetch a single record by primary key."""
        return await self.session.get(self.model, id)

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
    ) -> list[ModelT]:
        """Fetch multiple records with pagination and optional ordering."""
        stmt = self._base_query().offset(skip).limit(limit)
        if order_by and hasattr(self.model, order_by):
            stmt = stmt.order_by(getattr(self.model, order_by))
        else:
            stmt = stmt.order_by(self.model.created_at.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_field(self, field: str, value: Any) -> ModelT | None:
        """Fetch a single record by a specific field value."""
        if not hasattr(self.model, field):
            msg = f"{self.model.__name__} has no field '{field}'"
            raise ValueError(msg)

        stmt = self._base_query().where(getattr(self.model, field) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_many_by_field(
        self,
        field: str,
        value: Any,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelT]:
        """Fetch multiple records matching a field value."""
        if not hasattr(self.model, field):
            msg = f"{self.model.__name__} has no field '{field}'"
            raise ValueError(msg)

        stmt = (
            self._base_query()
            .where(getattr(self.model, field) == value)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total records (excluding soft-deleted if applicable)."""
        stmt = select(func.count()).select_from(self.model)
        if issubclass(self.model, SoftDeleteMixin):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, id: UUID) -> bool:
        """Check if a record exists by primary key."""
        stmt = select(func.count()).select_from(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    # ── Write operations ─────────────────────────────────────────────────

    async def create(self, **kwargs: Any) -> ModelT:
        """Create and persist a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def create_many(self, items: list[dict[str, Any]]) -> list[ModelT]:
        """Bulk create multiple records."""
        instances = [self.model(**data) for data in items]
        self.session.add_all(instances)
        await self.session.flush()
        for instance in instances:
            await self.session.refresh(instance)
        return instances

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        """Update an existing record with new values."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Hard delete a record."""
        await self.session.delete(instance)
        await self.session.flush()

    async def soft_delete(self, instance: ModelT) -> ModelT:
        """Soft delete a record by setting deleted_at."""
        if not isinstance(instance, SoftDeleteMixin):
            msg = f"{self.model.__name__} does not support soft delete"
            raise TypeError(msg)

        from datetime import datetime, timezone

        instance.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    # ── Internal helpers ─────────────────────────────────────────────────

    def _base_query(self) -> Select:
        """Base SELECT query that excludes soft-deleted records if applicable."""
        stmt = select(self.model)
        if issubclass(self.model, SoftDeleteMixin):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return stmt


# ─── Concrete Module Repository ─────────────────────────────────────────────


class UserRepository(BaseRepository):
    """User-specific data access layer.

    Extends BaseRepository with domain-specific queries.
    Location: app/modules/users/repository.py
    """

    def __init__(self, session: AsyncSession) -> None:
        from app.modules.users.models import User

        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Any | None:
        """Fetch a user by their email address."""
        return await self.get_by_field("email", email)

    async def get_active_users(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Any]:
        """Fetch only active users."""
        return await self.get_many_by_field(
            "is_active",
            True,
            skip=skip,
            limit=limit,
        )
