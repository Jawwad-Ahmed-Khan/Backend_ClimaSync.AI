"""Generic async CRUD repository using SQLAlchemy.

Module-specific repositories inherit from BaseRepository and add
custom query methods. All operations use flush + refresh (no commit —
the session dependency handles that).
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_model import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """Generic async repository providing basic CRUD operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        """Initialise with the model class and async session."""
        self.model = model
        self.session = session

    async def get_by_id(self, record_id: UUID) -> ModelType | None:
        """Retrieve a single record by its primary key."""
        return await self.session.get(self.model, record_id)

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ModelType]:
        """Retrieve paginated list of records."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new record and return it with generated fields."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(
        self,
        instance: ModelType,
        **kwargs: Any,
    ) -> ModelType:
        """Update an existing record's fields and return it."""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Hard-delete a record from the database."""
        await self.session.delete(instance)
        await self.session.flush()

    async def count(self) -> int:
        """Return total count of records."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()
