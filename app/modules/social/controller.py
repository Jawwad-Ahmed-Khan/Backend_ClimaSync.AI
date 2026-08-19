"""Social controller — HTTP endpoints for news and platform broadcasts."""

import uuid
from typing import Literal

from fastapi import APIRouter, Path, Query, Request

from app.core.limiter import limiter
from app.modules.admin.dependencies import CurrentAdminDep
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.social.dependencies import SocialServiceDep
from app.modules.social.schemas import (
    SocialEngagementUpdate,
    SocialPostCreate,
    SocialPostFrontendViewResponse,
)

router = APIRouter(prefix="/social", tags=["Social / News"])


@router.get(
    "",
    response_model=list[SocialPostFrontendViewResponse],
    summary="List Social Posts & News",
    description="Retrieve the aggregated broadcast timeline.",
)
async def list_posts(
    current_user: CurrentUserDep,
    service: SocialServiceDep,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Fetch timeline via SQL View read optimization."""
    return await service.list_posts(limit=limit, offset=offset)


@router.get(
    "/{post_id}",
    response_model=SocialPostFrontendViewResponse,
    summary="Get Specific Social Post",
)
async def get_post(
    current_user: CurrentUserDep,
    service: SocialServiceDep,
    post_id: uuid.UUID = Path(...),
):
    """Retrieve detailed post with platform array."""
    return await service.get_post(post_id)


@router.post(
    "",
    response_model=SocialPostFrontendViewResponse,
    summary="Create & Broadcast Post",
    description="Requires Admin. Will automatically map to platform queues.",
)
@limiter.limit("5/minute")
async def create_post(
    request: Request,
    data: SocialPostCreate,
    current_admin: CurrentAdminDep,
    service: SocialServiceDep,
):
    """Publish a new announcement."""
    return await service.create_post(
        creator_id=current_admin.user_id,
        creator_type="admin",
        payload=data,
    )


@router.patch(
    "/{post_id}/platforms/{platform}",
    response_model=SocialPostFrontendViewResponse,
    summary="Update Platform Analytics (Webhook)",
    description="Increment likes, views, shares, or modify publish status.",
)
async def update_engagement(
    updates: SocialEngagementUpdate,
    current_admin: CurrentAdminDep,
    service: SocialServiceDep,
    post_id: uuid.UUID = Path(...),
    platform: Literal["twitter", "facebook", "instagram", "linkedin", "tiktok"] = Path(...),
):
    """Modify engagement variables simulating a webhook update."""
    return await service.apply_engagement(
        post_id=post_id,
        platform=platform,
        updates=updates,
    )


@router.delete(
    "/{post_id}",
    summary="Soft delete a social post",
    description="Marks a social post as deleted (soft delete). Requires Admin.",
)
async def delete_post(
    current_admin: CurrentAdminDep,
    service: SocialServiceDep,
    post_id: uuid.UUID = Path(...),
):
    """Soft-delete a social post."""
    await service.soft_delete_post(post_id)
    return {"message": "Post deleted successfully"}
