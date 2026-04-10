"""Separated service exclusively handling NGO profile updates and reads."""

import uuid
from app.modules.auth.exceptions import InvalidCredentialsException, NoProfileFoundException
from app.modules.users.repository import UserRepository
from app.modules.ngo.repository import NgoRepository
from app.modules.auth.schemas import UpdateProfileRequest, UserProfileResponse

class AuthProfileService:
    def __init__(self, user_repo: UserRepository, ngo_repo: NgoRepository) -> None:
        self._user_repo = user_repo
        self._ngo_repo = ngo_repo

    async def get_me(self, user_id: uuid.UUID) -> UserProfileResponse:
        """Return the full profile for the authenticated user."""
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise InvalidCredentialsException()

        profile = await self._ngo_repo.get_profile_by_ngo_id(user_id)
        if profile is None:
            raise NoProfileFoundException()

        return UserProfileResponse(
            user_id=user.user_id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            email_verified=user.email_verified,
            org_name=profile.org_name,
            head_of_operations=profile.head_of_operations,
            phone=profile.phone,
            website=profile.website,
            base_city=profile.base_city,
            base_district=profile.base_district,
            base_province=profile.base_province,
            verification_status=profile.verification_status,
            last_login_at=user.last_login_at,
        )

    async def update_profile(self, user_id: uuid.UUID, data: UpdateProfileRequest) -> UserProfileResponse:
        """Update the NGO profile for the authenticated user."""
        profile = await self._ngo_repo.get_profile_by_ngo_id(user_id)
        if profile is None:
            raise NoProfileFoundException()

        update_fields = data.model_dump(exclude_unset=True)
        if update_fields:
            await self._ngo_repo.update_profile(user_id, **update_fields)

        return await self.get_me(user_id)
