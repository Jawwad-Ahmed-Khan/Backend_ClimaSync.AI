"""Admin module dependency injection wiring."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.admin.repository import (
    AdminNgoRepository,
    AdminProfileRepository,
    AdminReportRepository,
    AuditLogRepository,
)
from app.modules.admin.service import AdminService
from app.modules.auth.dependencies import get_current_user
from app.modules.ngo.repository import NgoRepository
from app.modules.users.models import User


def get_admin_profile_repository(session: Annotated[AsyncSession, Depends(get_db)]) -> AdminProfileRepository:
    return AdminProfileRepository(session)


def get_audit_log_repository(session: Annotated[AsyncSession, Depends(get_db)]) -> AuditLogRepository:
    return AuditLogRepository(session)


def get_admin_report_repository(session: Annotated[AsyncSession, Depends(get_db)]) -> AdminReportRepository:
    return AdminReportRepository(session)


def get_admin_ngo_repository(session: Annotated[AsyncSession, Depends(get_db)]) -> AdminNgoRepository:
    return AdminNgoRepository(session)


def get_ngo_repository(session: Annotated[AsyncSession, Depends(get_db)]) -> NgoRepository:
    return NgoRepository(session)


def get_admin_service(
    profile_repo: Annotated[AdminProfileRepository, Depends(get_admin_profile_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    report_repo: Annotated[AdminReportRepository, Depends(get_admin_report_repository)],
    ngo_admin_repo: Annotated[AdminNgoRepository, Depends(get_admin_ngo_repository)],
    ngo_repo: Annotated[NgoRepository, Depends(get_ngo_repository)],
) -> AdminService:
    return AdminService(
        profile_repo=profile_repo,
        audit_repo=audit_repo,
        report_repo=report_repo,
        ngo_admin_repo=ngo_admin_repo,
        ngo_repo=ngo_repo,
    )


async def get_current_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Dependency that enforces admin or super_admin roles."""
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Forbidden. Admin access required.")
    return current_user


AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
CurrentAdminDep = Annotated[User, Depends(get_current_admin)]
