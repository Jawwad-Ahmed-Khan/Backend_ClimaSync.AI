---
name: FastAPI Production Skill
description: >
  Comprehensive FastAPI skill for building production-grade APIs with best practices,
  security hardening, full type safety, async patterns, modular architecture, and
  industry-standard patterns. Covers every layer from routing to deployment.
version: 1.0.0
---

# FastAPI Production Skill

This skill defines the authoritative standards, patterns, and conventions for building
FastAPI applications in this project. **Every code generation, review, and refactoring
task MUST follow these guidelines.**

> **How to use this skill:** When the agent is asked to create, modify, or review
> FastAPI code, it MUST read this file first and follow all patterns exactly. Example
> files in `examples/` provide reference implementations. Checklists in `resources/`
> provide step-by-step guides for common workflows.

---

## Table of Contents

1. [Project Architecture](#1-project-architecture)
2. [Module Blueprint](#2-module-blueprint)
3. [Application Factory](#3-application-factory)
4. [Configuration & Settings](#4-configuration--settings)
5. [Database & ORM](#5-database--orm)
6. [Authentication & Authorization](#6-authentication--authorization)
7. [Pydantic Schemas](#7-pydantic-schemas)
8. [Dependency Injection](#8-dependency-injection)
9. [Error Handling](#9-error-handling)
10. [Middleware](#10-middleware)
11. [Background Tasks](#11-background-tasks)
12. [Logging & Observability](#12-logging--observability)
13. [Performance](#13-performance)
14. [Security Hardening](#14-security-hardening)
15. [Type Safety](#15-type-safety)
16. [Testing Strategy](#16-testing-strategy)
17. [API Versioning](#17-api-versioning)
18. [Deployment](#18-deployment)
19. [Code Style & Conventions](#19-code-style--conventions)
20. [Dependency Management](#20-dependency-management)

---

## 1. Project Architecture

### Directory Structure

```
project-root/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Application factory (create_app)
│   ├── core/                    # Shared infrastructure
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic BaseSettings
│   │   ├── database.py          # SQLAlchemy engine, session
│   │   ├── security.py          # JWT, hashing, OAuth2 scheme
│   │   ├── dependencies.py      # Shared dependencies (get_db, get_current_user)
│   │   ├── exceptions.py        # Exception hierarchy + handlers
│   │   ├── middleware.py         # Custom middleware stack
│   │   ├── logging.py           # Structured logging setup
│   │   └── constants.py         # App-wide constants and enums
│   ├── common/                  # Reusable base classes & utilities
│   │   ├── __init__.py
│   │   ├── base_model.py        # SQLAlchemy base model with mixins
│   │   ├── base_schema.py       # Pydantic base schemas
│   │   ├── base_repository.py   # Generic CRUD repository
│   │   ├── base_service.py      # Generic service layer
│   │   ├── pagination.py        # Pagination utilities
│   │   ├── types.py             # Custom types and Annotated aliases
│   │   └── utils.py             # Pure utility functions
│   └── modules/                 # Feature modules
│       ├── __init__.py
│       ├── auth/                # Authentication module
│       ├── users/               # User management module
│       └── items/               # Domain-specific module
├── migrations/                  # Alembic migrations
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── unit/
│   │   └── modules/
│   └── integration/
│       └── modules/
├── scripts/                     # DevOps & utility scripts
├── .env                         # Environment variables (git-ignored)
├── .env.example                 # Template for .env
├── pyproject.toml               # Project config & dependencies
├── Dockerfile
└── docker-compose.yml
```

### Architectural Principles

1. **Modular Monolith**: Each feature is a self-contained module under `app/modules/`.
   Modules communicate via service interfaces, never by importing each other's internals.
2. **Layered Architecture**: `Router → Service → Repository → Database`. Each layer has
   a single responsibility. No layer may skip another (routers MUST NOT call repositories directly).
3. **Dependency Inversion**: All cross-cutting concerns (auth, DB sessions, config) are
   injected via FastAPI's `Depends()`, never imported directly into business logic.
4. **Shared Infrastructure**: `app/core/` for application-level config; `app/common/` for
   reusable base classes that modules extend.

---

## 2. Module Blueprint

Every feature module under `app/modules/<module_name>/` MUST contain:

```
app/modules/<module_name>/
├── __init__.py          # Module public API exports
├── router.py            # FastAPI APIRouter with all endpoints
├── schemas.py           # Pydantic models (request/response)
├── models.py            # SQLAlchemy ORM models
├── service.py           # Business logic (orchestration, validation)
├── repository.py        # Data access layer (queries, CRUD)
├── dependencies.py      # Module-specific Depends() callables
├── exceptions.py        # Module-specific exception classes
└── constants.py         # Module-specific constants and enums
```

### Module Rules

- **`__init__.py`** exports the module's router for mounting:
  ```python
  from app.modules.<module_name>.router import router

  __all__ = ["router"]
  ```
- **No circular imports**: modules import from `app.core` and `app.common`, never from
  sibling modules directly. Use dependency injection or events for cross-module communication.
- **Each module is independently testable**: tests mirror the module structure under
  `tests/unit/modules/<module_name>/` and `tests/integration/modules/<module_name>/`.

> **Reference**: See `examples/router.py`, `examples/service.py`, `examples/repository.py`

---

## 3. Application Factory

Use the factory pattern for app creation. This enables testing with different configs
and clean startup/shutdown lifecycle management.

```python
# app/main.py
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.middleware import register_middleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    # --- Startup ---
    # Initialize database connection pool, caches, external clients
    # Example: await database.connect()
    yield
    # --- Shutdown ---
    # Close connections, flush buffers, release resources
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # Register middleware (order matters — first registered = outermost)
    register_middleware(app)

    # Register global exception handlers
    register_exception_handlers(app)

    # Mount module routers
    _register_routers(app)

    return app


def _register_routers(app: FastAPI) -> None:
    """Mount all module routers with API version prefix."""
    from app.modules.auth import router as auth_router
    from app.modules.items import router as items_router
    from app.modules.users import router as users_router

    api_prefix = settings.API_V1_PREFIX  # "/api/v1"

    app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["Auth"])
    app.include_router(users_router, prefix=f"{api_prefix}/users", tags=["Users"])
    app.include_router(items_router, prefix=f"{api_prefix}/items", tags=["Items"])
```

### Root `main.py`

```python
# main.py (project root)
import uvicorn

from app.main import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## 4. Configuration & Settings

Use Pydantic `BaseSettings` for type-safe, validated configuration with `.env` support.

### Rules

1. **Never hardcode** secrets, URLs, or environment-specific values.
2. **All config** goes through `settings` — no `os.getenv()` scattered in code.
3. **Validate eagerly** — app fails fast on invalid config at startup.
4. **Secrets** are stored in `.env` (git-ignored) or a secrets manager.
5. **Provide `.env.example`** with all required keys (no values for secrets).

### Pattern

```python
# app/core/config.py
from functools import lru_cache
from pydantic import field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "Backend Clima"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = ""
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False

    # --- Security ---
    SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # --- Redis (optional) ---
    REDIS_URL: str | None = None

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json | text

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            msg = f"ENVIRONMENT must be one of {allowed}"
            raise ValueError(msg)
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
```

> **Reference**: See `examples/config.py` for the full implementation.

---

## 5. Database & ORM

Use **SQLAlchemy 2.0** with async support and the **repository pattern** for data access.

### Engine & Session Setup

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,  # Verify connections before use
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass
```

### Base Model with Mixins

```python
# app/common/base_model.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimestampMixin:
    """Adds created_at and updated_at columns."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds soft-delete support via deleted_at column."""
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class BaseModel(Base, TimestampMixin):
    """Abstract base model with UUID primary key and timestamps."""
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
```

### Session Dependency

```python
# app/core/dependencies.py
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session, auto-close on exit."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Repository Pattern

```python
# app/common/base_repository.py (simplified — see examples/repository.py for full)
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_model import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(Generic[ModelT]):
    """Generic async CRUD repository."""

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelT | None:
        return await self.session.get(self.model, id)

    async def get_all(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[ModelT]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.flush()
```

### Alembic Migrations

```bash
# Initialize (one-time)
alembic init migrations

# Generate migration
alembic revision --autogenerate -m "description_of_change"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

Migration rules:
- **Always review autogenerated migrations** before applying.
- **Never edit applied migrations** — create a new one instead.
- **Name migrations descriptively**: `add_users_email_index`, not `update1`.
- **Include both `upgrade()` and `downgrade()`** for reversibility.

> **Reference**: See `examples/model.py`, `examples/repository.py`

---

## 6. Authentication & Authorization

Use **OAuth2 + JWT** with **bcrypt/argon2** password hashing and **role-based access control**.

### JWT Token Flow

```
Client                           Server
  │                                │
  ├── POST /auth/login ──────────►│
  │   (email + password)          │
  │                                ├── Verify password hash
  │                                ├── Generate access_token (short-lived)
  │                                ├── Generate refresh_token (long-lived)
  │◄── { access_token,           │
  │      refresh_token } ─────────┤
  │                                │
  ├── GET /users/me ─────────────►│
  │   Authorization: Bearer xxx   │
  │                                ├── Decode & validate JWT
  │                                ├── Load user from DB
  │◄── { user_data } ─────────────┤
```

### Security Core

```python
# app/core/security.py
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    extra_claims: dict | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.SECRET_KEY.get_secret_value(),
        algorithms=[settings.JWT_ALGORITHM],
    )
```

### Auth Dependencies

```python
# app/core/dependencies.py (auth section)
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "User":
    """Decode JWT and return the authenticated user."""
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def require_role(*roles: str):
    """Factory for role-based access control dependency."""
    async def _check_role(
        current_user: Annotated["User", Depends(get_current_user)],
    ) -> "User":
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return _check_role
```

### Usage in Routers

```python
# Protected endpoint — any authenticated user
@router.get("/me")
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    return current_user

# Admin-only endpoint
@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    admin: Annotated[User, Depends(require_role("admin"))],
    service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    await service.delete(user_id)
```

> **Reference**: See `examples/auth.py`

---

## 7. Pydantic Schemas

Use **Pydantic v2** with strict separation between input and output schemas.

### Schema Naming Convention

| Schema Type | Naming | Purpose |
|-------------|--------|---------|
| `<Model>Base` | `UserBase` | Shared fields (used for inheritance) |
| `<Model>Create` | `UserCreate` | Request body for creation |
| `<Model>Update` | `UserUpdate` | Request body for updates (all fields optional) |
| `<Model>Read` | `UserRead` | Response model (includes `id`, timestamps) |
| `<Model>List` | `UserList` | Paginated list response |

### Pattern

```python
# app/modules/users/schemas.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Shared user fields."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True


class UserCreate(UserBase):
    """Request body for user creation."""
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Request body for user update — all fields optional."""
    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None


class UserRead(UserBase):
    """Response model for a single user."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    created_at: datetime
    updated_at: datetime


class UserList(BaseModel):
    """Paginated user list response."""
    items: list[UserRead]
    total: int
    page: int
    size: int
    pages: int
```

### Schema Rules

1. **Never expose internal fields** (password hashes, deleted_at) in Read schemas.
2. **Use `ConfigDict(from_attributes=True)`** on Read schemas for ORM integration.
3. **Validate at schema level**: Field constraints (`min_length`, `max_length`, `gt`, `lt`),
   custom validators (`@field_validator`), model validators (`@model_validator`).
4. **Use `Field(...)`** for required fields with metadata; `Field(None)` for optional.
5. **Use `EmailStr`**, `HttpUrl`, `SecretStr` from Pydantic for built-in validation.
6. **Create schemas are strict** (all required fields); **Update schemas are lenient** (all optional).

> **Reference**: See `examples/schema.py`

---

## 8. Dependency Injection

FastAPI's `Depends()` is the primary mechanism for injecting services, sessions, and auth.

### Dependency Hierarchy

```
Router endpoint
  ├── Depends(get_current_user)     ← Auth
  │     └── Depends(oauth2_scheme)  ← Token extraction
  │     └── Depends(get_db)         ← DB session
  ├── Depends(get_service)          ← Business logic
  │     └── Depends(get_repository) ← Data access
  │           └── Depends(get_db)   ← DB session (same instance)
  └── Depends(PaginationParams)     ← Query params
```

### Common Dependency Patterns

```python
# app/common/pagination.py
from dataclasses import dataclass
from typing import Annotated
from fastapi import Query


@dataclass
class PaginationParams:
    """Reusable pagination query parameters."""
    page: Annotated[int, Query(ge=1, description="Page number")] = 1
    size: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.size


# Module-level dependency wiring
# app/modules/users/dependencies.py
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService


def get_user_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRepository:
    return UserRepository(session=db)


def get_user_service(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(repository=repo)
```

### Rules

1. **Dependencies MUST be functions or classes**, not module-level singletons.
2. **Use `Annotated[Type, Depends(factory)]`** syntax (Pydantic v2 / FastAPI 0.95+).
3. **Scope is per-request** by default — each request gets its own DB session.
4. **Composition**: build complex dependencies from simple ones (see hierarchy above).
5. **Avoid side effects** in dependency functions (logging is OK; mutations are not).

> **Reference**: See `examples/dependencies.py`

---

## 9. Error Handling

Use a **custom exception hierarchy** with **global handlers** that produce structured
error responses following **RFC 7807 Problem Details**.

### Exception Hierarchy

```python
# app/core/exceptions.py
from typing import Any


class AppException(Exception):
    """Base exception for all application errors."""
    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource", id: Any = None) -> None:
        detail = f"{resource} not found" + (f": {id}" if id else "")
        super().__init__(message=detail, status_code=404, error_code="NOT_FOUND")


class ConflictError(AppException):
    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(message=message, status_code=409, error_code="CONFLICT")


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", details: dict | None = None) -> None:
        super().__init__(message=message, status_code=422, error_code="VALIDATION_ERROR", details=details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message=message, status_code=401, error_code="UNAUTHORIZED")


class ForbiddenError(AppException):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message=message, status_code=403, error_code="FORBIDDEN")


class RateLimitError(AppException):
    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message=message, status_code=429, error_code="RATE_LIMITED")
```

### Global Exception Handlers

```python
# app/core/exceptions.py (continued)
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "Application error: %s (code=%s, status=%d)",
            exc.message, exc.error_code, exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception: %s", str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal server error occurred",
                    "details": {},
                }
            },
        )
```

### Consistent Error Response Format

All error responses follow this structure:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "User not found: 123e4567-e89b-...",
    "details": {}
  }
}
```

### Rules

1. **Raise `AppException` subclasses** in service/repository layers — never `HTTPException`.
2. **`HTTPException` is only acceptable** in dependencies (auth) and routers (rare cases).
3. **Never expose stack traces** to clients in production.
4. **Log all errors** — warnings for 4xx, errors for 5xx.

> **Reference**: See `examples/exceptions.py`

---

## 10. Middleware

Register middleware in a dedicated function. Order matters: first registered = outermost.

### Standard Middleware Stack

```python
# app/core/middleware.py
import time
import uuid
import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


def register_middleware(app: FastAPI) -> None:
    """Register all middleware in correct order."""

    # CORS — must be outermost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Trusted Hosts (production)
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS,
        )

    # Custom middleware
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(TimingMiddleware)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request/response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Log request processing time."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Request %s %s completed in %.2fms (status=%d)",
            request.method,
            request.url.path,
            duration_ms,
            response.status_code,
        )
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        return response
```

> **Reference**: See `examples/middleware.py`

---

## 11. Background Tasks

### FastAPI Native (Simple Cases)

```python
from fastapi import BackgroundTasks

@router.post("/users/")
async def create_user(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    user = await service.create(user_in)
    background_tasks.add_task(send_welcome_email, user.email)
    return user
```

### Task Queue (Complex Cases)

For heavy or distributed work, use **Celery**, **ARQ**, or **Dramatiq**:

```python
# app/core/tasks.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3)
def send_notification(self, user_id: str, message: str) -> None:
    """Send a notification to a user with retry logic."""
    try:
        # ... send notification
        pass
    except Exception as exc:
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
```

### Rules

1. **Use FastAPI `BackgroundTasks`** for fire-and-forget tasks that are fast (<5 seconds)
   and don't need retries.
2. **Use a task queue** (Celery/ARQ) for tasks that are slow, need retries, or must
   survive server restarts.
3. **Never access request-scoped resources** (DB sessions) in background tasks — create
   new sessions inside the task.

---

## 12. Logging & Observability

### Structured JSON Logging

```python
# app/core/logging.py
import logging
import sys
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # Include request ID if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        # Include exception info
        if record.exc_info and record.exc_info[1]:
            log_data["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }
        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure application-wide logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    handler = logging.StreamHandler(sys.stdout)
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )

    root_logger.handlers = [handler]

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
```

### Health Check Endpoint

```python
# app/core/health.py
from fastapi import APIRouter, status
from sqlalchemy import text

from app.core.database import async_session_factory

health_router = APIRouter(tags=["Health"])


@health_router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """Basic health check."""
    return {"status": "healthy"}


@health_router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> dict:
    """Readiness check — verifies database connectivity."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not_ready", "database": str(e)}
```

### Rules

1. **Use structured logging** (JSON) in production; human-readable in development.
2. **Include correlation/request IDs** in every log entry for traceability.
3. **Log at appropriate levels**: DEBUG for dev details, INFO for request flow,
   WARNING for recoverable issues, ERROR for failures.
4. **Never log sensitive data** — passwords, tokens, PII.
5. **Expose `/health` and `/health/ready`** endpoints for orchestrators.

---

## 13. Performance

### Async Best Practices

```python
# ✅ GOOD: Async all the way
async def get_user_with_posts(user_id: UUID, db: AsyncSession) -> User:
    stmt = select(User).options(selectinload(User.posts)).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

# ❌ BAD: Blocking call in async context
async def get_user_bad(user_id: UUID) -> User:
    return db.query(User).get(user_id)  # Synchronous! Blocks event loop

# ✅ GOOD: Run CPU-bound work in thread pool
import asyncio
async def process_image(data: bytes) -> bytes:
    return await asyncio.to_thread(heavy_cpu_function, data)
```

### Connection Pooling

- **Database**: Configure `pool_size`, `max_overflow`, `pool_timeout` in settings.
- **HTTP clients**: Use `httpx.AsyncClient()` with connection limits:
  ```python
  async with httpx.AsyncClient(
      limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
      timeout=httpx.Timeout(30.0),
  ) as client:
      response = await client.get(url)
  ```

### Caching (Redis)

```python
# app/core/cache.py
from redis.asyncio import Redis
from app.core.config import settings

redis_client: Redis | None = None


async def get_redis() -> Redis:
    global redis_client
    if redis_client is None and settings.REDIS_URL:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


async def cache_get(key: str) -> str | None:
    redis = await get_redis()
    if redis:
        return await redis.get(key)
    return None


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    redis = await get_redis()
    if redis:
        await redis.set(key, value, ex=ttl)
```

### Pagination

Always paginate list endpoints:

```python
# app/common/pagination.py
import math
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class PaginatedResponse(BaseModel, Generic[SchemaT]):
    """Standard paginated response wrapper."""
    items: list[SchemaT]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(
        cls, items: list[Any], total: int, page: int, size: int
    ) -> "PaginatedResponse":
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size) if size > 0 else 0,
        )
```

### Rules

1. **Never block the event loop** — use `async`/`await` for all I/O.
2. **Use `asyncio.to_thread()`** for CPU-bound work.
3. **Enable connection pooling** for databases and HTTP clients.
4. **Paginate all list endpoints** — default `page=1, size=20, max_size=100`.
5. **Use eager loading** (`selectinload`, `joinedload`) to avoid N+1 queries.
6. **Cache hot data** in Redis with appropriate TTLs.

---

## 14. Security Hardening

### Input Validation

- **Pydantic models validate ALL input** — no raw `dict` from requests.
- **Set `max_length` on all string fields** to prevent abuse.
- **Whitelist allowed values** with `Literal` or enums.
- **Sanitize file uploads**: validate MIME type, enforce size limits.

### SQL Injection Prevention

- **Always use parameterized queries** (SQLAlchemy handles this by default).
- **Never use `text()` with f-strings**:
  ```python
  # ❌ NEVER
  await session.execute(text(f"SELECT * FROM users WHERE id = '{user_id}'"))

  # ✅ ALWAYS
  await session.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})
  ```

### Rate Limiting

```python
# Using slowapi or custom middleware
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, ...) -> TokenResponse:
    ...
```

### Security Headers

```python
# Add via middleware or reverse proxy
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
```

### Security Checklist (Quick Reference)

- [ ] All endpoints validate input via Pydantic schemas
- [ ] Passwords hashed with bcrypt/argon2 (never plain text)
- [ ] JWT tokens have short expiry (≤30 min for access tokens)
- [ ] Refresh tokens stored securely (httpOnly cookies or DB)
- [ ] CORS restricted to known origins (no `*` in production)
- [ ] Rate limiting on auth endpoints
- [ ] No sensitive data in logs or error responses
- [ ] HTTPS enforced in production
- [ ] SQL injection prevention verified (use parameterized queries)
- [ ] File upload validation (type, size, name sanitization)
- [ ] Dependencies pinned and audited for vulnerabilities

> **Reference**: See `resources/security-checklist.md`

---

## 15. Type Safety

### Full Type Annotations

```python
# ✅ GOOD: Every function, variable, and return type is annotated
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.users.schemas import UserCreate, UserRead

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def create_user(
    user_data: UserCreate,
    db: DbSession,
) -> UserRead:
    ...

# ❌ BAD: Missing annotations
async def create_user(user_data, db):
    ...
```

### Custom Annotated Types

```python
# app/common/types.py
from typing import Annotated
from uuid import UUID

from fastapi import Path, Query
from pydantic import Field

# Path parameter types
ResourceId = Annotated[UUID, Path(description="Resource UUID")]

# Query parameter types
SearchQuery = Annotated[str | None, Query(max_length=255, description="Search term")]
PageNumber = Annotated[int, Query(ge=1, description="Page number")]
PageSize = Annotated[int, Query(ge=1, le=100, description="Items per page")]

# Schema field types
NameField = Annotated[str, Field(min_length=1, max_length=255)]
EmailField = Annotated[str, Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")]
PasswordField = Annotated[str, Field(min_length=8, max_length=128)]
```

### Rules

1. **Annotate everything**: function params, return types, class attributes, variables.
2. **Use `Annotated` types** for reusable parameter/field definitions.
3. **Use `TypeVar` and `Generic`** for base classes (repository, service).
4. **Use `Protocol`** for interface contracts between modules.
5. **Run `mypy` or `pyright`** in strict mode as part of CI.

---

## 16. Testing Strategy

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures (app, client, db, factories)
├── unit/
│   └── modules/
│       ├── users/
│       │   ├── test_service.py
│       │   └── test_schemas.py
│       └── auth/
│           └── test_security.py
└── integration/
    └── modules/
        ├── users/
        │   └── test_router.py
        └── auth/
            └── test_auth_flow.py
```

### Shared Fixtures

```python
# tests/conftest.py
import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import create_app
from app.core.database import Base
from app.core.dependencies import get_db

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
```

### Test Patterns

```python
# tests/integration/modules/users/test_router.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users/",
        json={
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "securepass123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "password" not in data  # Never expose password


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient) -> None:
    # Create first user
    await client.post("/api/v1/users/", json={...})
    # Try duplicate
    response = await client.post("/api/v1/users/", json={...})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
```

### Rules

1. **Test pyramid**: Many unit tests (fast, isolated), fewer integration tests (with DB/client).
2. **Use `pytest-asyncio`** for async test support.
3. **Use `httpx.AsyncClient`** (not `TestClient`) for async endpoint tests.
4. **Override dependencies** in tests via `app.dependency_overrides`.
5. **Each test is independent** — use function-scoped fixtures, clean DB per test.
6. **Test error paths** — not just happy paths.
7. **Target ≥80% coverage**: `pytest --cov=app --cov-report=term-missing`.

> **Reference**: See `examples/testing.py`

---

## 17. API Versioning

### URL Prefix Versioning

```python
# App mounts all v1 routers under /api/v1
API_V1_PREFIX = "/api/v1"
app.include_router(users_router, prefix=f"{API_V1_PREFIX}/users")

# When v2 is needed:
API_V2_PREFIX = "/api/v2"
app.include_router(users_v2_router, prefix=f"{API_V2_PREFIX}/users")
```

### Deprecation Strategy

1. **Mark deprecated endpoints** with `deprecated=True` in router decorator.
2. **Add `Deprecation` header** in response with sunset date.
3. **Maintain v1 for at least 6 months** after v2 release.
4. **Log usage of deprecated endpoints** for migration tracking.

```python
@router.get("/old-endpoint", deprecated=True)
async def old_endpoint() -> dict:
    """Deprecated: Use /api/v2/new-endpoint instead."""
    ...
```

---

## 18. Deployment

### Docker Multi-Stage Build

```dockerfile
# Dockerfile
FROM python:3.14-slim AS base

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# --- Builder stage ---
FROM base AS builder

COPY pyproject.toml ./
RUN pip install --prefix=/install .

# --- Production stage ---
FROM base AS production

COPY --from=builder /install /usr/local
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### docker-compose.yml

```yaml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Uvicorn/Gunicorn Configuration

```python
# For production with Gunicorn + Uvicorn workers:
# gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# CPU-bound formula: workers = (2 × CPU_CORES) + 1
# Memory-bound: adjust based on per-worker memory usage
```

> **Reference**: See `resources/deployment-checklist.md`

---

## 19. Code Style & Conventions

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files & directories | `snake_case` | `user_service.py` |
| Classes | `PascalCase` | `UserService` |
| Functions & methods | `snake_case` | `get_user_by_id` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_PAGE_SIZE` |
| Type aliases | `PascalCase` | `DbSession` |
| Private | `_leading_underscore` | `_validate_email` |
| Environment vars | `UPPER_SNAKE_CASE` | `DATABASE_URL` |

### Import Order

```python
# 1. Standard library
import asyncio
import logging
from datetime import datetime
from uuid import UUID

# 2. Third-party packages
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local application
from app.core.config import settings
from app.core.dependencies import get_db
from app.modules.users.schemas import UserCreate, UserRead
```

### Docstrings

```python
async def create_user(
    user_data: UserCreate,
    db: AsyncSession,
) -> User:
    """Create a new user with hashed password.

    Args:
        user_data: Validated user creation data.
        db: Database session (injected).

    Returns:
        The newly created User instance.

    Raises:
        ConflictError: If a user with the same email already exists.
    """
    ...
```

### Router/Endpoint Conventions

```python
router = APIRouter()

# Use HTTP method decorators with explicit status codes and response models
@router.get("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@router.put("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
@router.patch("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
```

### Git Commit Messages

Use Conventional Commits:

```
feat(users): add email verification endpoint
fix(auth): handle expired refresh tokens gracefully
refactor(database): switch to async session factory
docs(readme): add deployment instructions
test(items): add integration tests for CRUD operations
chore(deps): upgrade SQLAlchemy to 2.0.30
```

---

## 20. Dependency Management

### Required Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    # Web framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",

    # Database
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.30.0",           # PostgreSQL async driver
    "alembic>=1.14.0",            # Migrations

    # Validation & Settings
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "email-validator>=2.2.0",

    # Security
    "pyjwt>=2.9.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.18",   # Form data (OAuth2 login)

    # HTTP Client
    "httpx>=0.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",             # Test client
    "aiosqlite>=0.20.0",         # SQLite async for tests
    "ruff>=0.8.0",               # Linter + formatter
    "mypy>=1.13.0",              # Type checker
    "pre-commit>=4.0.0",
]

redis = [
    "redis[hiredis]>=5.2.0",
]

celery = [
    "celery[redis]>=5.4.0",
]
```

### Tool Configuration

```toml
# pyproject.toml (continued)

[tool.ruff]
target-version = "py314"
line-length = 99

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "S", "T20", "SIM", "RUF"]
ignore = ["S101"]  # Allow assert in tests

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.mypy]
python_version = "3.14"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --tb=short --strict-markers -x"
```

---

## Quick Reference Card

### Creating a New Module

1. Create `app/modules/<name>/` with all files from the [Module Blueprint](#2-module-blueprint)
2. Define models in `models.py` with `BaseModel` as parent
3. Create schemas in `schemas.py` (Base, Create, Update, Read, List)
4. Implement repository in `repository.py` extending `BaseRepository`
5. Implement service in `service.py` (business logic, calls repository)
6. Wire dependencies in `dependencies.py`
7. Define routes in `router.py` (inject service via Depends)
8. Register router in `app/main.py` → `_register_routers()`
9. Generate and apply Alembic migration
10. Write tests in `tests/unit/modules/<name>/` and `tests/integration/modules/<name>/`

> **See**: `resources/module-checklist.md` for the full checklist.

### Command Cheat Sheet

```bash
# Run development server
uvicorn main:app --reload

# Run tests
pytest
pytest --cov=app --cov-report=term-missing

# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Lint & format
ruff check app/ tests/
ruff format app/ tests/

# Type check
mypy app/
```