"""API Tests for Social & News Module."""

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
async def test_social_list_posts(app_admin) -> None:
    """Reading feed is accessible."""
    async with AsyncClient(
        transport=ASGITransport(app=app_admin), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/social")
    
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_social_create_post_forbidden_for_ngo(app_ngo) -> None:
    """Non-admin should get 403 Forbidden for admin endpoints."""
    payload = {
        "content_text": "Flooding warning in Area 51",
        "platforms": ["twitter"]
    }
    async with AsyncClient(
        transport=ASGITransport(app=app_ngo), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/social", json=payload)
    
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden. Admin access required."}
