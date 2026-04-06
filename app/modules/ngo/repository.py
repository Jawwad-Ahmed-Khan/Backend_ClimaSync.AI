"""NGO repository — data access for ngo_profiles and ngo_resources tables.

Provides creation methods used during OTP verification to set up the
NGO organisation profile and default resource inventory.
"""

import uuid

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
