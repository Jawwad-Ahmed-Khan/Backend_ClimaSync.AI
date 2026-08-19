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

    async def get_dashboard_stats(self) -> dict:
        """Get aggregated dashboard stats for command center."""
        return await self.report_repo.get_dashboard_stats()

    async def generate_detailed_report(self) -> dict:
        """Generate rich analytics report with breakdowns."""
        return {
            "total_disasters": await self.report_repo.get_total_disasters_count(),
            "total_tasks": await self.report_repo.get_total_tasks_count(),
            "avg_completion_rate": await self.report_repo.get_avg_completion_rate(),
            "disasters_by_type": await self.report_repo.get_disasters_by_type(),
            "tasks_over_time": await self.report_repo.get_tasks_over_time(),
            "ngo_leaderboard": await self.report_repo.get_ngo_leaderboard(),
        }
