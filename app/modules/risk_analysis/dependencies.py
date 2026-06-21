"""Risk Analysis module dependency injection."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.dependencies import DbSessionDep
from app.modules.risk_analysis.repository import RiskAnalysisRepository
from app.modules.risk_analysis.service import RiskAnalysisService


def get_risk_analysis_repo(session: DbSessionDep) -> RiskAnalysisRepository:
    return RiskAnalysisRepository(session)


def get_risk_analysis_service(repo: Annotated[RiskAnalysisRepository, Depends(get_risk_analysis_repo)]) -> RiskAnalysisService:
    return RiskAnalysisService(repo)


RiskAnalysisServiceDep = Annotated[RiskAnalysisService, Depends(get_risk_analysis_service)]
