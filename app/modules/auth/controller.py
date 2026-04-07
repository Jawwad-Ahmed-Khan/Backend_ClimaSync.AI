"""Auth controller — HTTP endpoints for registration, login, and OTP flows.

Handles ONLY HTTP concerns: request parsing, dependency injection,
response shaping, and status codes. Business logic lives in AuthService.
"""

from fastapi import APIRouter, Request

from app.common.base_schemas import MessageResponse
from app.core.limiter import limiter
from app.modules.auth.dependencies import AuthServiceDep
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterNgoRequest,
    RegisterResponse,
    ResendOtpRequest,
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
