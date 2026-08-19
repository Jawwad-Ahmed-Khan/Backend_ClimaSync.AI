"""Unit tests for the Auth Service.

Tests registration, OTP generation, and verification logic
without a real database interaction by mocking the repositories.
"""

from unittest.mock import AsyncMock, patch
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import app.common.services.notification_service
from app.modules.auth.exceptions import (
    EmailAlreadyRegisteredException,
    OtpRateLimitException,
    OtpInvalidException,
    OtpExpiredException,
)
from app.modules.auth.schemas import (
    RegisterNgoRequest,
    ResendOtpRequest,
    VerifyOtpRequest,
)
from app.modules.auth.service import AuthService
from app.core.config import settings
from app.core.security import hash_otp


@pytest.fixture
def mock_user_repo():
    return AsyncMock()


@pytest.fixture
def mock_token_repo():
    return AsyncMock()


@pytest.fixture
def mock_refresh_repo():
    return AsyncMock()


@pytest.fixture
def mock_ngo_repo():
    return AsyncMock()


@pytest.fixture
def auth_service(mock_user_repo, mock_token_repo, mock_refresh_repo, mock_ngo_repo):
    return AuthService(
        user_repo=mock_user_repo,
        token_repo=mock_token_repo,
        refresh_repo=mock_refresh_repo,
        ngo_repo=mock_ngo_repo,
    )


@pytest.mark.asyncio
async def test_register_ngo_email_already_verified(auth_service, mock_user_repo):
    """Test that registering with an already verified email raises an exception."""
    user_mock = AsyncMock()
    user_mock.email_verified = True
    mock_user_repo.get_by_email.return_value = user_mock

    data = RegisterNgoRequest(
        org_name="Test NGO",
        email="test@example.com",
        password="securepassword123",
    )

    with pytest.raises(EmailAlreadyRegisteredException):
        await auth_service.register_ngo(data)

    mock_user_repo.get_by_email.assert_called_once_with("test@example.com")


@pytest.mark.asyncio
async def test_register_ngo_success_new_user(
    auth_service, mock_user_repo, mock_token_repo
):
    """Test standard registration of a completely new user."""
    mock_user_repo.get_by_email.return_value = None
    
    new_user_mock = AsyncMock()
    new_user_mock.user_id = str(uuid.uuid4())
    mock_user_repo.create_user.return_value = new_user_mock

    data = RegisterNgoRequest(
        org_name="New NGO",
        email="new@example.com",
        password="securepassword123",
    )

    with patch("app.common.services.notification_service.NotificationService.dispatch_otp_verification", new_callable=AsyncMock) as send_otp_mock:
        response = await auth_service.register_ngo(data)

        assert response.email == "new@example.com"
        assert response.message == "Verification OTP sent to your email"
        
        mock_user_repo.create_user.assert_called_once()
        mock_token_repo.revoke_open_tokens.assert_called_once_with(new_user_mock.user_id, purpose="email_verification")
        mock_token_repo.create_token.assert_called_once()
        send_otp_mock.assert_called_once()


@pytest.mark.asyncio
async def test_resend_otp_rate_limit(
    auth_service, mock_user_repo, mock_token_repo
):
    """Test that OTP resend correctly enforces rate limiting."""
    user_mock = AsyncMock()
    user_mock.email_verified = False
    mock_user_repo.get_by_email.return_value = user_mock
    
    # Simulate max rate limit hits
    mock_token_repo.count_recent_tokens.return_value = settings.OTP_RATE_LIMIT_PER_HOUR

    data = ResendOtpRequest(email="test@example.com")

    with pytest.raises(OtpRateLimitException):
        await auth_service.resend_otp(data)
        
    mock_token_repo.count_recent_tokens.assert_called_once_with(user_mock.user_id, purpose="email_verification")


@pytest.mark.asyncio
async def test_verify_otp_expired_token(
    auth_service, mock_token_repo
):
    """Test that an expired OTP token raises an error."""
    token_mock = AsyncMock()
    token_mock.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    mock_token_repo.find_open_token_by_email.return_value = token_mock
    
    data = VerifyOtpRequest(email="test@example.com", otp="123456", org_name="Testing")
    
    with pytest.raises(OtpExpiredException):
        await auth_service.verify_otp(data)


@pytest.mark.asyncio
async def test_verify_otp_success(
    auth_service, mock_token_repo, mock_user_repo, mock_ngo_repo, mock_refresh_repo
):
    """Test standard verification successful path."""
    token_mock = AsyncMock()
    token_mock.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    token_mock.attempts_count = 0
    token_mock.max_attempts = 5
    token_mock.token_hash = hash_otp("123456")
    token_mock.verification_token_id = str(uuid.uuid4())
    token_mock.user_id = str(uuid.uuid4())
    token_mock.email = "test@example.com"
    
    mock_token_repo.find_open_token_by_email.return_value = token_mock
    
    profile_mock = AsyncMock()
    profile_mock.verification_status = "pending"
    mock_ngo_repo.create_profile.return_value = profile_mock
    
    data = VerifyOtpRequest(email="test@example.com", otp="123456", org_name="Testing")
    
    response = await auth_service.verify_otp(data)
    
    assert response.message == "Email verified successfully"
    assert response.access_token is not None
    assert response.refresh_token is not None
    assert response.user.email == "test@example.com"
    
    mock_token_repo.mark_used.assert_called_once_with(token_mock.verification_token_id)
    mock_user_repo.mark_email_verified.assert_called_once()
    mock_ngo_repo.create_profile.assert_called_once()
    mock_ngo_repo.create_resources.assert_called_once()
    mock_refresh_repo.create_token.assert_called_once()
