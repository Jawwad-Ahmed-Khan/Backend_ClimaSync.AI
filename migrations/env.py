"""Alembic env.py — configured for async SQLAlchemy.

Imports all models so autogenerate detects schema changes.
Overrides the DB URL from app settings (not alembic.ini).
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# Import ALL models so Alembic sees them for autogenerate
from app.modules.users.models import User  # noqa: F401
from app.modules.auth.models import AuthVerificationToken, AuthRefreshToken  # noqa: F401
from app.modules.ngo.models import NgoProfile, NgoResource  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Store the database URL for use in run_migrations_online
# Don't set it in config to avoid ConfigParser escaping issues
db_url = settings.async_database_url

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    """Run migrations against the provided connection."""
    context.configure(connection=connection, target_metadata=target_metadata)  # type: ignore[arg-type]
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with an async engine."""
    # Create engine configuration with the database URL
    configuration = {
        "sqlalchemy.url": db_url,
    }
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
