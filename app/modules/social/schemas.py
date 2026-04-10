"""Social module Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SocialPlatformType = Literal["twitter", "facebook", "instagram", "linkedin", "tiktok"]
SocialPostStatusType = Literal["draft", "queued", "published", "failed"]


class SocialPostCreate(BaseModel):
    """Schema for creating a new social announcement."""
    content_text: str | None = Field(None, description="The main broadcast text")
    content_image_url: str | None = None
    video_url: str | None = None
    scheduled_at: datetime | None = None
    event_id: uuid.UUID | None = Field(None, description="Link this post contextually to a disaster event")
    platforms: list[SocialPlatformType] = Field(default_factory=list, description="Target networks to queue against")


class SocialEngagementUpdate(BaseModel):
    """Webhook schema to patch aggregated analytics."""
    likes_increment: int = Field(0, ge=0)
    shares_increment: int = Field(0, ge=0)
    views_increment: int = Field(0, ge=0)
    comments_increment: int = Field(0, ge=0)
    status: SocialPostStatusType | None = None


class SocialPostFrontendViewResponse(BaseModel):
    """Reflects the highly efficient social_posts_frontend_view structure."""
    social_post_id: uuid.UUID
    event_id: uuid.UUID | None = None
    content_text: str | None = None
    content_image_url: str | None = None
    video_url: str | None = None
    status: str
    created_by: uuid.UUID | None = None
    created_by_type: str
    scheduled_at: datetime | None = None
    failed_reason: str | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    
    # Aggregated View Metrics
    platforms: list[str] = Field(default_factory=list)
    engagement_views: int = 0
    engagement_likes: int = 0
    engagement_shares: int = 0
    engagement_comments: int = 0

    model_config = ConfigDict(from_attributes=True)
