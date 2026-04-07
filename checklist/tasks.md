# Login Feature — Tasks

## T1: Schema Layer
- [x] Add `LoginRequest` with email (EmailStr) + password (8-72 chars)
- [x] Add `LoginResponse` with message, tokens, token_type, user
- [x] Verify both schemas inherit from `BaseSchema`

## T2: Exception Layer
- [x] Add `InvalidCredentialsException` extending `UnauthorizedException` (401)
- [x] Add `AccountDisabledException` extending `ForbiddenException` (403)
- [x] Add `EmailNotVerifiedException` extending `ForbiddenException` (403)
- [x] Verify all exceptions use generic messages (no user enumeration)

## T3: Repository Layer
- [x] Add `UserRepository.update_last_login(user_id, logged_in_at)`
- [x] Add `NgoRepository.get_profile_by_ngo_id(ngo_id)`
- [x] Verify both use `flush()` after modification

## T4: Service Layer
- [x] Add `AuthService.login()` public method
- [x] Add `AuthService._check_password()` private helper
- [x] Add `AuthService._validate_account_active()` private helper
- [x] Add `AuthService._validate_email_verified()` private helper
- [x] Make `_generate_tokens()` accept `role` as keyword argument
- [x] Update `_complete_verification()` to pass role to `_generate_tokens()`
- [x] Add timing-safe dummy hash when user is None

## T5: Controller Layer
- [x] Add `POST /auth/login` endpoint
- [x] Add rate limiting decorator (10/minute)
- [x] Extract IP address and user-agent from Request
- [x] Import `LoginRequest` and `LoginResponse`

## T6: Documentation
- [x] Create `checklist/requirements.md`
- [x] Create `checklist/constitution.md`
- [x] Create `checklist/spec.md`
- [x] Create `checklist/plan.md`
- [x] Create `checklist/tasks.md`
- [x] Create `checklist/subtasks.md`
- [x] Create `checklist/research.md`
- [x] Create `checklist/quickstart.md`

## T7: Git & Verification
- [x] Syntax checks pass for all modified files
- [ ] Commit to `feature/login` branch
- [ ] Merge to `Develop`
- [ ] Push to origin
