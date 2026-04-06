# Specification: NGO Registration

## 1. Feature Overview
The system enables NGO organizations to register an account, confirm their email via OTP, and receive a JWT token upon successful verification. It provides the foundation for NGO onboarding with robust security, rate limiting, and database validation.

## 2. User Scenarios & Testing

- **Scenario 1: Successful NGO Registration**
  An NGO user provides their organization name, email, and password. The system sends a 6-digit OTP to their email and returns a success message.
- **Scenario 2: Successful OTP Verification**
  The NGO user submits the OTP received via email along with their email address and organization name. The system verifies the OTP, creates the user and NGO profile records, and returns a JWT access and refresh token pair.
- **Scenario 3: Resend OTP**
  An unverified NGO user requests a new OTP. The system revokes any previous open tokens, generates a new one, sends it via email, and returns a success message.
- **Scenario 4: OTP Rate Limit Exceeded**
  An NGO user attempts to request more than 5 OTPs within an hour. The system rejects the request to prevent abuse.
- **Scenario 5: OTP Maximum Attempts Reached**
  An NGO user enters an incorrect OTP 5 times. The system invalidates the token and requires the user to request a new one.

## 3. Functional Requirements

- **Registration API:** The system must provide a POST endpoint for registration that validates inputs (email, password length) and triggers an OTP email.
- **OTP Generation & Delivery:** The system must generate a secure 6-digit OTP and send it via an email service (e.g., SMTP).
- **OTP Verification API:** The system must provide a POST endpoint that validates the OTP against a hashed version stored in the database.
- **Token Management:** Upon successful OTP verification, the system must generate a JWT access token (15 min expiry) and refresh token (7 days expiry), and store the refresh token hash.
- **Rate Limiting:** The system must restrict OTP requests to 5 per hour per user.
- **Role-Based Access:** The system must assign the `ngo_user` role to registering NGOs.
- **Stateless Organization Name Handling:** The organization name must be accepted during the OTP verification request to avoid temporary caching.
- **Database Modularity:** The system must rely on standard PostgreSQL features, remaining agnostic to the hosting provider (compatible with Supabase and AWS RDS).

## 4. Success Criteria

- Registration requests successfully send OTP emails within 10 seconds.
- Valid OTP verification results in the generation of both JWT tokens in less than 500ms.
- OTP rate-limiting successfully blocks the 6th request from the same user within a 1-hour window.
- Successful verification accurately populates 4 core database tables (`users`, `auth_verification_tokens`, `ngo_profiles`, `ngo_resources`) in a single transaction.

## 5. Key Entities

- **User (`users`):** Core authentication record including email, password hash, and verification status.
- **Auth Verification Token (`auth_verification_tokens`):** Tracks OTP hashes, expiration, attempts, and usage status.
- **NGO Profile (`ngo_profiles`):** Contains the organization name, auto-generated temporary registration number, and pending verification status.
- **NGO Resource (`ngo_resources`):** Holds default capacity metrics (e.g., ambulances, volunteers) initialized to zero.
- **Auth Refresh Token (`auth_refresh_tokens`):** Stores hashed refresh tokens for session management.

## 6. Assumptions and Defaults

- The `org_name` field will be re-submitted by the frontend during the OTP verification step to ensure a stateless backend process.
- Registration numbers for new NGOs will be auto-generated with a "TEMP-" prefix. Admin verification will assign permanent numbers.
- Default service radius for new NGOs is 10 km.
- Database migrations and ORM models will use SQLAlchemy.
