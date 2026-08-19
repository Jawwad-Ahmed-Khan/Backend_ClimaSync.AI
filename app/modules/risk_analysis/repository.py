"""Risk Analysis repository — data access for AI assessments."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.risk_analysis.models import RiskAnalysis


class RiskAnalysisRepository:
    """Handles persistence of AI-generated risk reports."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: dict[str, Any]) -> RiskAnalysis:
        """Save a new risk assessment record."""
        record = RiskAnalysis(**data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get_by_alert_id(self, alert_id: uuid.UUID) -> list[RiskAnalysis]:
        """Fetch all assessments for a specific alert."""
        from sqlalchemy import select
        stmt = select(RiskAnalysis).where(RiskAnalysis.alert_id == alert_id).order_by(RiskAnalysis.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
