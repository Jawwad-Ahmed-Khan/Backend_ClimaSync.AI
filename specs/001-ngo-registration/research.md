# Research: NGO Registration

## Decision: Async Email via `aiosmtplib`
- **Rationale**: The project requires non-blocking email delivery. `aiosmtplib` is the standard async wrapper for SMTP.
- **Implementation**: Will be isolated in `app/modules/auth/email.py`.
- **Alternatives Considered**: SendGrid SDK (synchronous by default), FastAPI background tasks with synchronous SMTP (viable but less performant for high volumes).

## Decision: Rate Limiting via `slowapi`
- **Rationale**: `slowapi` provides a decorator-based approach for FastAPI. It supports IP-based limiting and integrates easily with global settings.
- **Implementation**: Applied to `/auth/register` and `/auth/resend-otp` endpoints (5 requests/hour).
- **Alternatives Considered**: Custom middleware (manual), Redis-based rate limiting (too complex for MVP).

## Decision: OTP Hashing with `bcrypt`
- **Rationale**: Even short strings should be hashed before storage to prevent leakage from database snapshots. `bcrypt` (via `passlib`) is already used for passwords.
- **Implementation**: 6-digit OTP will be hashed before storage in `auth_verification_tokens.token_hash`.
- **Alternatives Considered**: SHA-256 (not salted by default), storing in plaintext (unsecure).

## Decision: Transactional Profile Creation
- **Rationale**: OTP verification, user status update, NGO profile creation, and default resource creation must occur in a single atomic database transaction.
- **Implementation**: Using `AsyncSession.begin()` context manager in the service layer, passing the session to repositories.
- **Alternatives Considered**: Multiple sequential calls (risk of partial data creation on failure).

## Decision: Database Migration Strategy
- **Rationale**: Supabase is a managed PostgreSQL service. Migration to AWS RDS only requires updating `DATABASE_URL`.
- **Implementation**: No changes to application logic. Alembic will manage schema changes via standard PostgreSQL syntax.
- **AWS Considerations**: Use `sslmode=require` for AWS RDS connections.
