"""Social profile SQLAlchemy models.

Maps to 'social_posts' and 'social_post_platforms' tables.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base_model import BaseModel, SoftDeleteMixin


class SocialPost(BaseModel, SoftDeleteMixin):
    """Social post mapped to 'social_posts' table."""

    __tablename__ = "social_posts"

    social_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disaster_events.event_id", ondelete="SET NULL"),
        nullable=True,
    )
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        ENUM("draft", "queued", "published", "failed", name="social_post_status", create_type=False),
        nullable=False,
        server_default=text("'draft'::social_post_status"),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_type: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'admin'")
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    # Relationships
    platforms: Mapped[list[SocialPostPlatform]] = relationship(
        "SocialPostPlatform",
        back_populates="post",
        cascade="all, delete-orphan",
    )


class SocialPostPlatform(BaseModel):
    """Platform-specific tracking model."""

    __tablename__ = "social_post_platforms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    social_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("social_posts.social_post_id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(
        ENUM("twitter", "facebook", "instagram", "linkedin", "tiktok", name="social_platform", create_type=False),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        ENUM("draft", "queued", "published", "failed", name="social_post_status", create_type=False),
        nullable=False,
        server_default=text("'queued'::social_post_status"),
    )
    post_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metrics
    views: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    likes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    shares: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    comments: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    # Relationships
    post: Mapped[SocialPost] = relationship(
        "SocialPost",
        back_populates="platforms",
    )
