# Login Feature — Sub-Tasks

## T1: Schema Layer — Sub-Tasks

### T1.1: LoginRequest
- Define `email` field with `EmailStr` type
- Define `password` field with `min_length=8, max_length=72`
- Password max 72 chars because bcrypt silently truncates beyond that
- Add descriptive field descriptions for OpenAPI docs

### T1.2: LoginResponse
- Include `message` (str) for human-readable status
- Include `access_token` (str) and `refresh_token` (str)
- Include `token_type` with default `"bearer"`
- Include `user: UserBasicResponse` — reuse existing response schema

---

## T2: Exception Layer — Sub-Tasks

### T2.1: InvalidCredentialsException
- Inherit from `UnauthorizedException` → maps to HTTP 401
- Message: "Invalid email or password" (deliberately generic)
- Used for BOTH non-existent email AND wrong password

### T2.2: AccountDisabledException
- Inherit from `ForbiddenException` → maps to HTTP 403
- Message: "Account is disabled. Please contact support."
- Triggered when `user.is_active = false`

### T2.3: EmailNotVerifiedException
- Inherit from `ForbiddenException` → maps to HTTP 403
- Message: "Email address is not verified. Please check your inbox for the OTP."
- Triggered when `user.email_verified = false`

---

## T3: Repository Layer — Sub-Tasks

### T3.1: UserRepository.update_last_login()
- Accept `user_id: UUID` and `logged_in_at: datetime`
- Execute `UPDATE users SET last_login_at = :logged_in_at WHERE user_id = :user_id`
- Call `flush()` to push changes within the transaction

### T3.2: NgoRepository.get_profile_by_ngo_id()
- Accept `ngo_id: UUID`
- Execute `SELECT * FROM ngo_profiles WHERE ngo_id = :ngo_id`
- Return `NgoProfile | None`
- Used to populate `org_name` and `verification_status` in login response

---

## T4: Service Layer — Sub-Tasks

### T4.1: login() Method Flow
1. Look up user by email → `_user_repo.get_by_email()`
2. Run password check (timing-safe) → `_check_password()`
3. If user is None or password wrong → raise `InvalidCredentialsException`
4. Validate account active → `_validate_account_active()`
5. Validate email verified → `_validate_email_verified()`
6. Generate tokens with user's role → `_generate_tokens(user_id, role=user.role)`
7. Update last_login_at → `_user_repo.update_last_login()`
8. Store refresh token → `_store_refresh_token()`
9. Fetch NGO profile → `_ngo_repo.get_profile_by_ngo_id()`
10. Build and return `LoginResponse`

### T4.2: Timing-Safe Password Check
- When user is `None`, use dummy hash: `$2b$12$invalidhashpadding000000000000000`
- This ensures bcrypt always runs, preventing timing-based user detection
- `_check_password()` delegates to `verify_password()` from `core/security.py`

### T4.3: Dynamic _generate_tokens()
- Changed signature from `(user_id)` to `(user_id, *, role: str)`
- Role is now a keyword-only argument for clarity
- Updated `_complete_verification()` to pass `role=_ROLE_NGO_USER`
- Login passes `role=user.role` (reads from DB)

---

## T5: Controller Layer — Sub-Tasks

### T5.1: Endpoint Definition
- Route: `POST /auth/login`
- Response model: `LoginResponse`
- Rate limit: `10/minute` via `@limiter.limit()`

### T5.2: Request Processing
- Extract `ip_address` from `request.client.host`
- Extract `user_agent` from `request.headers.get("user-agent")`
- Delegate to `service.login(data, ip_address, user_agent)`

### T5.3: Import Updates
- Add `LoginRequest` and `LoginResponse` to controller imports
