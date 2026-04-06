# Security Audit Checklist

Use this checklist when reviewing API endpoints, auth flows, and data handling for security vulnerabilities.

---

## Authentication & Authorization

- [ ] All protected endpoints require `Depends(get_current_user)` or `Depends(require_role(...))`
- [ ] JWT access tokens have short expiry (≤ 30 minutes)
- [ ] Refresh tokens have reasonable expiry (≤ 90 days)
- [ ] Token validation checks `type` claim ("access" vs "refresh")
- [ ] Expired/invalid tokens return 401 with `WWW-Authenticate: Bearer` header
- [ ] Password hashing uses bcrypt or argon2 (never MD5/SHA)
- [ ] Password requirements enforced: min 8 chars, mixed case, digits
- [ ] Login endpoint has rate limiting (≤ 5 attempts/minute per IP)
- [ ] No sensitive data in JWT payload (no passwords, PII, secrets)
- [ ] Role-based access control tested for all privilege levels

## Input Validation

- [ ] All request bodies validated via Pydantic schemas
- [ ] String fields have `max_length` constraints
- [ ] Numeric fields have `ge`, `le`, `gt`, `lt` bounds
- [ ] Enum/Literal types used where values are constrained
- [ ] Email fields use `EmailStr` validator
- [ ] URL fields use `HttpUrl` validator
- [ ] File uploads validate: MIME type, max size, filename sanitization
- [ ] No raw `dict` or `Any` types in request models
- [ ] Path parameters use `UUID` type (not bare strings)

## SQL & Data Safety

- [ ] All queries use SQLAlchemy ORM or parameterized `text()` queries
- [ ] NO f-strings or string concatenation in SQL
- [ ] Eager loading used where needed (no N+1 queries)
- [ ] Sensitive fields (passwords, tokens) are never returned in API responses
- [ ] Soft-deleted records excluded from standard queries
- [ ] Database user has minimal required permissions (not superuser)

## API Security

- [ ] CORS origins restricted to known domains (no `*` in production)
- [ ] `Strict-Transport-Security` header set (HTTPS enforced)
- [ ] `X-Content-Type-Options: nosniff` header set
- [ ] `X-Frame-Options: DENY` header set
- [ ] `Content-Security-Policy` header set
- [ ] `Referrer-Policy` header set
- [ ] API docs (`/docs`, `/redoc`, `/openapi.json`) disabled in production
- [ ] Request ID tracked for all requests
- [ ] Error responses never expose stack traces or internal details

## Secrets Management

- [ ] All secrets stored in `.env` file or secrets manager
- [ ] `.env` is in `.gitignore`
- [ ] `.env.example` exists with all keys (no real values)
- [ ] `SecretStr` used for secret fields in Settings
- [ ] No hardcoded secrets, tokens, or API keys in source code
- [ ] Secret key is cryptographically random (≥ 32 bytes)
- [ ] Different secrets per environment (dev ≠ staging ≠ production)

## Logging & Monitoring

- [ ] Authentication failures logged with IP and timestamp
- [ ] Rate limit hits logged
- [ ] 5xx errors logged with full stack trace (server-side only)
- [ ] No passwords, tokens, or PII in log output
- [ ] Request IDs included in all log entries
- [ ] Health endpoints exposed for monitoring (not auth-protected)

## Dependencies

- [ ] All dependencies pinned to specific versions
- [ ] `pip audit` or `safety check` run (no known vulnerabilities)
- [ ] Unused dependencies removed
- [ ] Docker base image uses specific version tag (not `latest`)
- [ ] Non-root user in Docker container

## Network

- [ ] Database connections use TLS/SSL in production
- [ ] Redis connections use TLS in production
- [ ] External HTTP calls use timeouts and connection limits
- [ ] Trusted host middleware configured in production
