"""Risk Analysis controller — HTTP endpoints for risk assessment proxy."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.limiter import limiter
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.risk_analysis.dependencies import RiskAnalysisServiceDep
from app.modules.risk_analysis.schemas import RiskAnalysisRequest, RiskAnalysisResponse

router = APIRouter(prefix="/risk-analysis", tags=["Risk Analysis"])


@router.post(
    "/assess",
    response_model=RiskAnalysisResponse,
    summary="Trigger AI Risk Analysis",
    description=(
        "Sends a disaster breach payload to the Risk Analysis Agent microservice. "
        "The agent performs multi-source reasoning (DB + web search) and returns a "
        "comprehensive risk assessment report. May take up to 3 minutes."
    ),
)
@limiter.limit("10/minute")
async def trigger_risk_assessment(
    request: Request,
    payload: RiskAnalysisRequest,
    current_user: CurrentUserDep,
    service: RiskAnalysisServiceDep,
) -> RiskAnalysisResponse:
    """Proxy endpoint — forwards breach payload to Risk Analysis service."""
    return await service.assess(payload, user_id=current_user.user_id)


@router.get(
    "/health",
    summary="Risk Analysis Service Health",
    description="Checks connectivity to the Risk Analysis Agent microservice.",
)
async def risk_analysis_health(
    current_user: CurrentUserDep,
    service: RiskAnalysisServiceDep,
) -> dict:
    """Returns health status of the Risk Analysis microservice."""
    return await service.health_check()
