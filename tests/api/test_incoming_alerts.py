"""API tests for POST /api/v1/alerts/incoming and WebSocket /ws/alerts."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# -------------------------------------------------------------------------
# Sample payloads (mirrors the spec examples exactly)
# -------------------------------------------------------------------------

EARTHQUAKE_PAYLOAD = {
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
    "forecast_horizon_h": None,
    "detected_at": "2025-07-15T10:18:00+05:00",
    "seismic_event_id": "us2024test001",
    "weather_location_id": None,
    "gauge_id": None,
}

FLOOD_PAYLOAD = {
    "breach_id": "b2c3d4e5-f6a7-8901-2345-6789abcdef01",
    "source_api": "google_flood_hub",
    "disaster_kind": "flood",
    "metric_name": "gauge_pct_of_danger",
    "location_name": "Sukkur",
    "district": "sukkur",
    "province": "sindh",
    "latitude": 27.7135,
    "longitude": 68.8524,
    "observed_value": 105.3,
    "threshold_value": 100.0,
    "breach_severity": "emergency",
    "unit": "percent",
    "observation_time": "2025-07-17T02:30:00+05:00",
    "is_forecast": True,
    "forecast_horizon_h": 36,
    "detected_at": "2025-07-15T14:30:00+05:00",
    "gauge_id": "google-gauge-sukkur-001",
    "seismic_event_id": None,
    "weather_location_id": None,
}

HEATWAVE_PAYLOAD = {
    "breach_id": "c3d4e5f6-a7b8-9012-3456-789abcdef012",
    "source_api": "open_meteo",
    "disaster_kind": "heatwave",
    "metric_name": "temp_max_c",
    "location_name": "Larkana",
    "district": "larkana",
    "province": "sindh",
    "latitude": 27.5589,
    "longitude": 68.2120,
    "observed_value": 49.5,
    "threshold_value": 49.0,
    "breach_severity": "emergency",
    "unit": "celsius",
    "observation_time": "2025-07-18T14:00:00+05:00",
    "is_forecast": True,
    "forecast_horizon_h": 72,
    "detected_at": "2025-07-15T14:00:00+05:00",
    "weather_location_id": "larkana_27.5589_68.2120",
    "seismic_event_id": None,
    "gauge_id": None,
}


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _make_app_with_mock_service():
    """Build the FastAPI app with IncomingAlertService fully mocked."""
    from app.main import create_app
    from app.modules.incoming_alerts.dependencies import get_incoming_alert_service

    mock_service = MagicMock()
    mock_service.process = AsyncMock(return_value=None)

    app = create_app()
    app.dependency_overrides[get_incoming_alert_service] = lambda: mock_service
    return app, mock_service


# -------------------------------------------------------------------------
# POST /api/v1/alerts/incoming — happy path
# -------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [EARTHQUAKE_PAYLOAD, FLOOD_PAYLOAD, HEATWAVE_PAYLOAD],
    ids=["earthquake", "flood", "heatwave"],
)
async def test_incoming_alert_created(payload: dict) -> None:
    """All three payload shapes return 201 with the correct breach_id."""
    app, _ = _make_app_with_mock_service()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/alerts/incoming", json=payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "success"
    assert body["alert_id"] == payload["breach_id"]


# -------------------------------------------------------------------------
# POST /api/v1/alerts/incoming — invalid API key
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_incoming_alert_rejects_bad_api_key() -> None:
    """Returns 403 when INCOMING_ALERT_API_KEY is set and key is wrong."""
    from app.core.config import settings

    app, _ = _make_app_with_mock_service()

    with patch.object(settings, "INCOMING_ALERT_API_KEY", "super-secret-key"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/alerts/incoming",
                json=EARTHQUAKE_PAYLOAD,
                headers={"X-API-Key": "wrong-key"},
            )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_incoming_alert_accepts_correct_api_key() -> None:
    """Returns 201 when INCOMING_ALERT_API_KEY matches the header value."""
    from app.core.config import settings

    app, _ = _make_app_with_mock_service()

    with patch.object(settings, "INCOMING_ALERT_API_KEY", "super-secret-key"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/alerts/incoming",
                json=EARTHQUAKE_PAYLOAD,
                headers={"X-API-Key": "super-secret-key"},
            )

    assert response.status_code == 201


# -------------------------------------------------------------------------
# POST /api/v1/alerts/incoming — duplicate breach_id
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_incoming_alert_conflict_on_duplicate() -> None:
    """Returns 409 when the service raises HTTPException(409)."""
    from fastapi import HTTPException
    from app.main import create_app
    from app.modules.incoming_alerts.dependencies import get_incoming_alert_service

    mock_service = MagicMock()
    mock_service.process = AsyncMock(
        side_effect=HTTPException(status_code=409, detail="Already processed")
    )

    app = create_app()
    app.dependency_overrides[get_incoming_alert_service] = lambda: mock_service

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/alerts/incoming", json=EARTHQUAKE_PAYLOAD)

    assert response.status_code == 409


# -------------------------------------------------------------------------
# POST /api/v1/alerts/incoming — validation failure
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_incoming_alert_rejects_missing_required_fields() -> None:
    """Returns 422 when required fields are absent."""
    app, _ = _make_app_with_mock_service()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/alerts/incoming",
            json={"breach_id": "only-id-no-other-fields"},
        )

    assert response.status_code == 422


# -------------------------------------------------------------------------
# WebSocket /ws/alerts — auth tests
# -------------------------------------------------------------------------


def _make_valid_admin_token() -> str:
    """Generate a real JWT for an admin user using the app's secret."""
    from app.core.security import create_access_token

    return create_access_token(
        subject=str(uuid.uuid4()),
        extra_claims={"role": "admin"},
    )


def _make_ngo_token() -> str:
    """Generate a real JWT for an NGO user."""
    from app.core.security import create_access_token

    return create_access_token(
        subject=str(uuid.uuid4()),
        extra_claims={"role": "ngo_user"},
    )


def test_ws_rejects_missing_token() -> None:
    """WebSocket closes with 1008 when no token query param is provided."""
    from starlette.testclient import TestClient
    from app.main import create_app

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    with pytest.raises(Exception):
        with client.websocket_connect("/ws/alerts"):
            pass


def test_ws_rejects_ngo_token() -> None:
    """WebSocket closes with 1008 when the token role is 'ngo_user'."""
    from starlette.testclient import TestClient
    from app.main import create_app

    app = create_app()
    ngo_token = _make_ngo_token()
    client = TestClient(app, raise_server_exceptions=False)

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/alerts?token={ngo_token}"):
            pass


def test_ws_accepts_admin_token_and_broadcasts() -> None:
    """Admin token connects and receives a broadcast pushed by the manager."""
    import json
    import asyncio
    from starlette.testclient import TestClient
    from app.main import create_app
    from app.websockets.manager import admin_ws_manager

    app = create_app()
    client = TestClient(app)
    admin_token = _make_valid_admin_token()

    with client.websocket_connect(f"/ws/alerts?token={admin_token}") as ws:
        # Broadcast synchronously by running the coroutine in the test event loop
        test_payload = {
            "breach_id": "ws-test-001",
            "disaster_kind": "earthquake",
            "breach_severity": "emergency",
        }
        asyncio.get_event_loop().run_until_complete(
            admin_ws_manager.broadcast_alert(test_payload)
        )

        raw = ws.receive_text()
        message = json.loads(raw)
        assert message["event"] == "NEW_DISASTER_ALERT"
        assert message["data"]["breach_id"] == "ws-test-001"
