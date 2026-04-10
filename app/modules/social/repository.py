"""Social module repository — data access and aggregated view reads."""

import uuid
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.social.models import SocialPost, SocialPostPlatform


class SocialRepository:
    """Repository connecting to social_posts, platforms, and frontend views."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_frontend_views(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """Reads instantly from the optimized postgres aggregated view."""
        stmt = text("""
            SELECT * FROM social_posts_frontend_view
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        result = await self.session.execute(stmt, {"limit": limit, "offset": offset})
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_frontend_view_by_id(self, post_id: uuid.UUID) -> dict | None:
        """Reads a specific aggregated post."""
        stmt = text("""
            SELECT * FROM social_posts_frontend_view
            WHERE social_post_id = :post_id
        """)
        result = await self.session.execute(stmt, {"post_id": post_id})
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def create_post(self, data: dict[str, Any], platforms: list[str]) -> SocialPost:
        """Create a social post alongside queued platform records."""
        # Create core post
        post = SocialPost(**data)
        self.session.add(post)
        await self.session.flush()

        # Add target platforms
        platform_records = []
        for p in platforms:
            plat = SocialPostPlatform(
                social_post_id=post.social_post_id,
                platform=p,
                status="queued"
            )
            platform_records.append(plat)
            self.session.add(plat)
        
        await self.session.flush()
        await self.session.refresh(post)
        return post

    async def update_platform_engagement(self, post_id: uuid.UUID, platform: str, updates: dict[str, Any]) -> SocialPostPlatform | None:
        """Patch metrics on a specific platform branch."""
        stmt = (
            update(SocialPostPlatform)
            .where(SocialPostPlatform.social_post_id == post_id, SocialPostPlatform.platform == platform)
            .values(**updates)
        )
        await self.session.execute(stmt)
        await self.session.flush()
        
        # return updated platform
        select_stmt = select(SocialPostPlatform).where(SocialPostPlatform.social_post_id == post_id, SocialPostPlatform.platform == platform)
        result = await self.session.execute(select_stmt)
        return result.scalar_one_or_none()
