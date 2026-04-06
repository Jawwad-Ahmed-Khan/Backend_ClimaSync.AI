# NGO Registration API — Complete Backend Specification

> **Purpose:** Everything a backend developer needs to implement the NGO registration flow in FastAPI.
> Maps: Frontend Form → API Endpoints → Service Logic → Database Tables

---

## 1. Registration Flow Overview

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as FastAPI
    participant SVC as AuthService
    participant DB as PostgreSQL

    FE->>API: POST /auth/register
    Note right of FE: { org_name, email, password }
    API->>SVC: register_ngo(data)
    SVC->>DB: Check email uniqueness (users)
    SVC->>DB: INSERT into users (unverified)
    Note right of DB: email_verified = false
    SVC->>DB: INSERT into auth_verification_tokens
    SVC-->>FE: Send OTP email
    SVC-->>API: { message, email }
    API-->>FE: 201 Created

    FE->>API: POST /auth/verify-otp
    Note right of FE: { email, otp }
    API->>SVC: verify_otp(email, otp)
    SVC->>DB: Find open token by email + purpose
    SVC->>DB: Compare hash, check expiry/attempts
    SVC->>DB: Mark token used_at = now()
    SVC->>DB: UPDATE users SET email_verified = true
    SVC->>DB: INSERT into ngo_profiles
    SVC->>DB: INSERT into ngo_resources (defaults)
    SVC->>DB: Generate JWT access + refresh tokens
    SVC->>DB: INSERT into auth_refresh_tokens
    API-->>FE: 200 OK { tokens, user }

    FE->>API: POST /auth/resend-otp
    Note right of FE: { email }
    API->>SVC: resend_otp(email)
    SVC->>DB: Rate limit check
    SVC->>DB: Revoke old tokens
    SVC->>DB: INSERT new auth_verification_token
    SVC-->>FE: Send new OTP email
    API-->>FE: 200 OK { message }
```

---

## 2. Database Tables Involved

### Step 1 (Register) touches:
| Table | Operation | Auto-triggered |
|---|---|---|
| `users` | INSERT | — |
| `notification_preferences` | INSERT | ✅ Auto via trigger `trg_create_default_notification_preferences` |
| `auth_verification_tokens` | INSERT | — |

### Step 2 (Verify OTP) touches:
| Table | Operation | Auto-triggered |
|---|---|---|
| `auth_verification_tokens` | UPDATE (attempts / used_at) | — |
| `users` | UPDATE (email_verified, email_verified_at) | — |
| `ngo_profiles` | INSERT | — |
| `ngo_resources` | INSERT (all defaults = 0) | — |
| `auth_refresh_tokens` | INSERT | — |

---

## 3. Exact Column Mappings

### 3.1 `users` table — INSERT on register

```
user_id              → gen_random_uuid()          [auto by DB]
email                → request.email              [citext, validated]
password_hash        → bcrypt(request.password)   [>= 60 chars]
role                 → 'ngo_user'                 [hardcoded enum]
is_active            → true                       [default]
email_verified       → false                      [default, set true on OTP verify]
email_verified_at    → NULL                       [set on OTP verify]
last_login_at        → NULL                       [set on first login]
password_changed_at  → now()                      [default]
created_at           → now()                      [default]
updated_at           → now()                      [default]
deleted_at           → NULL                       [default]
```

### 3.2 `auth_verification_tokens` table — INSERT on register

```
verification_token_id → gen_random_uuid()          [auto]
user_id               → newly_created_user.user_id
email                 → request.email
purpose               → 'email_verification'       [enum]
token_hash            → bcrypt(otp_plaintext)       [hash the 6-digit OTP]
expires_at            → now() + interval '10 minutes' [configurable via env]
used_at               → NULL
revoked_at            → NULL
attempts_count        → 0
max_attempts          → 5                           [configurable via env]
created_at            → now()
updated_at            → now()
```

> **DB Constraint:** `idx_verification_tokens_one_open` ensures only ONE open (unused + unrevoked) token per user+purpose at a time. Before inserting a new token, revoke any existing open token first.

### 3.3 `ngo_profiles` table — INSERT on OTP verification

```
ngo_id              → verified_user.user_id        [FK to users.user_id]
org_name            → request.org_name             [from registration form]
org_email           → verified_user.email          [copy from users.email initially]
registration_number → auto-generate or leave NULL  [SEE QUESTION BELOW]
head_of_operations  → NULL                         [filled later in profile]
phone               → NULL                         [filled later]
phone_verified      → false
logo_url            → NULL
website             → NULL
base_city           → NULL                         [filled later in Areas page]
base_district       → NULL
base_province       → NULL
base_location       → NULL                         [filled later]
service_radius_km   → 10                           [default]
verification_status → 'pending'                    [admin verifies later]
verified_by         → NULL
verified_at         → NULL
suspended_reason    → NULL
rating              → 0.0
created_at          → now()
updated_at          → now()
deleted_at          → NULL
```

> **DB Trigger:** `trg_validate_ngo_profile_user_role` runs on INSERT and confirms the user has `role = 'ngo_user'` and `deleted_at IS NULL`.

### 3.4 `ngo_resources` table — INSERT on OTP verification

```
ngo_id                → verified_user.user_id      [FK to ngo_profiles.ngo_id]
ambulances            → 0     [all defaults]
rescue_boats          → 0
trucks                → 0
four_wheel_vehicles   → 0
cranes                → 0
doctors               → 0
paramedics            → 0
rescue_divers         → 0
volunteers_available  → 0
food_packets_capacity → 0
shelter_capacity      → 0
created_at            → now()
updated_at            → now()
```

### 3.5 `auth_refresh_tokens` table — INSERT on OTP verification (after generating JWT)

```
refresh_token_id → gen_random_uuid()
user_id          → verified_user.user_id
session_id       → gen_random_uuid()               [new session]
token_hash       → sha256(refresh_token_plaintext)  [hash before storing]
parent_token_id  → NULL                             [first token in chain]
issued_at        → now()
expires_at       → now() + interval '7 days'        [configurable via env]
last_used_at     → NULL
revoked_at       → NULL
revoke_reason    → NULL
ip_address       → request.client.host              [from FastAPI Request]
user_agent       → request.headers["user-agent"]
created_at       → now()
updated_at       → now()
```

---

## 4. Pydantic Schemas

### Request Schemas

```python
# app/modules/auth/schemas.py

class RegisterNgoRequest(BaseSchema):
    """POST /auth/register body"""
    org_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

class VerifyOtpRequest(BaseSchema):
    """POST /auth/verify-otp body"""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$')

class ResendOtpRequest(BaseSchema):
    """POST /auth/resend-otp body"""
    email: EmailStr
```

### Response Schemas

```python
class RegisterResponse(BaseSchema):
    """201 response after registration"""
    message: str          # "OTP sent to your email"
    email: str            # echo back the email

class VerifyOtpResponse(BaseSchema):
    """200 response after OTP verification"""
    message: str                    # "Email verified successfully"
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserBasicResponse

class UserBasicResponse(BaseSchema):
    """User data returned in auth responses"""
    user_id: UUID
    email: str
    role: str                       # "ngo_user"
    org_name: str
    is_active: bool
    email_verified: bool
    verification_status: str        # "pending"
```

---

## 5. SQLAlchemy Models

### User Model (already in your structure)

```python
# app/modules/users/models.py

class User(Base):
    __tablename__ = "users"

    user_id            = Column(UUID, primary_key=True, server_default=text("gen_random_uuid()"))
    email              = Column(Text, nullable=False)  # citext handled by DB
    password_hash      = Column(Text, nullable=False)
    role               = Column(Text, nullable=False)   # 'admin' | 'ngo_user'
    is_active          = Column(Boolean, nullable=False, server_default=text("true"))
    email_verified     = Column(Boolean, nullable=False, server_default=text("false"))
    email_verified_at  = Column(DateTime(timezone=True))
    last_login_at      = Column(DateTime(timezone=True))
    password_changed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    updated_at         = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at         = Column(DateTime(timezone=True))

    # Relationships
    ngo_profile = relationship("NgoProfile", back_populates="user", uselist=False)
```

### Auth Verification Token Model

```python
# app/modules/auth/models.py

class AuthVerificationToken(Base):
    __tablename__ = "auth_verification_tokens"

    verification_token_id = Column(UUID, primary_key=True, server_default=text("gen_random_uuid()"))
    user_id        = Column(UUID, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    email          = Column(Text, nullable=False)
    purpose        = Column(Text, nullable=False)     # 'email_verification' | 'password_reset'
    token_hash     = Column(Text, nullable=False)
    expires_at     = Column(DateTime(timezone=True), nullable=False)
    used_at        = Column(DateTime(timezone=True))
    revoked_at     = Column(DateTime(timezone=True))
    attempts_count = Column(SmallInteger, nullable=False, server_default=text("0"))
    max_attempts   = Column(SmallInteger, nullable=False, server_default=text("5"))
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), server_default=func.now())
```

### NGO Profile Model (new module: `app/modules/ngo/models.py`)

```python
# app/modules/ngo/models.py

class NgoProfile(Base):
    __tablename__ = "ngo_profiles"

    ngo_id              = Column(UUID, ForeignKey("users.user_id", ondelete="RESTRICT"), primary_key=True)
    org_name            = Column(String(255), nullable=False)
    org_email           = Column(Text, nullable=False)
    registration_number = Column(String(100), nullable=False, unique=True)
    head_of_operations  = Column(String(255))
    phone               = Column(String(20))
    phone_verified      = Column(Boolean, nullable=False, server_default=text("false"))
    logo_url            = Column(Text)
    website             = Column(Text)
    base_city           = Column(String(100))
    base_district       = Column(String(100))
    base_province       = Column(String(100))
    base_location       = Column(Geography("POINT", srid=4326))
    service_radius_km   = Column(Integer, nullable=False, server_default=text("10"))
    verification_status = Column(Text, nullable=False, server_default=text("'pending'"))
    verified_by         = Column(UUID, ForeignKey("users.user_id", ondelete="SET NULL"))
    verified_at         = Column(DateTime(timezone=True))
    suspended_reason    = Column(Text)
    rating              = Column(Numeric(2, 1), nullable=False, server_default=text("0.0"))
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at          = Column(DateTime(timezone=True))

    # Relationships
    user      = relationship("User", back_populates="ngo_profile", foreign_keys=[ngo_id])
    resources = relationship("NgoResource", back_populates="ngo_profile", uselist=False)


class NgoResource(Base):
    __tablename__ = "ngo_resources"

    ngo_id                = Column(UUID, ForeignKey("ngo_profiles.ngo_id", ondelete="CASCADE"), primary_key=True)
    ambulances            = Column(Integer, nullable=False, server_default=text("0"))
    rescue_boats          = Column(Integer, nullable=False, server_default=text("0"))
    trucks                = Column(Integer, nullable=False, server_default=text("0"))
    four_wheel_vehicles   = Column(Integer, nullable=False, server_default=text("0"))
    cranes                = Column(Integer, nullable=False, server_default=text("0"))
    doctors               = Column(Integer, nullable=False, server_default=text("0"))
    paramedics            = Column(Integer, nullable=False, server_default=text("0"))
    rescue_divers         = Column(Integer, nullable=False, server_default=text("0"))
    volunteers_available  = Column(Integer, nullable=False, server_default=text("0"))
    food_packets_capacity = Column(Integer, nullable=False, server_default=text("0"))
    shelter_capacity      = Column(Integer, nullable=False, server_default=text("0"))
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), server_default=func.now())

    ngo_profile = relationship("NgoProfile", back_populates="resources")
```

---

## 6. Service Logic — Step-by-Step Pseudocode

### 6.1 `register_ngo(data: RegisterNgoRequest)`

```
FUNCTION register_ngo(org_name, email, password):

    1. VALIDATE email format (Pydantic handles this)

    2. CHECK email uniqueness:
       SELECT user_id FROM users
       WHERE email = :email AND deleted_at IS NULL
       → If found AND email_verified = true:
           RAISE AlreadyExistsException("Email already registered")
       → If found AND email_verified = false:
           # User started registration but never verified
           # Option A: Delete old user, create new one
           # Option B: Reuse existing user, send new OTP
           # RECOMMENDED: Option B (reuse + resend OTP)
           REVOKE any open verification tokens for this user
           GENERATE new OTP → hash it → INSERT new token
           SEND OTP email
           RETURN { message: "OTP resent", email }

    3. HASH password:
       password_hash = bcrypt.hash(password)
       # Result is 60 chars, passes DB constraint

    4. INSERT user (within transaction):
       INSERT INTO users (email, password_hash, role)
       VALUES (:email, :password_hash, 'ngo_user')
       RETURNING user_id
       # → notification_preferences auto-created by DB trigger

    5. STORE org_name temporarily:
       # org_name is NOT in users table — it goes to ngo_profiles
       # But ngo_profiles is created AFTER OTP verification
       # OPTIONS:
       #   A. Store org_name in a temporary column/cache (Redis/memory)
       #   B. Store org_name in auth_verification_tokens as JSONB metadata
       #   C. Accept org_name again during OTP verification
       #   D. Add a pending_org_name column to users table
       #
       # RECOMMENDED: Option C — Accept org_name in verify-otp request
       # This is simplest and stateless. Frontend sends org_name again.

    6. GENERATE OTP:
       otp_plain = generate_secure_6_digit_otp()  # e.g. "847291"
       otp_hash  = bcrypt.hash(otp_plain)

    7. REVOKE any existing open tokens:
       UPDATE auth_verification_tokens
       SET revoked_at = now()
       WHERE user_id = :user_id
         AND purpose = 'email_verification'
         AND used_at IS NULL AND revoked_at IS NULL

    8. INSERT verification token:
       INSERT INTO auth_verification_tokens
       (user_id, email, purpose, token_hash, expires_at)
       VALUES (:user_id, :email, 'email_verification', :otp_hash,
               now() + interval '10 minutes')

    9. SEND OTP email (async, don't block):
       await send_otp_email(email, otp_plain, org_name)

   10. RETURN RegisterResponse:
       { message: "Verification OTP sent to your email", email: email }
```

### 6.2 `verify_otp(data: VerifyOtpRequest)`

```
FUNCTION verify_otp(email, otp, org_name):

    1. FIND open verification token:
       SELECT * FROM auth_verification_tokens
       WHERE email = :email
         AND purpose = 'email_verification'
         AND used_at IS NULL
         AND revoked_at IS NULL
       ORDER BY created_at DESC
       LIMIT 1

       → If not found:
           RAISE ValidationException("No pending verification found")

    2. CHECK expiry:
       IF token.expires_at < now():
           RAISE OtpExpiredException("OTP has expired. Please request a new one.")

    3. CHECK attempts:
       IF token.attempts_count >= token.max_attempts:
           RAISE OtpMaxAttemptsException("Too many attempts. Request a new OTP.")

    4. VERIFY OTP hash:
       IF NOT bcrypt.verify(otp, token.token_hash):
           # Increment attempts
           UPDATE auth_verification_tokens
           SET attempts_count = attempts_count + 1
           WHERE verification_token_id = :token_id
           RAISE OtpInvalidException("Invalid OTP code")

    5. === BEGIN TRANSACTION (all-or-nothing) ===

    6. MARK token as used:
       UPDATE auth_verification_tokens
       SET used_at = now()
       WHERE verification_token_id = :token_id

    7. VERIFY user email:
       UPDATE users
       SET email_verified = true,
           email_verified_at = now()
       WHERE user_id = :token.user_id

    8. CREATE ngo_profile:
       INSERT INTO ngo_profiles (ngo_id, org_name, org_email, registration_number)
       VALUES (
           :token.user_id,
           :org_name,
           :email,
           generate_registration_number()  -- e.g. "NGO-2026-00001"
       )
       # → DB trigger validates user role = 'ngo_user'

    9. CREATE ngo_resources (all defaults):
       INSERT INTO ngo_resources (ngo_id) VALUES (:token.user_id)
       # → All 11 resource columns default to 0

   10. GENERATE tokens:
       access_token  = create_jwt(user_id, role='ngo_user', exp=15min)
       refresh_token = create_jwt(user_id, type='refresh', exp=7days)

   11. STORE refresh token:
       INSERT INTO auth_refresh_tokens
       (user_id, token_hash, expires_at, ip_address, user_agent)
       VALUES (
           :user_id,
           sha256(:refresh_token),
           now() + interval '7 days',
           :request.client.host,
           :request.headers["user-agent"]
       )

   12. === COMMIT TRANSACTION ===

   13. RETURN VerifyOtpResponse:
       {
           message: "Email verified successfully",
           access_token, refresh_token, token_type: "bearer",
           user: { user_id, email, role, org_name, is_active, email_verified, verification_status }
       }
```

### 6.3 `resend_otp(data: ResendOtpRequest)`

```
FUNCTION resend_otp(email):

    1. FIND user:
       SELECT * FROM users
       WHERE email = :email AND deleted_at IS NULL
       → If not found: RAISE NotFoundException
       → If email_verified = true: RAISE ValidationException("Already verified")

    2. RATE LIMIT check:
       SELECT COUNT(*) FROM auth_verification_tokens
       WHERE user_id = :user_id
         AND purpose = 'email_verification'
         AND created_at > now() - interval '1 hour'
       → If count >= 5: RAISE OtpRateLimitException

    3. REVOKE existing open tokens:
       UPDATE auth_verification_tokens
       SET revoked_at = now()
       WHERE user_id = :user_id
         AND purpose = 'email_verification'
         AND used_at IS NULL AND revoked_at IS NULL

    4. GENERATE + INSERT new token (same as register step 6-8)

    5. SEND email (async)

    6. RETURN { message: "New OTP sent to your email" }
```

---

## 7. Controller Endpoints

```python
# app/modules/auth/controller.py

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", status_code=201, response_model=RegisterResponse)
async def register(
    data: RegisterNgoRequest,
    service: AuthServiceDep,
) -> RegisterResponse:
    """Register a new NGO. Sends OTP to email."""
    return await service.register_ngo(data)


@router.post("/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(
    data: VerifyOtpRequest,
    request: Request,
    service: AuthServiceDep,
) -> VerifyOtpResponse:
    """Verify OTP and complete registration. Creates NGO profile."""
    return await service.verify_otp(data, request)


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp(
    data: ResendOtpRequest,
    service: AuthServiceDep,
) -> MessageResponse:
    """Resend verification OTP. Rate limited to 5/hour."""
    return await service.resend_otp(data)
```

---

## 8. Validation Rules

| Field | Rule | Where Enforced |
|---|---|---|
| `email` | Valid email format | Pydantic `EmailStr` |
| `email` | Case-insensitive unique among active users | DB partial unique index `idx_users_email_unique_active` |
| `password` | 8-128 characters | Pydantic `Field(min_length=8, max_length=128)` |
| `password_hash` | ≥ 60 characters | DB CHECK `users_password_hash_length_chk` |
| `org_name` | 1-255 characters, non-empty after trim | Pydantic + DB CHECK `ngo_profiles_org_name_chk` |
| `otp` | Exactly 6 digits | Pydantic `pattern=r'^\d{6}$'` |
| `otp` | Not expired | Service logic: `token.expires_at < now()` |
| `otp` | Max 5 wrong attempts | Service logic: `token.attempts_count >= max_attempts` |
| `otp` | Rate limit: max 5 OTPs per hour | Service logic: count recent tokens |
| `role` | Must be `'ngo_user'` for registration | Hardcoded in service |
| `ngo_profiles.ngo_id` | Must reference user with `role='ngo_user'` | DB trigger `trg_validate_ngo_profile_user_role` |

---

## 9. Error Responses

| Scenario | Exception | HTTP | Response Body |
|---|---|---|---|
| Email already registered (verified) | `AlreadyExistsException` | 409 | `{ "detail": "Email already registered" }` |
| OTP expired | `OtpExpiredException` → `ValidationException` | 422 | `{ "detail": "OTP has expired" }` |
| Wrong OTP code | `OtpInvalidException` → `UnauthorizedException` | 401 | `{ "detail": "Invalid OTP code" }` |
| Max OTP attempts reached | `OtpMaxAttemptsException` → `ForbiddenException` | 403 | `{ "detail": "Too many failed attempts" }` |
| Too many OTP requests | `OtpRateLimitException` → `ForbiddenException` | 403 | `{ "detail": "OTP rate limit exceeded" }` |
| User not found (resend) | `NotFoundException` | 404 | `{ "detail": "No account with this email" }` |
| Already verified (resend) | `ValidationException` | 422 | `{ "detail": "Email already verified" }` |
| No pending verification | `ValidationException` | 422 | `{ "detail": "No pending verification" }` |

---

## 10. Security Considerations

| Concern | Implementation |
|---|---|
| **Password storage** | bcrypt hash with salt (passlib); never store plaintext |
| **OTP storage** | bcrypt hash; never store plaintext OTP in DB |
| **Refresh token storage** | SHA-256 hash; never store plaintext in DB |
| **OTP brute-force** | Max 5 attempts per token + rate limit 5 tokens/hour |
| **Timing attacks** | Use constant-time comparison for OTP verification (bcrypt handles this) |
| **Email enumeration** | Return same message for "already registered" during resend to avoid leaking info |
| **Transaction safety** | OTP verify + user update + profile create in single DB transaction |
| **Token cleanup** | Schedule periodic deletion of expired/used tokens (pg_cron or Edge Function) |

---

## 11. Environment Variables Needed

```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/climasync_db
SECRET_KEY=your-jwt-secret-256-bit
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
OTP_EXPIRE_MINUTES=10
OTP_MAX_ATTEMPTS=5
OTP_RATE_LIMIT_PER_HOUR=5
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@climasync.ai
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@climasync.ai
```

---

## 12. Open Decision: `org_name` Storage During Registration

The registration form collects `org_name`, but `ngo_profiles` is only created **after** OTP verification. Where does `org_name` live between Step 1 and Step 2?

### Recommended: Accept `org_name` in verify-otp request

```python
class VerifyOtpRequest(BaseSchema):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$')
    org_name: str = Field(..., min_length=1, max_length=255)  # ← resend from frontend
```

**Why this is best:**
- Stateless — no temporary storage needed
- Simple — frontend already has the value in memory/state
- No schema changes needed to users table
- If user refreshes the OTP page, they re-enter org_name (or frontend localStorage persists it)

### Alternative B: Store in verification token metadata

Add org_name to the token row so it survives page refreshes:

```sql
-- Not in current schema, would need migration:
ALTER TABLE auth_verification_tokens ADD COLUMN metadata JSONB;
```

Then store `{"org_name": "Pakistan Relief Trust"}` in it. Service reads it during verify.

> [!IMPORTANT]
> **Pick one approach and tell the backend developer.** Option A (resend in verify request) is simplest and recommended.

---

## 13. Registration Number Auto-Generation

`ngo_profiles.registration_number` has `NOT NULL UNIQUE`. Options:

```python
def generate_registration_number() -> str:
    """Generate: NGO-2026-XXXXX (year + 5-digit sequence)"""
    year = datetime.now().year
    # Query max existing number for this year
    # Or use a DB sequence
    return f"NGO-{year}-{next_sequence:05d}"
```

Or make it a **temporary placeholder** that the admin replaces with the real government registration number during NGO verification. In that case:

```python
registration_number = f"TEMP-{uuid4().hex[:8].upper()}"
# e.g. "TEMP-A3F8B2C1"
```

> [!IMPORTANT]
> **Decide:** Is `registration_number` entered by the NGO during registration, or auto-generated? If entered by NGO, add it to `RegisterNgoRequest`.

---

## 14. File/Module Structure for Implementation

```
app/modules/
├── auth/
│   ├── models.py          # AuthVerificationToken, AuthRefreshToken
│   ├── schemas.py         # RegisterNgoRequest, VerifyOtpRequest, etc.
│   ├── repository.py      # OtpRepository, RefreshTokenRepository
│   ├── service.py         # register_ngo(), verify_otp(), resend_otp()
│   ├── controller.py      # POST /auth/register, /verify-otp, /resend-otp
│   ├── dependencies.py    # AuthServiceDep wiring
│   ├── exceptions.py      # OtpExpired, OtpInvalid, OtpMaxAttempts, etc.
│   └── email.py           # send_otp_email()
│
├── users/
│   ├── models.py          # User model (existing)
│   ├── repository.py      # UserRepository (existing, add get_by_email)
│   └── ...
│
└── ngo/                   # NEW MODULE
    ├── __init__.py
    ├── models.py          # NgoProfile, NgoResource
    ├── schemas.py         # NgoProfileResponse, etc.
    ├── repository.py      # NgoRepository (create_profile, create_resources)
    ├── service.py         # Future: update_profile, manage_resources
    ├── controller.py      # Future: GET/PATCH /ngo/profile, etc.
    └── dependencies.py    # NgoServiceDep wiring
```

---

## 15. Summary — What the Developer Builds

| # | Task | Files | Effort |
|---|---|---|---|
| 1 | Create `AuthVerificationToken` model | `auth/models.py` | Small |
| 2 | Create `AuthRefreshToken` model | `auth/models.py` | Small |
| 3 | Create `NgoProfile` + `NgoResource` models | `ngo/models.py` | Medium |
| 4 | Add `RegisterNgoRequest` + response schemas | `auth/schemas.py` | Small |
| 5 | Build `OtpRepository` (create, find, increment, mark used) | `auth/repository.py` | Medium |
| 6 | Build `RefreshTokenRepository` (create, find) | `auth/repository.py` | Small |
| 7 | Build `NgoRepository` (create_profile, create_resources) | `ngo/repository.py` | Small |
| 8 | Implement `register_ngo()` in service | `auth/service.py` | Medium |
| 9 | Implement `verify_otp()` in service | `auth/service.py` | Large |
| 10 | Implement `resend_otp()` in service | `auth/service.py` | Small |
| 11 | Wire controller endpoints | `auth/controller.py` | Small |
| 12 | Implement `send_otp_email()` | `auth/email.py` | Medium |
| 13 | Add auth exceptions | `auth/exceptions.py` | Small |
| 14 | Generate Alembic migration | `migrations/versions/` | Small |
