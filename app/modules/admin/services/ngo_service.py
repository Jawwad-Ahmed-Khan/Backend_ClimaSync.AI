"""Admin service for handling strict NGO verifications."""

import uuid
from datetime import datetime, timezone
from fastapi import HTTPException

from app.modules.admin.repository import AdminNgoRepository
from app.modules.ngo.repository import NgoRepository
from app.modules.admin.services.audit_service import AdminAuditService
from app.modules.admin.schemas import NgoVerificationUpdate

class AdminNgoService:
    def __init__(
        self,
        ngo_admin_repo: AdminNgoRepository,
        ngo_repo: NgoRepository,
        audit_service: AdminAuditService,
    ) -> None:
        self.ngo_admin_repo = ngo_admin_repo
        self.ngo_repo = ngo_repo
        self.audit_service = audit_service

    async def list_ngos(self, status: str | None = None, limit: int = 100, offset: int = 0) -> list[dict]:
        return await self.ngo_admin_repo.get_ngos(status=status, limit=limit, offset=offset)

    async def verify_ngo(self, ngo_id: uuid.UUID, admin_id: uuid.UUID, data: NgoVerificationUpdate, ip_address: str | None = None) -> dict:
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

        if new_status == "verified" and old_status != "verified":
            update_payload["verified_by"] = admin_id
            update_payload["verified_at"] = datetime.now(timezone.utc)

        updated_ngo = await self.ngo_repo.update_profile(ngo_id, **update_payload)

        await self.audit_service.log_audit(
            admin_id=admin_id,
            action=f"Changed NGO status to {new_status}",
            entity_type="ngo_profiles",
            entity_id=ngo_id,
            old_values={"verification_status": old_status},
            new_values={"verification_status": new_status},
            ip_address=ip_address,
        )

        return updated_ngo
