# ClimaSync.AI Backend — Constitution

## Project Overview
ClimaSync.AI is an Agentic AI-based disaster management system. This backend serves the API layer for NGO registration, authentication, and future disaster response coordination.

## Technology Stack
- **Language**: Python 3.14+ (managed by `uv`)
- **Framework**: FastAPI with async support
- **ORM**: SQLAlchemy 2.0+ (async mode via `asyncpg`)
- **Database**: PostgreSQL (Supabase / AWS RDS)
- **Validation**: Pydantic v2 with `pydantic-settings`
- **Password Hashing**: bcrypt (via `bcrypt` package directly)
- **JWT**: `python-jose[cryptography]`
- **Rate Limiting**: `slowapi`
- **Email**: `aiosmtplib` (async SMTP)

## Architecture Principles

### 1. Layered Architecture
```
Controller → Service → Repository → Models
     ↑            ↑           ↑
  HTTP only    Business    SQL only
  concerns    logic only   concerns
```

- **Controllers** handle only HTTP: request parsing, status codes, response shaping
- **Services** contain all business logic; never import FastAPI or database sessions
- **Repositories** contain only SQL queries; no business decisions
- **Models** define the SQLAlchemy ORM mappings

### 2. Dependency Injection
- FastAPI `Depends()` chain wires repositories → services → controllers
- Each module has a `dependencies.py` file for DI wiring
- Type aliases (e.g., `AuthServiceDep`) keep controller signatures clean

### 3. Exception Hierarchy
- All domain exceptions inherit from `AppException` in `core/exceptions.py`
- Module-specific exceptions live in their own `exceptions.py`
- Exception → HTTP mapping happens ONLY in `core/exception_handlers.py`
- Controllers NEVER catch domain exceptions

### 4. Async Everything
- All database operations use `async/await`
- Email sending is async via `aiosmtplib`
- No blocking I/O in the request path

### 5. Security First
- Passwords: bcrypt with 72-byte truncation
- OTP: bcrypt hash (constant-time comparison)
- Refresh tokens: SHA-256 hash in DB
- JWT: HS256 with configurable secret and expiry
- No secrets in code — all via `.env` / environment variables

### 6. Configuration via Environment
- All settings in `core/config.py` using `pydantic-settings`
- Never use `os.environ` directly
- `.env` file for local development

### 7. Scalable Module Design
- Modules are self-contained under `app/modules/<name>/`
- Each module has: `models.py`, `schemas.py`, `repository.py`, `service.py`, `controller.py`, `dependencies.py`, `exceptions.py`
- New features (e.g., social auth, password reset) add new methods/modules without modifying existing code

## Code Standards
- Type hints on all function signatures
- Docstrings on all public methods
- `Mapped[]` with `mapped_column()` for SQLAlchemy models (modern style)
- `BaseSchema` with `from_attributes=True` for all Pydantic models
- Private methods prefixed with `_`
- Module-level constants in `SCREAMING_SNAKE_CASE`

## Git Workflow
- `main` — production-ready code
- `Develop` — integration branch
- `feature/<name>` — feature branches from Develop
- Merge to Develop after code review
