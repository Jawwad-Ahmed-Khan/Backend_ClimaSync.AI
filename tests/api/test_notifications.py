"""API Tests for Notification module."""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.modules.auth.dependencies import get_current_user
from app.modules.users.models import User

# Mocks
async def override_get_current_user_ngo() -> User:
    return User(
        user_id=uuid.uuid4(),
        email="testngo@example.com",
        role="ngo_user",
        is_active=True,
    )

@pytest.fixture
def app_ngo():
    app = create_app()
    app.dependency_overrides[get_current_user] = override_get_current_user_ngo
    return app

@pytest.mark.asyncio
async def test_get_notifications(app_ngo) -> None:
    """NGOs can retrieve their notifications."""
    async with AsyncClient(
        transport=ASGITransport(app=app_ngo), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/notifications")
    
    # 200 OK because database handles get safely, returns list
    assert response.status_code == 200 
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_unread_count(app_ngo) -> None:
    """NGOs can retrieve unread count."""
    async with AsyncClient(
        transport=ASGITransport(app=app_ngo), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/notifications/unread-count")
    
    assert response.status_code == 200 
    assert "unread_count" in response.json()

@pytest.mark.asyncio
async def test_mark_notifications_read(app_ngo) -> None:
    """NGOs can mark specific notifications read."""
    payload = {"notification_ids": [str(uuid.uuid4())]}
    async with AsyncClient(
        transport=ASGITransport(app=app_ngo), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/notifications/mark-read", json=payload)
    
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_mark_all_notifications_read(app_ngo) -> None:
    """NGOs can mark all notifications read."""
    async with AsyncClient(
        transport=ASGITransport(app=app_ngo), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/notifications/read-all")
    
    assert response.status_code == 200
