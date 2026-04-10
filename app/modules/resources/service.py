"""Resource module service logic bridging repo actions and schemas."""

import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.modules.resources.repository import ResourceRepository
from app.modules.resources.schemas import (
    AdminSearchPayload,
    AreaCreate,
    NGOFullResourceProfile,
    ResourcePatch,
    SpecializationCreate,
)


class ResourceService:
    """Validation layer strictly constraining writes."""

    def __init__(self, repo: ResourceRepository) -> None:
        self.repo = repo

    async def get_my_profile(self, ngo_id: uuid.UUID) -> NGOFullResourceProfile:
        """Fetch unified block representing the NGO physical environment."""
        resources = await self.repo.get_or_create_resource(ngo_id)
        areas = await self.repo.get_areas(ngo_id)
        specializations = await self.repo.get_specializations(ngo_id)
        
        return NGOFullResourceProfile(
            ngo_id=ngo_id,
            capabilities=resources,
            areas=areas,
            specializations=specializations
        )

    async def patch_capabilities(self, ngo_id: uuid.UUID, payload: ResourcePatch) -> dict:
        """Selectively overwrite integer tracks without requiring full payload passing."""
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No valid update variables parsed.")
            
        resource_obj = await self.repo.get_or_create_resource(ngo_id)
        await self.repo.update_resource(resource_obj, updates)
        return {"status": "success", "message": "Capabilities updated"}

    async def add_operational_area(self, ngo_id: uuid.UUID, payload: AreaCreate) -> dict:
        """Map geographic deployment constraints allowing postgres to detect dupes natively."""
        try:
            await self.repo.add_area(ngo_id, payload.province, payload.district)
            return {"status": "success", "message": "Area added successfully"}
        except IntegrityError:
            raise HTTPException(
                status_code=400, 
                detail="Area constraint violation: You already have this operational zone marked."
            )

    async def remove_operational_area(self, ngo_id: uuid.UUID, area_id: uuid.UUID) -> dict:
        success = await self.repo.delete_area(ngo_id, area_id)
        if not success:
            raise HTTPException(status_code=404, detail="Area record not found on your profile.")
        return {"status": "success"}

    async def add_specialization(self, ngo_id: uuid.UUID, payload: SpecializationCreate) -> dict:
        try:
            await self.repo.add_specialization(ngo_id, payload.specialization)
            return {"status": "success", "message": "Specialization successfully added"}
        except IntegrityError:
            raise HTTPException(
                status_code=400, 
                detail="Constraint violation: This categorization exists on your profile already."
            )

    async def remove_specialization(self, ngo_id: uuid.UUID, spec_id: uuid.UUID) -> dict:
        success = await self.repo.delete_specialization(ngo_id, spec_id)
        if not success:
            raise HTTPException(status_code=404, detail="Specialization record not found.")
        return {"status": "success"}

    async def execute_dispatcher_query(self, payload: AdminSearchPayload) -> list[dict]:
        """
        Executes Admin query against SQL mapping, manually assembling result block.
        Using dictionaries is safe here to combine standard fields with resources.
        """
        ngos = await self.repo.admin_search(payload)
        
        results = []
        for n in ngos:
            # Inject resource map organically
            resource_obj = await self.repo.get_or_create_resource(n.ngo_id)
            results.append({
                "ngo_id": n.ngo_id,
                "ngo_name": n.organization_name,
                "contact_email": n.contact_email,
                "contact_phone": n.contact_phone,
                "rating": float(n.rating) if getattr(n, "rating", None) else None,
                "resources": resource_obj
            })
            
        return results
