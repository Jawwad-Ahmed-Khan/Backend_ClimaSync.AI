"""Resource manipulation mapping and search querying."""

import uuid
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.ngo.models import NgoProfile, NgoResource
from app.modules.resources.models import (
    NGOOperationalArea,
    NGOSpecialization,
)
from app.modules.resources.schemas import AdminSearchPayload


class ResourceRepository:
    """Operations mapping for physical unit limits and search queries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_resource(self, ngo_id: uuid.UUID) -> NgoResource:
        """Fetches resource counter. If empty, initialized to defaults."""
        result = await self.session.execute(select(NgoResource).where(NgoResource.ngo_id == ngo_id))
        resource = result.scalar_one_or_none()
        
        if not resource:
            resource = NgoResource(ngo_id=ngo_id)
            self.session.add(resource)
            await self.session.flush()
            
        return resource

    async def update_resource(self, resource: NgoResource, updates: dict[str, Any]) -> NgoResource:
        for key, value in updates.items():
            setattr(resource, key, value)
        self.session.add(resource)
        await self.session.flush()
        await self.session.refresh(resource)
        return resource

    # ---- Areas ----
    async def get_areas(self, ngo_id: uuid.UUID) -> list[NGOOperationalArea]:
        result = await self.session.execute(
            select(NGOOperationalArea).where(NGOOperationalArea.ngo_id == ngo_id)
        )
        return list(result.scalars().all())

    async def add_area(self, ngo_id: uuid.UUID, province: str, district: str) -> NGOOperationalArea:
        area = NGOOperationalArea(ngo_id=ngo_id, province=province, district=district)
        self.session.add(area)
        await self.session.flush()
        await self.session.refresh(area)
        return area

    async def delete_area(self, ngo_id: uuid.UUID, area_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(NGOOperationalArea).where(
                and_(NGOOperationalArea.id == area_id, NGOOperationalArea.ngo_id == ngo_id)
            )
        )
        area = result.scalar_one_or_none()
        if area:
            await self.session.delete(area)
            await self.session.flush()
            return True
        return False

    # ---- Specializations ----
    async def get_specializations(self, ngo_id: uuid.UUID) -> list[NGOSpecialization]:
        result = await self.session.execute(
            select(NGOSpecialization).where(NGOSpecialization.ngo_id == ngo_id)
        )
        return list(result.scalars().all())

    async def add_specialization(self, ngo_id: uuid.UUID, specialization: str) -> NGOSpecialization:
        spec = NGOSpecialization(ngo_id=ngo_id, specialization=specialization)
        self.session.add(spec)
        await self.session.flush()
        await self.session.refresh(spec)
        return spec

    async def delete_specialization(self, ngo_id: uuid.UUID, spec_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(NGOSpecialization).where(
                and_(NGOSpecialization.id == spec_id, NGOSpecialization.ngo_id == ngo_id)
            )
        )
        spec = result.scalar_one_or_none()
        if spec:
            await self.session.delete(spec)
            await self.session.flush()
            return True
        return False

    # ---- Discovery Engine ----
    async def admin_search(self, payload: AdminSearchPayload) -> list[NgoProfile]:
        """Powerful dispatcher method utilizing dynamic SQL filters to pinpoint NGOs."""
        
        # Start matching active NGO profiles. Use selectinload on their child relationships 
        # so memory mapping is incredibly efficient instead of nested n+1 loops
        stmt = select(NgoProfile).where(NgoProfile.deleted_at.is_(None))
        
        # We need to JOIN related resource requirements if ANY resource constraint exists
        needs_resource_join = any([
            payload.min_ambulances,
            payload.min_rescue_boats,
            payload.min_doctors,
            payload.min_volunteers,
            payload.min_shelter_capacity
        ])
        
        if needs_resource_join:
            stmt = stmt.join(NgoResource, NgoProfile.ngo_id == NgoResource.ngo_id)
            
            if payload.min_ambulances:
                stmt = stmt.where(NgoResource.ambulances >= payload.min_ambulances)
            if payload.min_rescue_boats:
                stmt = stmt.where(NgoResource.rescue_boats >= payload.min_rescue_boats)
            if payload.min_doctors:
                stmt = stmt.where(NgoResource.doctors >= payload.min_doctors)
            if payload.min_volunteers:
                stmt = stmt.where(NgoResource.volunteers_available >= payload.min_volunteers)
            if payload.min_shelter_capacity:
                stmt = stmt.where(NgoResource.shelter_capacity >= payload.min_shelter_capacity)

        # Region constraints
        needs_area_join = any([payload.province, payload.district])
        if needs_area_join:
            stmt = stmt.join(NGOOperationalArea, NgoProfile.ngo_id == NGOOperationalArea.ngo_id)
            
            if payload.province:
                stmt = stmt.where(NGOOperationalArea.province.ilike(f"%{payload.province}%"))
            if payload.district:
                stmt = stmt.where(NGOOperationalArea.district.ilike(f"%{payload.district}%"))
                
        # Discipline constraints
        if payload.specialization:
            stmt = stmt.join(NGOSpecialization, NgoProfile.ngo_id == NGOSpecialization.ngo_id)
            stmt = stmt.where(NGOSpecialization.specialization.ilike(f"%{payload.specialization}%"))

        stmt = stmt.limit(payload.limit)
        
        # We don't map relationships backward structurally since NGO is the central node,
        # but we can resolve the full Profile
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())
