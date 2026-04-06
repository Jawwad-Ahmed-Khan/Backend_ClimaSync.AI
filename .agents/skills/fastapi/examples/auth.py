"""
Example: Authentication & Authorization
=========================================
Reference implementation of JWT authentication, password hashing,
OAuth2 scheme, and role-based access control.

Location: app/core/security.py (hashing, JWT)
         app/modules/auth/router.py (login/refresh endpoints)
         app/core/dependencies.py (auth dependencies)
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


# ═══════════════════════════════════════════════════════════════════════════════
# PASSWORD HASHING (app/core/security.py)
# ═══════════════════════════════════════════════════════════════════════════════


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    # For argon2: schemes=["argon2"], and install argon2-cffi
)


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Returns the hashed password string for storage.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored hash.

    Returns True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ═══════════════════════════════════════════════════════════════════════════════
# JWT TOKEN MANAGEMENT (app/core/security.py)
# ═══════════════════════════════════════════════════════════════════════════════


def create_access_token(
    subject: str | UUID,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived access token.

    Args:
        subject: The token subject (usually user ID as string).
        extra_claims: Additional claims to include (role, permissions, etc.).
        expires_delta: Custom expiry duration (defaults to settings).

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    subject: str | UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a long-lived refresh token.

    Refresh tokens are used to obtain new access tokens
    without re-entering credentials. Store securely!
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is malformed or invalid.

    Returns:
        The decoded token payload.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY.get_secret_value(),
        algorithms=[settings.JWT_ALGORITHM],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""

    access_token: str = Field(description="Short-lived JWT access token")
    refresh_token: str = Field(description="Long-lived JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")


class RefreshRequest(BaseModel):
    """Request body for token refresh."""

    refresh_token: str = Field(description="Valid refresh token")


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH ROUTER (app/modules/auth/router.py)
# ═══════════════════════════════════════════════════════════════════════════════


router = APIRouter()

# OAuth2 scheme — tells FastAPI to expect Bearer tokens
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"
)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and receive JWT tokens",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends()],  # Replace with your get_db
) -> TokenResponse:
    """Authenticate user with email/password and return JWT tokens.

    Uses OAuth2 password flow (form data: username + password).

    Returns:
        TokenResponse with access_token and refresh_token.

    Raises:
        HTTPException(401): If credentials are invalid.
    """
    # 1. Find user by email (username field in OAuth2 form)
    # user = await user_repo.get_by_email(form_data.username)
    user = None  # Replace with actual repo call

    # 2. Verify credentials
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # 4. Generate tokens
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
)
async def refresh_token(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends()],  # Replace with your get_db
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token.

    Raises:
        HTTPException(401): If refresh token is invalid or expired.
    """
    try:
        payload = decode_token(body.refresh_token)

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Optionally: verify user still exists and is active
        # user = await user_repo.get_by_id(user_id)

        # Generate new access token
        new_access_token = create_access_token(subject=user_id)
        new_refresh_token = create_refresh_token(subject=user_id)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired — please login again",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
