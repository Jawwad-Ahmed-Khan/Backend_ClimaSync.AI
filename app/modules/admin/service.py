"""Admin service — business logic for NGO verification and metrics reporting."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from app.modules.admin.repository import (
    AdminNgoRepository,
    AdminProfileRepository,
    AdminReportRepository,
    AuditLogRepository,
)
from app.modules.admin.schemas import NgoVerificationUpdate
from app.modules.ngo.repository import NgoRepository


class AdminService:
    """Core logic mapped to administrative actions."""

    def __init__(
        self,
        profile_repo: AdminProfileRepository,
        audit_repo: AuditLogRepository,
        report_repo: AdminReportRepository,
        ngo_admin_repo: AdminNgoRepository,
        ngo_repo: NgoRepository,
    ) -> None:
        self.profile_repo = profile_repo
        self.audit_repo = audit_repo
        self.report_repo = report_repo
        self.ngo_admin_repo = ngo_admin_repo
        self.ngo_repo = ngo_repo

    async def log_audit(
        self,
        admin_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        old_values: dict | None = None,
        new_values: dict | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Standardized method to write to immutable audit log."""
        await self.audit_repo.create_log({
            "user_id": admin_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "old_values": old_values,
            "new_values": new_values,
            "ip_address": ip_address,
        })

    # --- NGO Management ---

    async def list_ngos(self, status: str | None = None, limit: int = 100, offset: int = 0) -> list[dict]:
        """Return a listed set of NGO profiles filtering optionally by status."""
        profiles = await self.ngo_admin_repo.get_ngos(status=status, limit=limit, offset=offset)
        # Using model_dump equivalent or just returning ORM for router to convert
        return profiles

    async def verify_ngo(self, ngo_id: uuid.UUID, admin_id: uuid.UUID, data: NgoVerificationUpdate, ip_address: str | None = None) -> dict:
        """Check the NGO, update its status, log the verification, and save via repo."""
        ngo = await self.ngo_repo.get_profile_by_ngo_id(ngo_id)
        if not ngo:
            raise HTTPException(status_code=404, detail="NGO profile not found")

        old_status = ngo.verification_status
        new_status = data.verification_status

        if new_status in ("suspended", "rejected") and not data.suspended_reason:
            raise HTTPException(status_code=400, detail="Suspended/Rejected status requires a reason")

        update_payload = {
            "verification_status": new_status,
            "suspended_reason": data.suspended_reason if new_status in ("suspended", "rejected") else None,
        }

        # If it was just verified
        if new_status == "verified" and old_status != "verified":
            update_payload["verified_by"] = admin_id
            update_payload["verified_at"] = datetime.now(timezone.utc)

        # Apply update
        updated_ngo = await self.ngo_repo.update_profile(ngo_id, **update_payload)

        # Log it
        await self.log_audit(
            admin_id=admin_id,
            action=f"Changed NGO status to {new_status}",
            entity_type="ngo_profiles",
            entity_id=ngo_id,
            old_values={"verification_status": old_status},
            new_values={"verification_status": new_status},
            ip_address=ip_address,
        )

        return updated_ngo

    # --- Audit Logs ---

    async def list_audit_logs(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """Return system audit logs."""
        logs = await self.audit_repo.get_logs(limit=limit, offset=offset)
        return logs

    # --- Reports ---

    async def generate_global_report(self) -> dict:
        """Synthesize metrics from across the system utilizing view queries."""
        return {
            "active_users_count": await self.report_repo.get_active_users_count(),
            "active_ngos_count": await self.report_repo.get_active_ngos_count(),
            "pending_ngos_count": await self.report_repo.get_pending_ngos_count(),
            "active_alerts_count": await self.report_repo.get_active_alerts_count(),
            "active_disasters_count": await self.report_repo.get_active_disasters_count(),
            "disaster_metrics": await self.report_repo.get_disaster_metrics(),
        }
