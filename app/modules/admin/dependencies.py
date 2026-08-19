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
    MessageRepository,
)
from app.modules.admin.services.ngo_service import AdminNgoService
from app.modules.admin.services.report_service import AdminReportService
from app.modules.admin.services.audit_service import AdminAuditService
from app.modules.admin.services.message_service import AdminMessageService
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


def get_message_repository(session: Annotated[AsyncSession, Depends(get_db)]) -> MessageRepository:
    return MessageRepository(session)


def get_admin_ngo_service(
    ngo_admin_repo: Annotated[AdminNgoRepository, Depends(get_admin_ngo_repository)],
    ngo_repo: Annotated[NgoRepository, Depends(get_ngo_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> AdminNgoService:
    from app.modules.admin.services.audit_service import AdminAuditService
    return AdminNgoService(
        ngo_admin_repo=ngo_admin_repo,
        ngo_repo=ngo_repo,
        audit_service=AdminAuditService(audit_repo),
    )

def get_admin_report_service(
    report_repo: Annotated[AdminReportRepository, Depends(get_admin_report_repository)],
) -> AdminReportService:
    return AdminReportService(report_repo)

def get_admin_audit_service(
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> AdminAuditService:
    return AdminAuditService(audit_repo)


def get_admin_message_service(
    message_repo: Annotated[MessageRepository, Depends(get_message_repository)],
) -> AdminMessageService:
    return AdminMessageService(message_repo)


async def get_current_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Dependency that enforces admin or super_admin roles."""
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Forbidden. Admin access required.")
    return current_user


AdminNgoServiceDep = Annotated[AdminNgoService, Depends(get_admin_ngo_service)]
AdminReportServiceDep = Annotated[AdminReportService, Depends(get_admin_report_service)]
AdminAuditServiceDep = Annotated[AdminAuditService, Depends(get_admin_audit_service)]
AdminMessageServiceDep = Annotated[AdminMessageService, Depends(get_admin_message_service)]
CurrentAdminDep = Annotated[User, Depends(get_current_admin)]
