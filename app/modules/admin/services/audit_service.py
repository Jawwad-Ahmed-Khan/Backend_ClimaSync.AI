"""System auditing isolation logic."""

import uuid
from app.modules.admin.repository import AuditLogRepository

class AdminAuditService:
    def __init__(self, audit_repo: AuditLogRepository) -> None:
        self.audit_repo = audit_repo

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
        await self.audit_repo.create_log({
            "user_id": admin_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "old_values": old_values,
            "new_values": new_values,
            "ip_address": ip_address,
        })

    async def list_audit_logs(self, limit: int = 100, offset: int = 0) -> list[dict]:
        return await self.audit_repo.get_logs(limit=limit, offset=offset)
