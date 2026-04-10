"""Disasters repository — data access for alerts and disaster events.

Contains ONLY database query logic. No business rules or decisions.
Returns model instances, None, or scalar values.
"""

import uuid
from decimal import Decimal

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.disasters.models import Alert, DisasterEvent, DisasterSource


class AlertRepository:
    """Data access for alerts table."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_alert(self, alert_data: dict) -> Alert:
        """Insert a new alert and return it."""
        alert = Alert(**alert_data)
        self.session.add(alert)
        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def get_by_id(self, alert_id: uuid.UUID) -> Alert | None:
        """Find an alert by ID."""
        stmt = select(Alert).where(and_(Alert.alert_id == alert_id, Alert.deleted_at.is_(None)))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_alerts(self, limit: int = 100, offset: int = 0) -> list[Alert]:
        """List active alerts."""
        stmt = (
            select(Alert)
            .where(Alert.deleted_at.is_(None))
            .order_by(Alert.detected_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_alert(self, alert: Alert, update_data: dict) -> Alert:
        """Update an existing alert object in session."""
        for key, value in update_data.items():
            setattr(alert, key, value)
        await self.session.flush()
        await self.session.refresh(alert)
        return alert


class DisasterEventRepository:
    """Data access for disaster_events table."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_event(self, event_data: dict) -> DisasterEvent:
        """Insert a new disaster event and return it."""
        event = DisasterEvent(**event_data)
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def get_by_id(self, event_id: uuid.UUID) -> DisasterEvent | None:
        """Find a disaster event by ID."""
        stmt = select(DisasterEvent).where(
            and_(DisasterEvent.event_id == event_id, DisasterEvent.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_events(self, limit: int = 100, offset: int = 0) -> list[DisasterEvent]:
        """List active disaster events."""
        stmt = (
            select(DisasterEvent)
            .where(DisasterEvent.deleted_at.is_(None))
            .order_by(DisasterEvent.detected_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_event(self, event: DisasterEvent, update_data: dict) -> DisasterEvent:
        """Update an existing event object in session."""
        for key, value in update_data.items():
            setattr(event, key, value)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def soft_delete(self, event: DisasterEvent) -> None:
        event.deleted_at = func.now()
        await self.session.flush()
