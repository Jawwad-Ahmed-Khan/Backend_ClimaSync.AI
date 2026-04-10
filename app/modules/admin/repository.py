"""Admin module repository — data access for admin profiles, audits, and metrics."""

import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.models import AdminProfile, AuditLog
from app.modules.ngo.models import NgoProfile


class AdminProfileRepository:
    """Data access for admin_profiles."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, admin_id: uuid.UUID) -> AdminProfile | None:
        stmt = select(AdminProfile).where(AdminProfile.admin_id == admin_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class AuditLogRepository:
    """Data access for immutable audit_logs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_log(self, data: dict[str, Any]) -> AuditLog:
        """Insert a new audit log entry."""
        log = AuditLog(**data)
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        return log

    async def get_logs(self, limit: int = 100, offset: int = 0) -> list[AuditLog]:
        """Retrieve audit logs."""
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class AdminReportRepository:
    """Queries for fetching global metrics/reports from views."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_users_count(self) -> int:
        stmt = text("SELECT COUNT(*) FROM active_users")
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_active_ngos_count(self) -> int:
        stmt = text("SELECT COUNT(*) FROM active_ngo_profiles")
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_pending_ngos_count(self) -> int:
        stmt = text("SELECT COUNT(*) FROM ngo_profiles WHERE verification_status = 'pending'")
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_active_alerts_count(self) -> int:
        stmt = text("SELECT COUNT(*) FROM active_alerts")
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_active_disasters_count(self) -> int:
        stmt = text("SELECT COUNT(*) FROM active_disaster_events")
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_disaster_metrics(self) -> list[dict]:
        stmt = text("SELECT event_id, total_tasks, completed_tasks, in_progress_tasks, unallocated_tasks, assigned_ngos FROM disaster_event_metrics")
        result = await self.session.execute(stmt)
        # Convert rows to dict
        return [dict(row._mapping) for row in result.fetchall()]


class AdminNgoRepository:
    """Admin-specific read access to NGOs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_ngos(self, status: str | None = None, limit: int = 100, offset: int = 0) -> list[NgoProfile]:
        stmt = select(NgoProfile).order_by(NgoProfile.created_at.desc())
        if status:
            stmt = stmt.where(NgoProfile.verification_status == status)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
