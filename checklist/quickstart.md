# ClimaSync.AI Backend — Quick Start Guide

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- PostgreSQL (Supabase or local)
- Git

## Setup

### 1. Clone & Branch

```bash
git clone https://github.com/Jawwad-Ahmed-Khan/Backend_ClimaSync.AI.git
cd Backend_ClimaSync.AI
git checkout Develop
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Configure Environment

Create `.env` in project root:

```env
DATABASE_URL=postgresql://user:pass@host:5432/climasync_db
SECRET_KEY=your-secure-256-bit-jwt-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
OTP_EXPIRE_MINUTES=10
OTP_MAX_ATTEMPTS=5
OTP_RATE_LIMIT_PER_HOUR=5
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@climasync.ai
SMTP_FROM_NAME=ClimaSync.AI
ENVIRONMENT=development
```

### 4. Database Setup

Run the SQL schema in your PostgreSQL instance:

```bash
psql -U your_user -d climasync_db -f database.sql
```

### 5. Run the Server

```bash
uv run uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

## API Endpoints

### Auth Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/register` | Register new NGO |
| `POST` | `/api/v1/auth/verify-otp` | Verify OTP & complete registration |
| `POST` | `/api/v1/auth/resend-otp` | Resend verification OTP |
| `POST` | `/api/v1/auth/login` | Login with email & password |
| `GET` | `/health` | Health check |

### Testing Login

#### Step 1: Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"org_name": "Test NGO", "email": "test@example.com", "password": "securepass123"}'
```

#### Step 2: Verify OTP (check your email)
```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "otp": "123456", "org_name": "Test NGO"}'
```

#### Step 3: Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "securepass123"}'
```

#### Expected 200 Response:
```json
{
    "message": "Login successful",
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "user": {
        "user_id": "...",
        "email": "test@example.com",
        "role": "ngo_user",
        "org_name": "Test NGO",
        "is_active": true,
        "email_verified": true,
        "verification_status": "pending"
    }
}
```

## Interactive Docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
app/
├── __init__.py
├── main.py                  # App factory
├── common/                  # Shared base classes
│   ├── base_model.py
│   ├── base_schemas.py
│   └── base_repository.py
├── core/                    # Framework config
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── exceptions.py
│   ├── exception_handlers.py
│   ├── limiter.py
│   ├── middleware.py
│   └── security.py
└── modules/
    ├── auth/                # Registration + Login
    │   ├── controller.py
    │   ├── service.py
    │   ├── repository.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── exceptions.py
    │   ├── dependencies.py
    │   └── email.py
    ├── users/               # User model + repository
    │   ├── models.py
    │   └── repository.py
    └── ngo/                 # NGO profiles + resources
        ├── models.py
        └── repository.py
```
