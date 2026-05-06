"""FastAPI router for the AI agent pipeline.

Mounts at /api/v1/agents — provides endpoints to trigger the full
4-agent pipeline or run individual agents for debugging.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.agents.data_extraction_agent import DataExtractionAgent
from app.modules.agents.orchestrator import run_agent_pipeline
from app.modules.agents.risk_analysis_agent import RiskAnalysisAgent
from app.modules.agents.schemas import (
    AgentPipelineResult,
    DisasterContext,
    RiskReport,
)
from app.modules.agents.task_definer_agent import TaskDefinerAgent

router = APIRouter(prefix="/agents", tags=["AI Agents"])


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


@router.post(
    "/analyze/{event_id}",
    response_model=AgentPipelineResult,
    summary="Run full 4-agent pipeline for a disaster event",
    status_code=status.HTTP_200_OK,
)
async def analyze_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AgentPipelineResult:
    """Trigger the complete agent pipeline:
    1. Data Extraction → 2. Risk Analysis → 3. Task Definer → 4. Task Allocator.

    Returns a summary of the pipeline run including the risk report,
    number of tasks created, and allocation results.
    """
    try:
        return await run_agent_pipeline(event_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI pipeline error: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Individual agent endpoints (for debugging / partial runs)
# ---------------------------------------------------------------------------


@router.post(
    "/extract/{event_id}",
    response_model=DisasterContext,
    summary="[Debug] Run only Agent 1 — Data Extraction",
)
async def extract_context(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DisasterContext:
    """Fetch and return the enriched DisasterContext without running any LLM."""
    try:
        agent = DataExtractionAgent(db)
        return await agent.run(event_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/risk/{event_id}",
    response_model=RiskReport,
    summary="[Debug] Run Agents 1+2 — Data Extraction + Risk Analysis",
)
async def analyze_risk(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RiskReport:
    """Extract context then run the Risk Analysis Agent. Updates DB risk_level."""
    try:
        context = await DataExtractionAgent(db).run(event_id)
        return await RiskAnalysisAgent(db).run(context)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post(
    "/tasks/{event_id}",
    summary="[Debug] Run Agents 1+2+3 — up through Task Definer",
)
async def define_tasks(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Extract context, run risk analysis, then generate and persist tasks."""
    try:
        context = await DataExtractionAgent(db).run(event_id)
        risk_report = await RiskAnalysisAgent(db).run(context)
        persisted = await TaskDefinerAgent(db).run(context, risk_report)
        return {
            "event_id": str(event_id),
            "risk_level": risk_report.risk_level,
            "tasks_created": len(persisted),
            "task_ids": [str(pt.task_id) for pt in persisted],
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
