# Login Feature — Execution Plan

## Phase 1: Setup ✅
1. Clone repo and checkout Develop branch
2. Create `feature/login` branch from Develop
3. Audit existing `feature/login-api` branch for reference

## Phase 2: Implementation ✅

### Step 2.1: Schemas
- Add `LoginRequest` (email, password) to `auth/schemas.py`
- Add `LoginResponse` (message, tokens, user) to `auth/schemas.py`

### Step 2.2: Exceptions
- Add `InvalidCredentialsException` (401) to `auth/exceptions.py`
- Add `AccountDisabledException` (403) to `auth/exceptions.py`
- Add `EmailNotVerifiedException` (403) to `auth/exceptions.py`

### Step 2.3: Repository Layer
- Add `update_last_login()` to `users/repository.py`
- Add `get_profile_by_ngo_id()` to `ngo/repository.py`

### Step 2.4: Service Layer
- Add `login()` method to `AuthService`
- Add `_check_password()` helper
- Add `_validate_account_active()` helper
- Add `_validate_email_verified()` helper
- Make `_generate_tokens()` accept dynamic `role` parameter

### Step 2.5: Controller Layer
- Add `POST /auth/login` endpoint with rate limiting (10/min)
- Extract IP address and user-agent from request

## Phase 3: Documentation ✅
- Create all files under `checklist/`:
  - `requirements.md`, `constitution.md`, `spec.md`, `plan.md`
  - `tasks.md`, `subtasks.md`, `research.md`, `quickstart.md`

## Phase 4: Verification
- Syntax validation (AST parsing)
- Git commit to `feature/login`
- Merge `feature/login` → `Develop`
- Push to origin

## Phase 5: Cleanup
- Remove temp reference files
- Update task tracker
