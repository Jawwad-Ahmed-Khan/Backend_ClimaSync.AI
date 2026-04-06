"""SQLAlchemy async engine, session factory, and declarative base.

All database access in the application uses async sessions yielded
by the session dependency in core/dependencies.py.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.async_database_url,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DATABASE_ECHO,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
