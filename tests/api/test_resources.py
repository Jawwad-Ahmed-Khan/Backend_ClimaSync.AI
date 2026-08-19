"""API Tests for Resource and Capabilities boundaries."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.modules.auth.dependencies import get_current_user
from app.modules.users.models import User

# Mocks
async def override_get_current_user_admin() -> User:
    return User(
        user_id=uuid.uuid4(),
        email="testadmin@example.com",
        role="admin",
        is_active=True,
    )

async def override_get_current_user_ngo() -> User:
    return User(
        user_id=uuid.uuid4(),
        email="testngo@example.com",
        role="ngo_user",
        is_active=True,
    )

@pytest.fixture
def app_admin():
    app = create_app()
    app.dependency_overrides[get_current_user] = override_get_current_user_admin
    return app

@pytest.fixture
def app_ngo():
    app = create_app()
    app.dependency_overrides[get_current_user] = override_get_current_user_ngo
    return app

@pytest.mark.asyncio
async def test_resources_me_unavailable_for_admin(app_admin) -> None:
    """Admin does not have localized capabilities, only NGOS do."""
    async with AsyncClient(
        transport=ASGITransport(app=app_admin), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/resources/me")
    
    assert response.status_code == 403
    assert "ngo" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_resources_search_works_for_admin(app_admin) -> None:
    """Admins can call search engine mapping operations zone."""
    payload = {"province": "Sindh", "min_ambulances": 2, "limit": 10}
    async with AsyncClient(
        transport=ASGITransport(app=app_admin), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/resources/search", json=payload)
    
    # 200 OK because it resolves gracefully even if database returns zero responders
    assert response.status_code == 200 
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_resources_search_blocked_for_ngos(app_ngo) -> None:
    """NGOs cannot dispatch and scan the system capabilities list."""
    payload = {"province": "Sindh", "limit": 10}
    async with AsyncClient(
        transport=ASGITransport(app=app_ngo), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/resources/search", json=payload)
    
    assert response.status_code == 403
