"""API Tests for Admin Module."""

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
async def test_admin_reports_success(app_admin) -> None:
    """Admin should get 200 OK for reports."""
    async with AsyncClient(
        transport=ASGITransport(app=app_admin), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/admin/reports")
    
    assert response.status_code == 200
    assert "active_users_count" in response.json()

@pytest.mark.asyncio
async def test_admin_reports_forbidden_for_ngo(app_ngo) -> None:
    """Non-admin should get 403 Forbidden for admin endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app_ngo), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/admin/reports")
    
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden. Admin access required."}

@pytest.mark.asyncio
async def test_admin_list_audit_logs(app_admin) -> None:
    """Admin should be able to view audit logs."""
    async with AsyncClient(
        transport=ASGITransport(app=app_admin), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/admin/audit-logs")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_admin_list_ngos(app_admin) -> None:
    """Admin should be able to list NGOs."""
    async with AsyncClient(
        transport=ASGITransport(app=app_admin), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/admin/ngos")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
