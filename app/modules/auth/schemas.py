"""Auth Pydantic schemas for registration, login, OTP verification, password management, and profile."""

from datetime import datetime
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


class ForgotPasswordRequest(BaseSchema):
    """POST /auth/forgot-password request body."""

    email: EmailStr = Field(
        ...,
        description="Email address of the account to reset",
    )


class ResetPasswordRequest(BaseSchema):
    """POST /auth/reset-password request body."""

    email: EmailStr = Field(
        ...,
        description="Email address of the account",
    )
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit OTP code from password reset email",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="New password (8–72 characters)",
    )


class ChangePasswordRequest(BaseSchema):
    """POST /auth/change-password request body."""

    current_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Current account password",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="New password (8–72 characters)",
    )


class RefreshTokenRequest(BaseSchema):
    """POST /auth/refresh-token request body."""

    refresh_token: str = Field(
        ...,
        description="Refresh token obtained from login or previous refresh",
    )


class LogoutRequest(BaseSchema):
    """POST /auth/logout request body."""

    refresh_token: str = Field(
        ...,
        description="Refresh token to revoke",
    )


class UpdateProfileRequest(BaseSchema):
    """PATCH /auth/me request body. All fields optional — only provided fields are updated."""

    org_name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Organisation name",
    )
    head_of_operations: str | None = Field(
        None,
        max_length=255,
        description="Name of the head of operations",
    )
    phone: str | None = Field(
        None,
        max_length=20,
        description="Contact phone number",
    )
    website: str | None = Field(
        None,
        description="Organisation website URL",
    )
    base_city: str | None = Field(
        None,
        max_length=100,
        description="Base city of operations",
    )
    base_district: str | None = Field(
        None,
        max_length=100,
        description="Base district of operations",
    )
    base_province: str | None = Field(
        None,
        max_length=100,
        description="Base province of operations",
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


class UserProfileResponse(BaseSchema):
    """Full user profile returned by GET /auth/me."""

    user_id: UUID
    email: str
    role: str
    is_active: bool
    email_verified: bool
    org_name: str
    head_of_operations: str | None
    phone: str | None
    website: str | None
    base_city: str | None
    base_district: str | None
    base_province: str | None
    verification_status: str
    last_login_at: datetime | None

