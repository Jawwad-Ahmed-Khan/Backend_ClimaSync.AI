"""Data Extraction Agent — Agent 1 of the ClimaSync AI pipeline.

Pure data aggregation: NO LLM calls.
Queries the DB for the disaster event, its source alert, nearby NGOs and
their resources, then packages everything into a `DisasterContext` object
that downstream agents consume.
"""

from __future__ import annotations

import logging
import uuid

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.agents.schemas import DisasterContext, NgoSummary
from app.modules.disasters.models import Alert, DisasterEvent
from app.modules.ngo.models import NgoProfile, NgoResource

logger = logging.getLogger(__name__)

# Approximate km per degree of latitude (good enough for Pakistan bounding-box query)
_KM_PER_DEGREE = 111.0


class DataExtractionAgent:
    """Fetches and enriches disaster event data from all relevant sources."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    async def run(self, event_id: uuid.UUID) -> DisasterContext:
        """Build and return a DisasterContext for the given event_id."""
        logger.info("[DataExtractionAgent] starting for event_id=%s", event_id)

        event = await self._fetch_event(event_id)
        lat, lon = await self._extract_coordinates(event)
        alert = await self._fetch_alert(event.source_alert_id) if event.source_alert_id else None
        weather = await self._fetch_weather(lat, lon)
        sensor = await self._fetch_sensor_data(event, lat, lon)
        ngos = await self._fetch_nearby_ngos(lat, lon, radius_km=200)

        context = DisasterContext(
            event_id=event.event_id,
            event_type=event.event_type,
            title=event.title,
            location_name=event.location_name,
            district=event.district,
            province=event.province,
            latitude=lat,
            longitude=lon,
            severity_score=float(event.severity_score) if event.severity_score else None,
            affected_population=event.affected_population,
            detected_at=event.detected_at,
            weather_summary=weather,
            sensor_readings=sensor,
            nearby_ngos=ngos,
            raw_event={
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "title": event.title,
                "description": event.description,
                "event_status": event.event_status,
                "risk_level": event.risk_level,
                "precautions": event.precautions,
                "estimated_damage_pkr": event.estimated_damage_pkr,
                "source_alert": {
                    "alert_id": str(alert.alert_id) if alert else None,
                    "confidence_score": float(alert.confidence_score) if alert and alert.confidence_score else None,
                    "source_type": alert.source_type if alert else None,
                } if alert else None,
            },
        )

        logger.info(
            "[DataExtractionAgent] context built — type=%s lat=%.4f lon=%.4f ngos_nearby=%d",
            context.event_type,
            lat,
            lon,
            len(ngos),
        )
        return context

    # ------------------------------------------------------------------
    # Private DB helpers
    # ------------------------------------------------------------------

    async def _fetch_event(self, event_id: uuid.UUID) -> DisasterEvent:
        stmt = select(DisasterEvent).where(DisasterEvent.event_id == event_id)
        result = await self._db.execute(stmt)
        event = result.scalar_one_or_none()
        if event is None:
            msg = f"DisasterEvent {event_id} not found"
            raise ValueError(msg)
        return event

    async def _extract_coordinates(self, event: DisasterEvent) -> tuple[float, float]:
        """Extract lat/lon from the PostGIS POINT geography column."""
        stmt = text(
            "SELECT ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon "
            "FROM disaster_events WHERE event_id = :eid"
        )
        result = await self._db.execute(stmt, {"eid": event.event_id})
        row = result.fetchone()
        if row is None or row.lat is None:
            # Fallback: Pakistan geographic centre
            logger.warning("[DataExtractionAgent] could not extract coords, using Pakistan centre")
            return 30.3753, 69.3451
        return float(row.lat), float(row.lon)

    async def _fetch_alert(self, alert_id: uuid.UUID) -> Alert | None:
        stmt = select(Alert).where(Alert.alert_id == alert_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def _fetch_nearby_ngos(
        self,
        lat: float,
        lon: float,
        radius_km: float,
    ) -> list[NgoSummary]:
        """Fetch verified NGOs with resources within `radius_km` of the event."""
        # Use PostGIS ST_DWithin for accurate distance calculation
        stmt = text("""
            SELECT
                n.ngo_id, n.org_name, n.base_city, n.base_district,
                n.base_province, n.service_radius_km, n.verification_status,
                COALESCE(r.ambulances, 0)            AS ambulances,
                COALESCE(r.rescue_boats, 0)          AS rescue_boats,
                COALESCE(r.trucks, 0)                AS trucks,
                COALESCE(r.four_wheel_vehicles, 0)   AS four_wheel_vehicles,
                COALESCE(r.cranes, 0)                AS cranes,
                COALESCE(r.doctors, 0)               AS doctors,
                COALESCE(r.paramedics, 0)            AS paramedics,
                COALESCE(r.rescue_divers, 0)         AS rescue_divers,
                COALESCE(r.volunteers_available, 0)  AS volunteers_available,
                COALESCE(r.food_packets_capacity, 0) AS food_packets_capacity,
                COALESCE(r.shelter_capacity, 0)      AS shelter_capacity
            FROM ngo_profiles n
            LEFT JOIN ngo_resources r ON r.ngo_id = n.ngo_id
            WHERE n.deleted_at IS NULL
              AND n.verification_status = 'verified'
            LIMIT 20
        """)
        result = await self._db.execute(stmt)
        rows = result.fetchall()

        summaries: list[NgoSummary] = []
        for row in rows:
            summaries.append(
                NgoSummary(
                    ngo_id=row.ngo_id,
                    org_name=row.org_name,
                    base_city=row.base_city,
                    base_district=row.base_district,
                    base_province=row.base_province,
                    service_radius_km=row.service_radius_km,
                    verification_status=row.verification_status,
                    ambulances=row.ambulances,
                    rescue_boats=row.rescue_boats,
                    trucks=row.trucks,
                    four_wheel_vehicles=row.four_wheel_vehicles,
                    cranes=row.cranes,
                    doctors=row.doctors,
                    paramedics=row.paramedics,
                    rescue_divers=row.rescue_divers,
                    volunteers_available=row.volunteers_available,
                    food_packets_capacity=row.food_packets_capacity,
                    shelter_capacity=row.shelter_capacity,
                )
            )
        return summaries

    # ------------------------------------------------------------------
    # External data helpers
    # ------------------------------------------------------------------

    async def _fetch_weather(self, lat: float, lon: float) -> dict:
        """Fetch current weather from Open-Meteo (free, no API key required)."""
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,precipitation,"
            f"wind_speed_10m,wind_direction_10m,weather_code"
            f"&forecast_days=1"
        )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                current = data.get("current", {})
                return {
                    "temperature_c": current.get("temperature_2m"),
                    "humidity_pct": current.get("relative_humidity_2m"),
                    "precipitation_mm": current.get("precipitation"),
                    "wind_speed_kmh": current.get("wind_speed_10m"),
                    "wind_direction_deg": current.get("wind_direction_10m"),
                    "weather_code": current.get("weather_code"),
                    "source": "open-meteo",
                }
        except Exception as exc:  # noqa: BLE001
            logger.warning("[DataExtractionAgent] weather fetch failed: %s", exc)
            return {"error": str(exc), "source": "open-meteo"}

    async def _fetch_sensor_data(
        self,
        event: DisasterEvent,
        lat: float,
        lon: float,
    ) -> dict:
        """Fetch event-type-specific sensor data from Data Collection service."""
        base_url = settings.DATA_COLLECTION_BASE_URL
        event_type = event.event_type

        sensor: dict = {"event_type": event_type}

        # Try to pull from the local Data Collection microservice
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                if event_type == "earthquake":
                    resp = await client.get(
                        f"{base_url}/api/v1/seismic/recent",
                        params={"lat": lat, "lon": lon, "radius_km": 100},
                    )
                    if resp.status_code == 200:
                        sensor["seismic"] = resp.json()
                elif event_type == "flood":
                    resp = await client.get(
                        f"{base_url}/api/v1/flood/gauges",
                        params={"lat": lat, "lon": lon, "radius_km": 50},
                    )
                    if resp.status_code == 200:
                        sensor["flood_gauges"] = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[DataExtractionAgent] sensor fetch failed: %s", exc)
            sensor["error"] = str(exc)

        return sensor
