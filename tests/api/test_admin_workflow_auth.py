"""Integration tests for admin workflow authentication endpoints.

Tests:
- POST /api/admin/auth/create (create admin account)
- POST /api/admin/auth/login (authenticate admin)

Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


# ============================================================================
# Test Data
# ============================================================================

def generate_unique_email():
    """Generate a unique email for testing."""
    return f"admin_{uuid.uuid4().hex[:8]}@example.com"


VALID_ADMIN_DATA = {
    "email": generate_unique_email(),
    "password": "SecurePassword123",
    "org_name": "Test Organization",
    "full_name": "Test Admin",
}


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def app():
    """Create FastAPI app instance."""
    return create_app()


# ============================================================================
# Task 6.2: Integration Tests for Authentication Endpoints
# ============================================================================


@pytest.mark.asyncio
async def test_create_admin_account_success(app):
    """Test successful admin account creation.
    
    Requirements: 1.1, 1.3, 17.6
    """
    test_data = {
        "email": generate_unique_email(),
        "password": "SecurePassword123",
        "org_name": "Test Organization",
        "full_name": "Test Admin",
    }
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/admin/auth/create", json=test_data)
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify response structure
    assert "user_id" in data
    assert "email" in data
    assert "org_name" in data
    assert "role" in data
    assert "access_token" in data
    assert "refresh_token" in data
    
    # Verify response values
    assert data["email"] == test_data["email"]
    assert data["org_name"] == test_data["org_name"]
    assert data["role"] == "admin"
    
    # Verify tokens are non-empty strings
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0
    assert isinstance(data["refresh_token"], str)
    assert len(data["refresh_token"]) > 0


@pytest.mark.asyncio
async def test_create_admin_account_duplicate_email(app):
    """Test admin account creation with duplicate email.
    
    Requirements: 1.4
    """
    test_data = {
        "email": generate_unique_email(),
        "password": "SecurePassword123",
        "org_name": "Test Organization",
        "full_name": "Test Admin",
    }
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Create first account
        response1 = await ac.post("/api/v1/admin/auth/create", json=test_data)
        assert response1.status_code == 201
        
        # Attempt to create second account with same email
        duplicate_data = {
            **test_data,
            "password": "DifferentPassword456",
            "org_name": "Different Organization",
        }
        response2 = await ac.post("/api/v1/admin/auth/create", json=duplicate_data)
    
    assert response2.status_code == 400
    data = response2.json()
    assert "detail" in data
    assert "already exists" in data["detail"].lower()


@pytest.mark.asyncio
async def test_create_admin_account_invalid_email(app):
    """Test admin account creation with invalid email format."""
    invalid_data = {
        "email": "not-an-email",
        "password": "SecurePassword123",
        "org_name": "Test Organization",
        "full_name": "Test Admin",
    }
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/admin/auth/create", json=invalid_data)
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_admin_account_short_password(app):
    """Test admin account creation with password too short.
    
    Requirements: 1.5
    """
    invalid_data = {
        "email": generate_unique_email(),
        "password": "short",  # Less than 8 characters
        "org_name": "Test Organization",
        "full_name": "Test Admin",
    }
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/admin/auth/create", json=invalid_data)
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_admin_success(app):
    """Test successful admin login.
    
    Requirements: 2.1, 2.3, 2.6, 2.7, 17.8
    """
    test_data = {
        "email": generate_unique_email(),
        "password": "SecurePassword123",
        "org_name": "Test Organization",
        "full_name": "Test Admin",
    }
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Create admin account first
        create_response = await ac.post("/api/v1/admin/auth/create", json=test_data)
        assert create_response.status_code == 201
        
        # Login with correct credentials
        login_data = {
            "email": test_data["email"],
            "password": test_data["password"],
        }
        response = await ac.post("/api/v1/admin/auth/login", json=login_data)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "user_id" in data
    assert "email" in data
    assert "org_name" in data
    assert "role" in data
    assert "access_token" in data
    assert "refresh_token" in data
    
    # Verify response values
    assert data["email"] == test_data["email"]
    assert data["org_name"] == test_data["org_name"]
    assert data["role"] == "admin"
    
    # Verify tokens are non-empty strings
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0
    assert isinstance(data["refresh_token"], str)
    assert len(data["refresh_token"]) > 0


@pytest.mark.asyncio
async def test_login_admin_invalid_password(app):
    """Test admin login with incorrect password.
    
    Requirements: 2.4
    """
    test_data = {
        "email": generate_unique_email(),
        "password": "SecurePassword123",
        "org_name": "Test Organization",
        "full_name": "Test Admin",
    }
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Create admin account first
        create_response = await ac.post("/api/v1/admin/auth/create", json=test_data)
        assert create_response.status_code == 201
        
        # Login with incorrect password
        login_data = {
            "email": test_data["email"],
            "password": "WrongPassword123",
        }
        response = await ac.post("/api/v1/admin/auth/login", json=login_data)
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_login_admin_nonexistent_email(app):
    """Test admin login with non-existent email.
    
    Requirements: 2.4
    """
    login_data = {
        "email": "nonexistent@example.com",
        "password": "SomePassword123",
    }
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/admin/auth/login", json=login_data)
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_jwt_tokens_are_valid(app):
    """Test that JWT tokens can be decoded and contain correct payload.
    
    Requirements: 2.6
    """
    test_data = {
        "email": generate_unique_email(),
        "password": "SecurePassword123",
        "org_name": "Test Organization",
        "full_name": "Test Admin",
    }
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Create admin account
        create_response = await ac.post("/api/v1/admin/auth/create", json=test_data)
        assert create_response.status_code == 201
        data = create_response.json()
    
    # Decode access token
    from app.core.security import decode_token
    access_payload = decode_token(data["access_token"])
    
    # Verify token payload
    assert "sub" in access_payload  # subject (user_id)
    assert "role" in access_payload
    assert "exp" in access_payload  # expiration
    assert "iat" in access_payload  # issued at
    assert "type" in access_payload
    assert access_payload["type"] == "access"
    assert access_payload["role"] == "admin"
    
    # Decode refresh token
    refresh_payload = decode_token(data["refresh_token"])
    
    # Verify refresh token payload
    assert "sub" in refresh_payload
    assert "exp" in refresh_payload
    assert "iat" in refresh_payload
    assert "type" in refresh_payload
    assert refresh_payload["type"] == "refresh"
    
    # Verify both tokens have same subject (user_id)
    assert access_payload["sub"] == refresh_payload["sub"]


