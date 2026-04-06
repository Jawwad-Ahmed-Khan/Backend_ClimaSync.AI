# Quickstart: NGO Registration

## Environment Setup
Ensure you have `uv` installed.
```bash
uv sync
uv add slowapi aiosmtplib passlib[bcrypt] python-jose[cryptography]
```

## Configuration
Add the following to your `.env` file:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-app-password
JWT_SECRET_KEY=your-256-bit-secret
OTP_EXPIRE_MINUTES=10
```

## Running the Application
```bash
uv run uvicorn app.main:app --reload
```

## Testing the Flow

### 1. Register NGO
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"org_name": "Pakistan Relief", "email": "test@example.com", "password": "securepassword123"}'
```

### 2. Verify OTP
Check your email for the 6-digit OTP.
```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "otp": "123456", "org_name": "Pakistan Relief"}'
```
Note: `org_name` is required again for stateless processing.
