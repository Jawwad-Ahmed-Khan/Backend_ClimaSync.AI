"""NGO repository — data access for ngo_profiles and ngo_resources tables.

Provides creation methods used during OTP verification to set up the
NGO organisation profile and default resource inventory, and lookup
methods used during login. Also supports partial profile updates.
"""

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ngo.models import NgoProfile, NgoResource


class NgoRepository:
    """Data access for ngo_profiles and ngo_resources tables."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with async session."""
        self.session = session

    async def create_profile(
        self,
        *,
        ngo_id: uuid.UUID,
        org_name: str,
        org_email: str,
        registration_number: str,
    ) -> NgoProfile:
        """Insert a new NGO profile and return it."""
        profile = NgoProfile(
            ngo_id=ngo_id,
            org_name=org_name,
            org_email=org_email,
            registration_number=registration_number,
        )
        self.session.add(profile)
        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def create_resources(
        self,
        ngo_id: uuid.UUID,
    ) -> NgoResource:
        """Insert default NGO resources (all zero) and return them."""
        resources = NgoResource(ngo_id=ngo_id)
        self.session.add(resources)
        await self.session.flush()
        await self.session.refresh(resources)
        return resources

    async def get_profile_by_ngo_id(
        self,
        ngo_id: uuid.UUID,
    ) -> NgoProfile | None:
        """Return the NGO profile for a given user/ngo id, or None."""
        stmt = select(NgoProfile).where(NgoProfile.ngo_id == ngo_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_profile(
        self,
        ngo_id: uuid.UUID,
        **fields: Any,
    ) -> NgoProfile | None:
        """Partial update of NGO profile fields. Returns the updated profile."""
        # Filter out None values — only update fields explicitly provided
        update_data = {k: v for k, v in fields.items() if v is not None}
        if not update_data:
            return await self.get_profile_by_ngo_id(ngo_id)

        stmt = (
            update(NgoProfile)
            .where(NgoProfile.ngo_id == ngo_id)
            .values(**update_data)
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.get_profile_by_ngo_id(ngo_id)

