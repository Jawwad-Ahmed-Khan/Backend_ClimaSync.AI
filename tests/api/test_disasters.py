"""API Tests for Disasters Module."""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport

from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user

async def override_get_current_user() -> User:
    return User(
        user_id=uuid.uuid4(),
        email="testadmin@example.com",
        role="admin",
        is_active=True,
    )

@pytest.mark.asyncio
async def test_list_alerts_empty() -> None:
    """Test listing alerts when none exist."""
    from app.main import create_app
    app = create_app()
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/alerts")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_disaster_events_empty() -> None:
    """Test listing disaster events when none exist."""
    from app.main import create_app
    app = create_app()
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/disasters")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
