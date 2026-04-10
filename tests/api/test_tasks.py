"""API Tests for Tasks Module."""

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
async def test_tasks_list_tasks_accessible_for_all(app_ngo) -> None:
    """Reading tasks feed is accessible (though filtered internally for NGOs)."""
    async with AsyncClient(
        transport=ASGITransport(app=app_ngo), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/tasks")
    
    # Needs to be 200, returning empty list or tasks dict because db is empty 
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_tasks_create_forbidden_for_ngo(app_ngo) -> None:
    """Non-admin should get 403 Forbidden for task creation endpoints."""
    payload = {
        "task_label": "Evacuate Zone B",
        "task_type": "evacuation",
        "description": "Proceed to Area B"
    }
    async with AsyncClient(
        transport=ASGITransport(app=app_ngo), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/tasks", json=payload)
    
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden. Admin access required."}


