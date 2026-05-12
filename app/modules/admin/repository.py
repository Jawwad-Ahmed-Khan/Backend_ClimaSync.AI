"""Admin module repository — data access for admin profiles, audits, metrics, and messaging."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.models import AdminProfile, AuditLog, Conversation, Message
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

    # --- Dashboard Stats (NEW) ---

    async def get_dashboard_stats(self) -> dict:
        """Get all aggregate counts for the admin command center."""
        stats = {}
        
        # Active disasters
        r = await self.session.execute(text("SELECT COUNT(*) FROM disaster_events WHERE event_status = 'active' AND deleted_at IS NULL"))
        stats["active_disasters"] = r.scalar() or 0

        # Total alerts
        r = await self.session.execute(text("SELECT COUNT(*) FROM alerts WHERE deleted_at IS NULL"))
        stats["total_alerts"] = r.scalar() or 0

        # New alerts (unverified)
        r = await self.session.execute(text("SELECT COUNT(*) FROM alerts WHERE status = 'new' AND deleted_at IS NULL"))
        stats["new_alerts"] = r.scalar() or 0

        # Total tasks
        r = await self.session.execute(text("SELECT COUNT(*) FROM tasks WHERE deleted_at IS NULL"))
        stats["total_tasks"] = r.scalar() or 0

        # Pending tasks
        r = await self.session.execute(text("SELECT COUNT(*) FROM tasks WHERE status IN ('pending_approval', 'unallocated') AND deleted_at IS NULL"))
        stats["pending_tasks"] = r.scalar() or 0

        # Completed tasks
        r = await self.session.execute(text("SELECT COUNT(*) FROM tasks WHERE status = 'completed' AND deleted_at IS NULL"))
        stats["completed_tasks"] = r.scalar() or 0

        # NGO counts
        r = await self.session.execute(text("SELECT COUNT(*) FROM ngo_profiles WHERE deleted_at IS NULL"))
        stats["total_ngos"] = r.scalar() or 0

        r = await self.session.execute(text("SELECT COUNT(*) FROM ngo_profiles WHERE verification_status = 'pending' AND deleted_at IS NULL"))
        stats["pending_ngos"] = r.scalar() or 0

        r = await self.session.execute(text("SELECT COUNT(*) FROM ngo_profiles WHERE verification_status = 'verified' AND deleted_at IS NULL"))
        stats["verified_ngos"] = r.scalar() or 0

        # Total users
        r = await self.session.execute(text("SELECT COUNT(*) FROM users WHERE deleted_at IS NULL"))
        stats["total_users"] = r.scalar() or 0

        # Social posts
        r = await self.session.execute(text("SELECT COUNT(*) FROM social_posts WHERE deleted_at IS NULL"))
        stats["total_social_posts"] = r.scalar() or 0

        return stats

    # --- Detailed Report (NEW) ---

    async def get_disasters_by_type(self) -> list[dict]:
        """Get disaster count grouped by event_type."""
        stmt = text("""
            SELECT event_type, COUNT(*) as count 
            FROM disaster_events 
            WHERE deleted_at IS NULL
            GROUP BY event_type
            ORDER BY count DESC
        """)
        result = await self.session.execute(stmt)
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_tasks_over_time(self) -> list[dict]:
        """Get task created/completed counts over last 12 months."""
        stmt = text("""
            SELECT 
                TO_CHAR(created_at, 'Mon') as month,
                COUNT(*) as created,
                COUNT(*) FILTER (WHERE status = 'completed') as completed
            FROM tasks
            WHERE deleted_at IS NULL
              AND created_at >= NOW() - INTERVAL '12 months'
            GROUP BY EXTRACT(MONTH FROM created_at), TO_CHAR(created_at, 'Mon')
            ORDER BY EXTRACT(MONTH FROM created_at)
        """)
        result = await self.session.execute(stmt)
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_ngo_leaderboard(self, limit: int = 20) -> list[dict]:
        """Get top NGOs by completed tasks count + rating."""
        stmt = text("""
            SELECT
                np.ngo_id,
                np.org_name,
                COALESCE(np.rating, 0) as rating,
                COUNT(t.task_id) FILTER (WHERE t.status = 'completed') as tasks_completed
            FROM ngo_profiles np
            LEFT JOIN tasks t ON t.assigned_ngo_id = np.ngo_id AND t.deleted_at IS NULL
            WHERE np.deleted_at IS NULL AND np.verification_status = 'verified'
            GROUP BY np.ngo_id, np.org_name, np.rating
            ORDER BY tasks_completed DESC, rating DESC
            LIMIT :limit
        """)
        result = await self.session.execute(stmt, {"limit": limit})
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_total_tasks_count(self) -> int:
        r = await self.session.execute(text("SELECT COUNT(*) FROM tasks WHERE deleted_at IS NULL"))
        return r.scalar() or 0

    async def get_total_disasters_count(self) -> int:
        r = await self.session.execute(text("SELECT COUNT(*) FROM disaster_events WHERE deleted_at IS NULL"))
        return r.scalar() or 0

    async def get_avg_completion_rate(self) -> float:
        r = await self.session.execute(text("""
            SELECT CASE WHEN COUNT(*) > 0 
                THEN ROUND(COUNT(*) FILTER (WHERE status = 'completed')::numeric / COUNT(*)::numeric * 100, 1)
                ELSE 0 
            END as rate
            FROM tasks WHERE deleted_at IS NULL
        """))
        return float(r.scalar() or 0)


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

    async def get_ngo_detailed(self, ngo_id: uuid.UUID) -> dict | None:
        """Get a single NGO with resources, specializations, and task counts."""
        # Base NGO profile
        stmt = text("""
            SELECT 
                np.ngo_id, np.org_name, np.org_email, np.registration_number,
                np.verification_status, COALESCE(np.rating, 0) as rating,
                np.province, np.city, np.address, np.contact_phone,
                np.website, np.founded_year, np.total_members, np.description,
                np.is_active, np.created_at,
                COUNT(t.task_id) FILTER (WHERE t.status = 'completed') as tasks_completed,
                COUNT(t.task_id) FILTER (WHERE t.status = 'in_progress') as tasks_in_progress
            FROM ngo_profiles np
            LEFT JOIN tasks t ON t.assigned_ngo_id = np.ngo_id AND t.deleted_at IS NULL
            WHERE np.ngo_id = :ngo_id AND np.deleted_at IS NULL
            GROUP BY np.ngo_id
        """)
        result = await self.session.execute(stmt, {"ngo_id": ngo_id})
        row = result.fetchone()
        if not row:
            return None
        ngo = dict(row._mapping)

        # Resources
        res_stmt = text("""
            SELECT resource_type, quantity, description 
            FROM ngo_resources 
            WHERE ngo_id = :ngo_id
        """)
        res_result = await self.session.execute(res_stmt, {"ngo_id": ngo_id})
        ngo["resources"] = [dict(r._mapping) for r in res_result.fetchall()]

        # Specializations
        spec_stmt = text("""
            SELECT specialization 
            FROM ngo_specializations 
            WHERE ngo_id = :ngo_id
        """)
        spec_result = await self.session.execute(spec_stmt, {"ngo_id": ngo_id})
        ngo["specializations"] = [r[0] for r in spec_result.fetchall()]

        # Operational areas
        area_stmt = text("""
            SELECT province || ' - ' || district as area
            FROM ngo_operational_areas 
            WHERE ngo_id = :ngo_id
        """)
        area_result = await self.session.execute(area_stmt, {"ngo_id": ngo_id})
        ngo["operational_areas"] = [r[0] for r in area_result.fetchall()]

        return ngo


# --- Messaging Repository (NEW) ---

class MessageRepository:
    """Data access for admin messaging system."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_conversation(self, user_a: uuid.UUID, user_b: uuid.UUID) -> Conversation:
        """Find existing conversation between two users or create one."""
        stmt = text("""
            SELECT * FROM conversations 
            WHERE (user_a_id = :ua AND user_b_id = :ub) OR (user_a_id = :ub AND user_b_id = :ua)
            LIMIT 1
        """)
        result = await self.session.execute(stmt, {"ua": user_a, "ub": user_b})
        row = result.fetchone()
        if row:
            return await self.session.get(Conversation, row._mapping["conversation_id"])

        conv = Conversation(user_a_id=user_a, user_b_id=user_b)
        self.session.add(conv)
        await self.session.flush()
        await self.session.refresh(conv)
        return conv

    async def create_message(self, data: dict) -> Message:
        """Insert a new message."""
        msg = Message(**data)
        self.session.add(msg)
        await self.session.flush()
        await self.session.refresh(msg)
        return msg

    async def get_conversations_for_user(self, user_id: uuid.UUID) -> list[dict]:
        """List conversations with last message and unread count for a user."""
        stmt = text("""
            SELECT 
                c.conversation_id,
                CASE WHEN c.user_a_id = :uid THEN c.user_b_id ELSE c.user_a_id END as participant_id,
                COALESCE(u.full_name, np.org_name, 'Unknown User') as participant_name,
                CASE 
                    WHEN u2.role = 'ngo_user' THEN 'ngo_user'
                    ELSE COALESCE(u2.role, 'user')
                END as participant_type,
                (SELECT content FROM messages m2 WHERE m2.conversation_id = c.conversation_id ORDER BY m2.created_at DESC LIMIT 1) as last_message,
                (SELECT created_at FROM messages m3 WHERE m3.conversation_id = c.conversation_id ORDER BY m3.created_at DESC LIMIT 1) as last_message_at,
                (SELECT COUNT(*) FROM messages m4 WHERE m4.conversation_id = c.conversation_id AND m4.receiver_id = :uid AND m4.is_read = false) as unread_count
            FROM conversations c
            LEFT JOIN users u2 ON u2.user_id = CASE WHEN c.user_a_id = :uid THEN c.user_b_id ELSE c.user_a_id END
            LEFT JOIN admin_profiles u ON u.admin_id = CASE WHEN c.user_a_id = :uid THEN c.user_b_id ELSE c.user_a_id END
            LEFT JOIN ngo_profiles np ON np.ngo_id = CASE WHEN c.user_a_id = :uid THEN c.user_b_id ELSE c.user_a_id END
            WHERE c.user_a_id = :uid OR c.user_b_id = :uid
            ORDER BY last_message_at DESC NULLS LAST
        """)
        result = await self.session.execute(stmt, {"uid": user_id})
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_messages(self, conversation_id: uuid.UUID, limit: int = 50, offset: int = 0) -> list[Message]:
        """Get messages for a conversation ordered chronologically."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_messages_read(self, conversation_id: uuid.UUID, reader_id: uuid.UUID) -> int:
        """Mark all messages in a conversation as read for a specific user."""
        stmt = (
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.receiver_id == reader_id,
                Message.is_read == False,
            )
            .values(is_read=True)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
