"""Risk Analysis service — calls the Risk Analysis microservice via HTTP."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.modules.risk_analysis.repository import RiskAnalysisRepository
from app.modules.risk_analysis.schemas import RiskAnalysisRequest, RiskAnalysisResponse

logger = logging.getLogger(__name__)

# Timeout for risk analysis — the agent may take up to 5 minutes
_RISK_ANALYSIS_TIMEOUT = 300.0


class RiskAnalysisService:
    """Proxy service that forwards assessment requests to the Risk Analysis Agent."""

    def __init__(self, repo: RiskAnalysisRepository) -> None:
        self.repo = repo

    async def assess(self, request: RiskAnalysisRequest, user_id: uuid.UUID | None = None) -> RiskAnalysisResponse:
        """
        Forwards the breach payload to the Risk Analysis Agent service.
        Saves the resulting high-fidelity report to the database.
        """
        url = f"{settings.RISK_ANALYSIS_URL.rstrip('/')}/api/v1/assess"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": settings.RISK_ANALYSIS_API_KEY,
        }
        payload = request.model_dump()
        requested_at = datetime.now(timezone.utc)

        logger.info(
            "Forwarding risk assessment to agent. breach_id=%s disaster=%s location=%s",
            request.breach_id,
            request.disaster_kind,
            request.location_name,
        )

        try:
            async with httpx.AsyncClient(timeout=_RISK_ANALYSIS_TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                logger.info(
                    "Risk assessment completed. breach_id=%s risk_level=%s",
                    request.breach_id,
                    data.get("risk_level"),
                )
                
                # --- PERSIST TO DATABASE ---
                try:
                    # Map confidence string to integer score
                    conf_map = {"HIGH": 90, "MEDIUM": 70, "LOW": 40}
                    conf_score = conf_map.get(data.get("data_confidence", "LOW").upper(), 50)
                    
                    # Extract population
                    exposure = data.get("exposure", {})
                    pop_breakdown = exposure.get("population_breakdown", {})
                    est_affected = pop_breakdown.get("estimated_directly_affected", 0) or 0
                    
                    save_data = {
                        "alert_id": uuid.UUID(request.breach_id),
                        "risk_level": data.get("risk_level", "UNKNOWN"),
                        "risk_score": int(data.get("composite_risk_score") or 0),
                        "confidence_score": conf_score,
                        "disaster_type": data.get("disaster_kind", "unknown"),
                        "analysis_summary": data.get("risk_level_justification", "No summary provided"),
                        "detailed_analysis": data,
                        "recommended_actions": data.get("critical_actions_needed", []),
                        "estimated_population_affected": est_affected,
                        "affected_area_km2": 0.0,  # Fulfilling the NOT NULL database constraint
                        "requested_by": user_id,
                        "requested_at": requested_at,
                        "completed_at": datetime.now(timezone.utc)
                    }
                    await self.repo.create(save_data)
                    logger.info("Risk assessment persisted to database.")
                except Exception as save_exc:
                    logger.error("Failed to save risk assessment to DB: %s", save_exc)
                    # We don't raise here, we still want to return the report to the user
                
                return RiskAnalysisResponse(**data)

            elif response.status_code == 401:
                logger.error("Risk Analysis service rejected API key.")
                raise HTTPException(
                    status_code=502,
                    detail="Risk Analysis service authentication failed. Check RISK_ANALYSIS_API_KEY.",
                )
            elif response.status_code == 422:
                logger.error("Risk Analysis service rejected payload: %s", response.text)
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid payload for risk analysis: {response.json()}",
                )
            else:
                logger.error(
                    "Risk Analysis service returned unexpected status %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                raise HTTPException(
                    status_code=502,
                    detail=f"Risk Analysis service error: {response.status_code}",
                )

        except httpx.ConnectError:
            logger.error("Cannot connect to Risk Analysis service at %s", settings.RISK_ANALYSIS_URL)
            raise HTTPException(
                status_code=503,
                detail="Risk Analysis service is unavailable. Ensure it is running on port 8001.",
            )
        except httpx.TimeoutException:
            logger.error("Risk Analysis service timed out after %.0fs", _RISK_ANALYSIS_TIMEOUT)
            raise HTTPException(
                status_code=504,
                detail="Risk Analysis service timed out. The AI agent is taking longer than expected.",
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error calling Risk Analysis service: %s", exc)
            raise HTTPException(
                status_code=500,
                detail=f"Internal error during risk analysis: {exc}",
            )

    async def health_check(self) -> dict:
        """Check if the Risk Analysis service is up."""
        url = f"{settings.RISK_ANALYSIS_URL}/health"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
            return response.json()
        except Exception as exc:
            return {"status": "unreachable", "error": str(exc)}
