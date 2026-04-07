# Login Feature — Research Notes

## 1. Codebase Analysis

### Existing Architecture (Develop branch)
- **Pattern**: Controller → Service → Repository (clean layering)
- **Auth module** already implements: `register`, `verify-otp`, `resend-otp`
- **DI wiring**: via `dependencies.py` using FastAPI `Depends()` chain
- **Exception handling**: Centralized in `core/exception_handlers.py`, maps domain exceptions → HTTP
- **Security**: All crypto in `core/security.py` (bcrypt, SHA-256, JWT via python-jose)

### Database Schema
- `users` table: has `last_login_at` column (NULL by default, set on first login)
- `auth_refresh_tokens`: stores hashed refresh tokens with session tracking
- `ngo_profiles`: linked 1:1 to users via `ngo_id` FK
- User roles: enum `('admin', 'ngo_user')` — set at registration

### Existing `feature/login-api` Branch
- A team member's partial implementation found on remote
- Audited and found to be clean, follows existing patterns
- Changes: +175 lines across 6 files
- Design decisions aligned with registration patterns
- Used as reference for our implementation

## 2. Frontend Analysis

### Frontend Repository (`front-end-ClimasyncAI`)
- **Framework**: Next.js with TypeScript and Tailwind CSS
- **Status**: Fresh scaffold — only `page.tsx` with default Next.js content
- **No login page exists** — backend defines the API contract
- **CORS**: Backend already allows `http://localhost:3000`

## 3. Security Research

### Password Verification Timing Attack
- Problem: If we skip `bcrypt.checkpw()` when user is not found, an attacker can detect valid emails by measuring response time
- Solution: Always run bcrypt against a dummy hash when user is None
- Dummy hash: `$2b$12$invalidhashpadding000000000000000` (valid bcrypt format, will never match)

### User Enumeration Prevention
- Problem: Different error messages for "email not found" vs "wrong password" leak information
- Solution: Single generic error: "Invalid email or password" for both cases
- Implementation: `InvalidCredentialsException` with generic detail

### Rate Limiting
- Endpoint-level: 10/min per IP via slowapi `@limiter.limit("10/minute")`
- Complements the existing `/register` (10/min) and `/resend-otp` (5/min) limits

## 4. JWT Token Design

### Current Implementation
- Access token: 30 min expiry, contains `sub` (user_id), `role`, `type: "access"`
- Refresh token: 7 day expiry, contains `sub` (user_id), `type: "refresh"`
- Algorithm: HS256 with configurable secret

### Scalability Decision: Dynamic Role
- **Before**: `_generate_tokens()` hardcoded `role='ngo_user'` in JWT claims
- **After**: `_generate_tokens(user_id, *, role: str)` reads role from user model
- **Impact**: Admin login requires zero code changes — just different DB role

## 5. Future Extensibility Notes

### Adding Social Auth (OAuth2)
- New methods can be added to `AuthService` (e.g., `login_with_google()`)
- Shared helpers: `_generate_tokens()`, `_store_refresh_token()`, `_validate_account_active()`
- New schemas: `SocialLoginRequest`, `SocialLoginResponse`
- New controller endpoints: `POST /auth/login/google`, `POST /auth/login/github`
- No existing code needs modification — only additions

### Adding Password Reset
- `auth_token_purpose` enum already supports `'password_reset'`
- `VerificationTokenRepository` can be reused with different purpose
- New service method: `request_password_reset()`, `reset_password()`
