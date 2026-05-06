"""Agent pipeline orchestrator — chains all 4 agents sequentially.

Exposes a single `run_agent_pipeline(event_id, db)` coroutine that
drives the full Data Extraction → Risk Analysis → Task Definer →
Task Allocator workflow and returns an AgentPipelineResult.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.data_extraction_agent import DataExtractionAgent
from app.modules.agents.risk_analysis_agent import RiskAnalysisAgent
from app.modules.agents.schemas import AgentPipelineResult
from app.modules.agents.task_allocator_agent import TaskAllocatorAgent
from app.modules.agents.task_definer_agent import TaskDefinerAgent

logger = logging.getLogger(__name__)


async def run_agent_pipeline(
    event_id: uuid.UUID,
    db: AsyncSession,
) -> AgentPipelineResult:
    """Run the full 4-agent disaster management pipeline.

    Steps:
        1. DataExtractionAgent  — fetch & enrich event data (no LLM)
        2. RiskAnalysisAgent    — classify risk + update DB
        3. TaskDefinerAgent     — generate & persist tasks
        4. TaskAllocatorAgent   — match tasks to NGOs + notify
    """
    logger.info("[Orchestrator] pipeline START — event_id=%s", event_id)

    # --- Agent 1: Data Extraction ----------------------------------------
    extraction_agent = DataExtractionAgent(db)
    context = await extraction_agent.run(event_id)
    logger.info("[Orchestrator] Agent 1 complete — context built")

    # --- Agent 2: Risk Analysis -------------------------------------------
    risk_agent = RiskAnalysisAgent(db)
    risk_report = await risk_agent.run(context)
    logger.info("[Orchestrator] Agent 2 complete — risk_level=%s", risk_report.risk_level)

    # --- Agent 3: Task Definer --------------------------------------------
    task_definer = TaskDefinerAgent(db)
    persisted_tasks = await task_definer.run(context, risk_report)
    logger.info("[Orchestrator] Agent 3 complete — %d tasks created", len(persisted_tasks))

    # --- Agent 4: Task Allocator ------------------------------------------
    allocator = TaskAllocatorAgent(db)
    allocation_map = await allocator.run(persisted_tasks, context)
    logger.info(
        "[Orchestrator] Agent 4 complete — allocated=%d unallocated=%d",
        len(allocation_map.allocations),
        len(allocation_map.unallocated_task_ids),
    )

    result = AgentPipelineResult(
        event_id=event_id,
        risk_report=risk_report,
        tasks_created=len(persisted_tasks),
        tasks_allocated=len(allocation_map.allocations),
        unallocated_task_ids=allocation_map.unallocated_task_ids,
        allocation_summary=allocation_map.summary,
    )

    logger.info(
        "[Orchestrator] pipeline COMPLETE — tasks_created=%d tasks_allocated=%d",
        result.tasks_created,
        result.tasks_allocated,
    )
    return result
