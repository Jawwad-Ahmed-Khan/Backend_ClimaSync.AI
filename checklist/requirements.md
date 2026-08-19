# Login Feature — Requirements

## Functional Requirements

### FR-1: Email/Password Authentication
- Users with a verified email and active account can login using `POST /api/v1/auth/login`
- Request body: `{ email, password }`
- Returns: JWT access token, refresh token, user profile summary

### FR-2: Security — Timing-Safe Password Check
- Password verification must use constant-time comparison (bcrypt)
- When a user is not found, a dummy hash must be processed to prevent timing-based enumeration

### FR-3: Security — Generic Error Messages
- Invalid email or wrong password must return **the same** error message: "Invalid email or password"
- This prevents user enumeration attacks

### FR-4: Account Status Validation
- Login must fail with `403` if `is_active = false`
- Login must fail with `403` if `email_verified = false`

### FR-5: Last Login Tracking
- On successful login, `users.last_login_at` must be updated to `now()`

### FR-6: Refresh Token Storage
- A new SHA-256 hashed refresh token is stored in `auth_refresh_tokens` table
- IP address and user-agent are captured from the request

### FR-7: Rate Limiting
- Login endpoint is rate-limited to 10 requests/minute per IP

### FR-8: Dynamic Role in JWT
- The JWT `role` claim must be read from the user's DB record, not hardcoded
- This supports future admin login without code changes

## Non-Functional Requirements

### NFR-1: Scalability
- The auth service architecture must support adding new auth strategies (social/OAuth) as new methods without modifying existing code

### NFR-2: Response Time
- Login should complete in < 500ms (bcrypt is the bottleneck at ~100ms)

### NFR-3: No Schema Migration Needed
- Login uses only existing DB columns (`users.last_login_at`, `auth_refresh_tokens`)

## Acceptance Criteria

- [ ] `POST /api/v1/auth/login` returns 200 with tokens on valid credentials
- [ ] Returns 401 for wrong email or password (same message for both)
- [ ] Returns 403 for disabled accounts
- [ ] Returns 403 for unverified emails
- [ ] Returns 429 when rate limit exceeded
- [ ] `last_login_at` updated after successful login
- [ ] Refresh token stored with SHA-256 hash
- [ ] JWT contains correct role from user record
