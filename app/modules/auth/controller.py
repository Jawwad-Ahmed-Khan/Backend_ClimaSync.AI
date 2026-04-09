"""Auth controller — HTTP endpoints for registration, login, OTP flows,
password management, token refresh, logout, and profile operations.

Handles ONLY HTTP concerns: request parsing, dependency injection,
response shaping, and status codes. Business logic lives in AuthService.
"""

from fastapi import APIRouter, Request

from app.common.base_schemas import MessageResponse
from app.core.limiter import limiter
from app.modules.auth.dependencies import AuthServiceDep, CurrentUserDep
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterNgoRequest,
    RegisterResponse,
    ResendOtpRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UserProfileResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

_STATUS_CREATED = 201


@router.post(
    "/register",
    status_code=_STATUS_CREATED,
    response_model=RegisterResponse,
    summary="Register a new NGO",
    description="Initiates NGO registration and sends a 6-digit OTP to the provided email.",
)
@limiter.limit("10/minute")
async def register(
    request: Request,
    data: RegisterNgoRequest,
    service: AuthServiceDep,
) -> RegisterResponse:
    """Register a new NGO. Sends OTP to email."""
    return await service.register_ngo(data)


@router.post(
    "/verify-otp",
    response_model=VerifyOtpResponse,
    summary="Verify OTP and complete registration",
    description="Verifies the OTP, creates NGO profile and resources, and returns JWT tokens.",
)
async def verify_otp(
    data: VerifyOtpRequest,
    request: Request,
    service: AuthServiceDep,
) -> VerifyOtpResponse:
    """Verify OTP and complete NGO registration."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.verify_otp(data, ip_address, user_agent)


@router.post(
    "/resend-otp",
    response_model=MessageResponse,
    summary="Resend verification OTP",
    description="Resends a new OTP to the email. Rate limited to 5 per hour.",
)
@limiter.limit("5/minute")
async def resend_otp(
    request: Request,
    data: ResendOtpRequest,
    service: AuthServiceDep,
) -> MessageResponse:
    """Resend verification OTP. Rate limited to 5/hour."""
    result = await service.resend_otp(data)
    return MessageResponse(message=result["message"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login as a verified NGO user",
    description=(
        "Authenticates an NGO user with email and password. "
        "Returns JWT access + refresh tokens on success. "
        "The account must be active and the email must be verified."
    ),
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    data: LoginRequest,
    service: AuthServiceDep,
) -> LoginResponse:
    """Authenticate NGO user and return JWT tokens."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.login(data, ip_address, user_agent)


# ------------------------------------------------------------------
# Password management (public — no auth required)
# ------------------------------------------------------------------


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset OTP",
    description=(
        "Sends a 6-digit OTP to the registered email address for password reset. "
        "Always returns success to prevent email enumeration."
    ),
)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    service: AuthServiceDep,
) -> MessageResponse:
    """Request a password reset OTP."""
    result = await service.forgot_password(data)
    return MessageResponse(message=result["message"])


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with OTP",
    description=(
        "Verifies the password reset OTP and sets a new password. "
        "All existing sessions are revoked (force re-login)."
    ),
)
async def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    service: AuthServiceDep,
) -> MessageResponse:
    """Verify OTP and reset the password."""
    result = await service.reset_password(data)
    return MessageResponse(message=result["message"])


# ------------------------------------------------------------------
# Token management (public — uses refresh token, not access token)
# ------------------------------------------------------------------


@router.post(
    "/refresh-token",
    response_model=LoginResponse,
    summary="Refresh access token",
    description=(
        "Exchanges a valid refresh token for a new access + refresh token pair. "
        "The old refresh token is revoked (single-use rotation)."
    ),
)
async def refresh_token(
    data: RefreshTokenRequest,
    request: Request,
    service: AuthServiceDep,
) -> LoginResponse:
    """Exchange refresh token for new token pair."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.refresh_token(data, ip_address, user_agent)


# ------------------------------------------------------------------
# Protected endpoints (require JWT access token)
# ------------------------------------------------------------------


@router.post(
    "/change-password",
    response_model=LoginResponse,
    summary="Change password (authenticated)",
    description=(
        "Changes the password for the authenticated user. Requires the current password. "
        "All existing sessions are revoked and fresh tokens are returned."
    ),
)
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> LoginResponse:
    """Change password for the authenticated user."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.change_password(
        current_user.user_id, data, ip_address, user_agent,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout current session",
    description="Revokes the provided refresh token, ending the current session.",
)
async def logout(
    data: LogoutRequest,
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> MessageResponse:
    """Logout by revoking the refresh token."""
    result = await service.logout(data)
    return MessageResponse(message=result["message"])


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Logout from all sessions",
    description="Revokes all refresh tokens for the authenticated user.",
)
async def logout_all(
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> MessageResponse:
    """Logout from all sessions."""
    result = await service.logout_all(current_user.user_id)
    return MessageResponse(message=result["message"])


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Returns the full profile of the authenticated user including NGO details.",
)
async def get_me(
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> UserProfileResponse:
    """Get the current user's profile."""
    return await service.get_me(current_user.user_id)


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="Update profile info",
    description=(
        "Updates the NGO profile for the authenticated user. "
        "Only provided fields are updated; omitted fields remain unchanged."
    ),
)
async def update_profile(
    data: UpdateProfileRequest,
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> UserProfileResponse:
    """Update the current user's profile."""
    return await service.update_profile(current_user.user_id, data)

