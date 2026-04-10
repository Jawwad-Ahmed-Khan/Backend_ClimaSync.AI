# ClimaSync.AI — API Requirements for Frontend Integration

## Overview

This document lists ALL backend APIs required by the frontend, organized by feature/page.
Each entry specifies the endpoint, method, request payload, expected response, and the
frontend component that consumes it.

---

## Authentication APIs (Currently Implemented)

### 1. POST `/api/v1/auth/register`

| Field | Value |
|:------|:------|
| **Used by** | `app/(auth)/register/page.tsx` → `authService.registerAPI()` |
| **Purpose** | Register a new NGO user and trigger OTP email |
| **Rate Limit** | 10/minute |
| **Request Body** | `{ org_name: string, email: string, password: string }` |
| **Success (201)** | `{ message: string, email: string }` |
| **Error (409)** | `{ detail: "Email already registered" }` |
| **Error (422)** | Pydantic validation errors |
| **Error (429)** | Rate limit exceeded |

### 2. POST `/api/v1/auth/verify-otp`

| Field | Value |
|:------|:------|
| **Used by** | `app/(auth)/verify/page.tsx` → `authService.verifyOtpAPI()` |
| **Purpose** | Verify 6-digit OTP and complete registration |
| **Request Body** | `{ email: string, otp: string, org_name: string }` |
| **Success (200)** | `{ message, access_token, refresh_token, token_type, user }` |
| **Error (401)** | `{ detail: "Invalid OTP code" }` |
| **Error (403)** | `{ detail: "Too many failed attempts..." }` |
| **Error (422)** | `{ detail: "OTP has expired..." }` or `{ detail: "No pending verification..." }` |

### 3. POST `/api/v1/auth/resend-otp`

| Field | Value |
|:------|:------|
| **Used by** | `app/(auth)/verify/page.tsx` → `authService.resendOtpAPI()` |
| **Purpose** | Resend OTP to unverified user |
| **Rate Limit** | 5/minute |
| **Request Body** | `{ email: string }` |
| **Success (200)** | `{ message: string }` |
| **Error (404)** | Account not found |
| **Error (422)** | Email already verified |
| **Error (429)** | Rate limit exceeded |

### 4. POST `/api/v1/auth/login`

| Field | Value |
|:------|:------|
| **Used by** | `app/(auth)/login/page.tsx` → `authService.loginAPI()` |
| **Purpose** | Authenticate verified user and return JWT tokens |
| **Rate Limit** | 10/minute |
| **Request Body** | `{ email: string, password: string }` |
| **Success (200)** | `{ message, access_token, refresh_token, token_type, user }` |
| **Error (401)** | `{ detail: "Invalid email or password" }` |
| **Error (403)** | `{ detail: "Account is disabled..." }` or `{ detail: "Email not verified..." }` |
| **Error (429)** | Rate limit exceeded |

---

## Authentication APIs (Not Yet Implemented — Required for Full Flow)

### 5. POST `/api/v1/auth/refresh` *(NEEDED)*

| Field | Value |
|:------|:------|
| **Used by** | `authService.ts` → interceptor (auto-refresh) |
| **Purpose** | Refresh expired access token using refresh token |
| **Request Body** | `{ refresh_token: string }` |
| **Success (200)** | `{ access_token, refresh_token, token_type }` |
| **Error (401)** | Invalid/expired refresh token |

### 6. POST `/api/v1/auth/logout` *(NEEDED)*

| Field | Value |
|:------|:------|
| **Used by** | `authContext.tsx` → `logout()` |
| **Purpose** | Revoke refresh token server-side |
| **Auth** | Bearer token required |
| **Success (200)** | `{ message: "Logged out" }` |

### 7. GET `/api/v1/auth/me` *(NEEDED)*

| Field | Value |
|:------|:------|
| **Used by** | `authContext.tsx` → hydration on page load |
| **Purpose** | Get current authenticated user profile |
| **Auth** | Bearer token required |
| **Success (200)** | Full user object |
| **Error (401)** | Token invalid/expired |

---

## Social Login APIs (Future — Currently UI Placeholders)

### 8. GET `/api/v1/auth/social/{provider}` *(FUTURE)*

| Field | Value |
|:------|:------|
| **Providers** | google, facebook, x, github, yahoo |
| **Purpose** | Initiate OAuth redirect to provider |
| **Response** | 302 redirect to provider consent screen |

### 9. GET `/api/v1/auth/social/{provider}/callback` *(FUTURE)*

| Field | Value |
|:------|:------|
| **Purpose** | Handle OAuth callback, find/create user, return JWTs |
| **Response** | Redirect to frontend with tokens in query params |

---

## Password Reset APIs (Future — Currently UI Placeholders)

### 10. POST `/api/v1/auth/forgot-password` *(FUTURE)*

| Field | Value |
|:------|:------|
| **Purpose** | Send password reset email |
| **Request Body** | `{ email: string }` |

### 11. POST `/api/v1/auth/reset-password` *(FUTURE)*

| Field | Value |
|:------|:------|
| **Purpose** | Reset password with token |
| **Request Body** | `{ token: string, new_password: string }` |

---

## User Object Structure (Returned by Login/Verify-OTP)

```json
{
  "user_id": "uuid",
  "email": "user@ngo.org",
  "role": "ngo_user | admin | super_admin",
  "org_name": "Pakistan Relief Foundation",
  "is_active": true,
  "email_verified": true,
  "verification_status": "pending | verified | rejected | suspended"
}
```

---

## CORS Requirements

The backend MUST allow the following origins:
- `http://localhost:3000` (Next.js dev server)
- Production frontend URL (when deployed)

Required headers: `Authorization`, `Content-Type`
Required methods: `GET`, `POST`, `OPTIONS`

---

## Summary by Priority

| Priority | Endpoint | Status |
|:---------|:---------|:-------|
| ✅ P0 | POST /auth/register | Implemented |
| ✅ P0 | POST /auth/verify-otp | Implemented |
| ✅ P0 | POST /auth/resend-otp | Implemented |
| ✅ P0 | POST /auth/login | Implemented |
| ⚠️ P1 | POST /auth/refresh | Needed |
| ⚠️ P1 | POST /auth/logout | Needed |
| ⚠️ P1 | GET /auth/me | Needed |
| 🔮 P2 | Social OAuth flow | Future |
| 🔮 P2 | Password reset flow | Future |
