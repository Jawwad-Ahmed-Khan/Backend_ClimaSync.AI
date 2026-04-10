"""Endpoints binding NGOs capabilities internally."""

import uuid

from fastapi import APIRouter, HTTPException, Path

from app.modules.admin.dependencies import CurrentAdminDep
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.resources.dependencies import ResourceServiceDep
from app.modules.resources.schemas import (
    AdminSearchPayload,
    AreaCreate,
    NGOFullResourceProfile,
    NGOSearchResult,
    ResourcePatch,
    SpecializationCreate,
)

router = APIRouter(prefix="/resources", tags=["Resources & Operational Areas"])


def enforce_ngo_role(user_role: str):
    """Local guard dictating endpoints are NGO native."""
    if user_role != "ngo_user":
        raise HTTPException(status_code=403, detail="Forbidden. Only NGOs can manage intrinsic capabilities.")


@router.get(
    "/me",
    response_model=NGOFullResourceProfile,
    summary="Get Internal NGO Configuration",
)
async def get_my_configuration(current_user: CurrentUserDep, service: ResourceServiceDep):
    """Extract everything concerning the logged-in NGO."""
    enforce_ngo_role(current_user.role)
    return await service.get_my_profile(current_user.user_id)


@router.patch(
    "/me/capacity",
    summary="Update Capability Count",
)
async def update_resource_capacity(
    payload: ResourcePatch, current_user: CurrentUserDep, service: ResourceServiceDep
):
    """Scale capacity numbers implicitly avoiding overwrites."""
    enforce_ngo_role(current_user.role)
    return await service.patch_capabilities(current_user.user_id, payload)


@router.post(
    "/me/areas",
    summary="Expand Operational Zone",
)
async def add_operational_area(
    payload: AreaCreate, current_user: CurrentUserDep, service: ResourceServiceDep
):
    enforce_ngo_role(current_user.role)
    return await service.add_operational_area(current_user.user_id, payload)


@router.delete(
    "/me/areas/{area_id}",
    summary="Retract Operational Zone",
)
async def remove_operational_area(
    current_user: CurrentUserDep, service: ResourceServiceDep, area_id: uuid.UUID = Path(...)
):
    enforce_ngo_role(current_user.role)
    return await service.remove_operational_area(current_user.user_id, area_id)


@router.post(
    "/me/specializations",
    summary="Add Specialization Label",
)
async def add_specialization(
    payload: SpecializationCreate, current_user: CurrentUserDep, service: ResourceServiceDep
):
    enforce_ngo_role(current_user.role)
    return await service.add_specialization(current_user.user_id, payload)


@router.delete(
    "/me/specializations/{spec_id}",
    summary="Remove Specialization Label",
)
async def remove_specialization(
    current_user: CurrentUserDep, service: ResourceServiceDep, spec_id: uuid.UUID = Path(...)
):
    enforce_ngo_role(current_user.role)
    return await service.remove_specialization(current_user.user_id, spec_id)


@router.post(
    "/search",
    response_model=list[NGOSearchResult],
    summary="Admin Search Intersecting NGO Capabilities",
)
async def map_responders_query(
    payload: AdminSearchPayload, current_admin: CurrentAdminDep, service: ResourceServiceDep
):
    """
    Powerful API triggering a mass SQL-JOIN sequence detecting active NGOs checking
    exact thresholds dynamically across equipment counts and zones.
    """
    return await service.execute_dispatcher_query(payload)
