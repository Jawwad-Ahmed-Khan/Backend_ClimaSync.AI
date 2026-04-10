"""Admin service for generating statistical aggregations."""

from app.modules.admin.repository import AdminReportRepository

class AdminReportService:
    def __init__(self, report_repo: AdminReportRepository) -> None:
        self.report_repo = report_repo

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
