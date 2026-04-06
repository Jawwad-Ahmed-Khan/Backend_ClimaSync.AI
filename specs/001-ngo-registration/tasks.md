# Tasks: NGO Registration

## Implementation Strategy
We will follow a modular, layer-first approach for each user story. All endpoints will be implemented asynchronously with strict 5-layer separation. MVP focuses on the core registration and verification flow.

## Phase 1: Setup
- [ ] T001 Install dependencies: `uv add slowapi aiosmtplib passlib[bcrypt] python-jose[cryptography]`
- [ ] T002 Configure SMTP and JWT settings in `app/core/config.py`
- [ ] T003 Initialize `Auth` and `Ngo` module directories and `__init__.py` files

## Phase 2: Foundational
- [ ] T004 Implement `AuthVerificationToken` and `AuthRefreshToken` models in `app/modules/auth/models.py`
- [ ] T005 Implement `NgoProfile` and `NgoResource` models in `app/modules/ngo/models.py`
- [ ] T006 [P] Create and run Alembic migrations for new models in `migrations/versions/`

## Phase 3: [US1] NGO Registration
**Goal**: Allow NGO users to initiate registration and receive an OTP.
- [ ] T007 [US1] Create registration schemas in `app/modules/auth/schemas.py`
- [ ] T008 [US1] Implement `AuthRepository` for token persistence in `app/modules/auth/repository.py`
- [ ] T009 [US1] Implement async email delivery utility in `app/modules/auth/email.py`
- [ ] T010 [US1] Implement `register_ngo` logic in `app/modules/auth/service.py`
- [ ] T011 [US1] Implement `POST /auth/register` endpoint in `app/modules/auth/controller.py`
- [ ] T012 [US1] Verify registration flow: Sends OTP email and creates unverified user.

## Phase 4: [US2] OTP Verification
**Goal**: Verify the registration OTP and create the NGO profile.
- [ ] T013 [US2] Create OTP verification schemas in `app/modules/auth/schemas.py`
- [ ] T014 [US2] Implement `NgoRepository` for profile/resource persistence in `app/modules/ngo/repository.py`
- [ ] T015 [US2] Implement `verify_otp` logic with transactional profile creation in `app/modules/auth/service.py`
- [ ] T016 [US2] Implement `POST /auth/verify-otp` endpoint in `app/modules/auth/controller.py`
- [ ] T017 [US2] Verify verification flow: Marks user verified and generates JWT tokens.

## Phase 5: [US3] Resend OTP & Rate Limiting
**Goal**: Allow users to request a new OTP with rate limiting protection.
- [ ] T018 [US3] Implement `resend_otp` logic in `app/modules/auth/service.py`
- [ ] T019 [US3] Configure `slowapi` rate limiter for auth endpoints in `app/modules/auth/controller.py`
- [ ] T020 [US3] Implement `POST /auth/resend-otp` endpoint in `app/modules/auth/controller.py`
- [ ] T021 [US3] Verify rate limiting: 6th request within 1 hour is blocked with 429.

## Phase 6: Polish & Cross-Cutting
- [ ] T022 Implement global exception handlers for `Auth` domain in `app/core/exception_handlers.py`
- [ ] T023 Final code review and ruff formatting across `app/modules/auth/` and `app/modules/ngo/`

## Dependencies
- US1 (Registration) must be completed before US2 (Verification)
- Foundational models must be migrated before US1 implementation

## Parallel Execution
- T004 and T005 can be done in parallel.
- T007 (Schemas) and T009 (Email util) can be done in parallel within US1.
