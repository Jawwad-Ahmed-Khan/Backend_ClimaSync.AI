"""SQLAlchemy async engine, session factory, and declarative base.

All database access in the application uses async sessions yielded
by the session dependency in core/dependencies.py.

IMPORTANT: All SQLAlchemy imports are deferred to avoid hanging on Windows.
"""

from app.core.config import settings

# Lazy initialization - engine created only when first accessed
_engine = None
_async_session_factory = None
_Base = None


def get_engine():
    """Get or create the async engine (deferred to avoid import-time hang)."""
    global _engine
    if _engine is None:
        # Import here to avoid hanging at module level on Windows
        from sqlalchemy.ext.asyncio import create_async_engine
        
        _engine = create_async_engine(
            settings.async_database_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections every hour
            echo=settings.DATABASE_ECHO,
            connect_args={
                "statement_cache_size": 0,
                "prepared_statement_cache_size": 0,
                "timeout": 10,  # asyncpg command timeout in seconds
                "server_settings": {"connect_timeout": "10"},
            },
        )
    return _engine


def get_session_factory():
    """Get or create the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        # Import here to avoid hanging at module level on Windows
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
        
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


def get_base():
    """Get or create the declarative base."""
    global _Base
    if _Base is None:
        # Import here to avoid hanging at module level on Windows
        from sqlalchemy.orm import DeclarativeBase
        
        class Base(DeclarativeBase):
            """Base class for all SQLAlchemy ORM models."""
            pass
        
        _Base = Base
    return _Base


# Stub objects to maintain backward compatibility - don't call them at import time
class _EngineStub:
    """Stub that defers engine creation to first real use."""
    def __call__(self, *args, **kwargs):
        return get_engine()(*args, **kwargs)
    def __getattr__(self, name):
        return getattr(get_engine(), name)


class _SessionFactoryStub:
    """Stub that defers session factory creation to first real use."""
    def __call__(self, *args, **kwargs):
        return get_session_factory()(*args, **kwargs)
    def __getattr__(self, name):
        return getattr(get_session_factory(), name)


class _BaseProxy:
    """Proxy to the deferred Base class.

    Implements __mro_entries__ so that ORM models can inherit from
    this proxy object directly:  class Foo(Base, Mixin): ...
    Python calls __mro_entries__ during class creation and replaces
    this proxy with the real DeclarativeBase subclass.
    """

    def __mro_entries__(self, bases: tuple) -> tuple:
        """Return the real base class for use in class body MRO resolution."""
        return (get_base(),)

    def __getattr__(self, name: str):
        return getattr(get_base(), name)


# Module-level stubs - these won't trigger engine/base creation at import time
engine = _EngineStub()
async_session_factory = _SessionFactoryStub()
Base = _BaseProxy()

