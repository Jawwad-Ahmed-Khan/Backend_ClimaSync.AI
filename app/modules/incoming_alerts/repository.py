"""Repository for incoming_alerts table — data access only, no business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.incoming_alerts.models import IncomingAlert
from app.modules.incoming_alerts.schemas import IncomingBreachPayload


class IncomingAlertRepository:
    """Handles persistence for raw incoming breach payloads."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, payload: IncomingBreachPayload) -> IncomingAlert:
        """Persist the payload and return the saved ORM instance."""
        alert = IncomingAlert(
            breach_id=payload.breach_id,
            source_api=payload.source_api,
            disaster_kind=payload.disaster_kind,
            location_name=payload.location_name,
            district=payload.district,
            province=payload.province,
            latitude=payload.latitude,
            longitude=payload.longitude,
            metric_name=payload.metric_name,
            observed_value=payload.observed_value,
            threshold_value=payload.threshold_value,
            unit=payload.unit,
            breach_severity=payload.breach_severity,
            observation_time=payload.observation_time,
            detected_at=payload.detected_at,
            is_forecast=payload.is_forecast,
            forecast_horizon_h=payload.forecast_horizon_h,
            seismic_event_id=payload.seismic_event_id,
            weather_location_id=payload.weather_location_id,
            gauge_id=payload.gauge_id,
        )
        self.session.add(alert)
        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def exists(self, breach_id: str) -> bool:
        """Return True if a record with this breach_id already exists."""
        stmt = select(IncomingAlert.breach_id).where(
            IncomingAlert.breach_id == breach_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
