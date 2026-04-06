"""Auth Pydantic schemas for registration, OTP verification, and responses."""

from uuid import UUID

from pydantic import EmailStr, Field

from app.common.base_schemas import BaseSchema


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class RegisterNgoRequest(BaseSchema):
    """POST /auth/register request body."""

    org_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the NGO organisation",
    )
    email: EmailStr = Field(
        ...,
        description="Email address for the NGO account",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Account password (limit to 72 chars for crypto hashing)",
    )


class VerifyOtpRequest(BaseSchema):
    """POST /auth/verify-otp request body."""

    email: EmailStr = Field(
        ...,
        description="Email address used during registration",
    )
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit OTP code from email",
    )
    org_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Organisation name (re-submitted for stateless processing)",
    )


class ResendOtpRequest(BaseSchema):
    """POST /auth/resend-otp request body."""

    email: EmailStr = Field(
        ...,
        description="Email address to resend OTP to",
    )


class LoginRequest(BaseSchema):
    """POST /auth/login request body."""

    email: EmailStr = Field(
        ...,
        description="Registered email address",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Account password",
    )

# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class RegisterResponse(BaseSchema):
    """201 response after successful registration initiation."""

    message: str
    email: str


class UserBasicResponse(BaseSchema):
    """Minimal user info returned in auth responses."""

    user_id: UUID
    email: str
    role: str
    org_name: str
    is_active: bool
    email_verified: bool
    verification_status: str


class VerifyOtpResponse(BaseSchema):
    """200 response after successful OTP verification."""

    message: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserBasicResponse


class LoginResponse(BaseSchema):
    """200 response after successful login."""

    message: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserBasicResponse
