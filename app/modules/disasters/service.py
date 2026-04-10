"""Disasters service — business logic for alerts and disaster events."""

import uuid

from fastapi import HTTPException

from app.modules.disasters.repository import AlertRepository, DisasterEventRepository
from app.modules.disasters.schemas import (
    AlertCreate,
    AlertUpdate,
    DisasterEventCreate,
    DisasterEventUpdate,
)


class DisasterService:
    """Business logic for disaster events and alerts."""

    def __init__(
        self,
        alert_repo: AlertRepository,
        event_repo: DisasterEventRepository,
    ) -> None:
        self.alert_repo = alert_repo
        self.event_repo = event_repo

    # --- Alerts ---

    async def create_alert(self, data: AlertCreate, user_id: uuid.UUID) -> dict:
        alert_data = data.model_dump()
        alert_data["created_by"] = user_id
        
        # Additional business rules can go here (e.g. notify admin if severity > 8)
        alert = await self.alert_repo.create_alert(alert_data)
        return alert

    async def get_alert(self, alert_id: uuid.UUID) -> dict:
        alert = await self.alert_repo.get_by_id(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert

    async def list_alerts(self, limit: int = 100, offset: int = 0) -> list[dict]:
        return await self.alert_repo.list_alerts(limit=limit, offset=offset)

    async def update_alert(self, alert_id: uuid.UUID, data: AlertUpdate, user_id: uuid.UUID) -> dict:
        alert = await self.alert_repo.get_by_id(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        update_data = data.model_dump(exclude_unset=True)
        # If status changes to 'verified', mark the user and time
        if "status" in update_data and update_data["status"] == "verified" and alert.status != "verified":
            from datetime import datetime, timezone
            update_data["verified_by"] = user_id
            update_data["verified_at"] = datetime.now(timezone.utc)
        
        updated_alert = await self.alert_repo.update_alert(alert, update_data)
        return updated_alert

    # --- Disaster Events ---

    async def create_event(self, data: DisasterEventCreate, user_id: uuid.UUID) -> dict:
        event_data = data.model_dump()
        event_data["created_by"] = user_id
        event = await self.event_repo.create_event(event_data)
        return event

    async def get_event(self, event_id: uuid.UUID) -> dict:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Disaster event not found")
        return event

    async def list_events(self, limit: int = 100, offset: int = 0) -> list[dict]:
        return await self.event_repo.list_events(limit=limit, offset=offset)

    async def update_event(self, event_id: uuid.UUID, data: DisasterEventUpdate, user_id: uuid.UUID) -> dict:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Disaster event not found")
        
        update_data = data.model_dump(exclude_unset=True)
        # Handle verification similarly based on event_status changes
        
        updated_event = await self.event_repo.update_event(event, update_data)
        return updated_event
    
    async def soft_delete_event(self, event_id: uuid.UUID) -> dict:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Disaster event not found")
        await self.event_repo.soft_delete(event)
        return {"message": "Disaster event isolated/deleted locally successfully."}
