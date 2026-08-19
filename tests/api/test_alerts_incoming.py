import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

@pytest.fixture
def app():
    from app.main import create_app
    return create_app()

@pytest.fixture
def valid_payload():
    return {
        "breach_id": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
        "source_api": "usgs",
        "disaster_kind": "earthquake",
        "metric_name": "magnitude",
        "location_name": "Muzaffarabad",
        "district": "muzaffarabad",
        "province": "azad_kashmir",
        "latitude": 34.3596,
        "longitude": 73.4715,
        "observed_value": 6.2,
        "threshold_value": 6.0,
        "breach_severity": "emergency",
        "unit": "richter",
        "observation_time": "2025-07-15T10:15:00+05:00",
        "is_forecast": False,
        "detected_at": "2025-07-15T10:18:00+05:00",
        "seismic_event_id": "us2024test001"
    }

@pytest.mark.asyncio
async def test_incoming_alert_success(app, valid_payload):
    # Mock the DB service so we don't write test data into the real DB during CI/CD
    # We patch the Dependency so it doesn't fail on DB operations.
    with patch("app.modules.disasters.service.DisasterService.create_alert", new_callable=AsyncMock) as mock_create_alert:
        mock_create_alert.return_value = {"id": "mocked"}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/alerts/incoming", json=valid_payload)
            
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "success"
            assert data["alert_id"] == valid_payload["breach_id"]
            
        mock_create_alert.assert_called_once()

@pytest.mark.asyncio
async def test_incoming_alert_invalid_api_key(app, valid_payload):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"x-api-key": "wrong_key_123"}
        response = await ac.post("/api/v1/alerts/incoming", json=valid_payload, headers=headers)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid API Key"

@pytest.mark.asyncio
async def test_incoming_alert_missing_fields(app, valid_payload):
    invalid_payload = valid_payload.copy()
    del invalid_payload["latitude"]  # Latitude is required
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/alerts/incoming", json=invalid_payload)
        
        assert response.status_code == 422
        assert "detail" in response.json()

def test_incoming_alert_websocket_broadcast(app, valid_payload):
    """
    Test using FastAPI's synchronous TestClient to manage WebSocket connections safely.
    """
    # Mocking the service to avoid real DB transactions
    with patch("app.modules.disasters.service.DisasterService.create_alert", new_callable=AsyncMock) as mock_create_alert:
        mock_create_alert.return_value = {"id": "mocked"}
        
        with TestClient(app) as client:
            with client.websocket_connect("/ws/alerts") as websocket:
                # Fire the POST request
                response = client.post("/api/v1/alerts/incoming", json=valid_payload)
                assert response.status_code == 201
                
                # Check if it was broadcasted
                data = websocket.receive_json()
                assert data["event"] == "NEW_DISASTER_ALERT"
                assert data["data"]["breach_id"] == valid_payload["breach_id"]
                assert data["data"]["disaster_kind"] == "earthquake"
