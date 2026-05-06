"""Task Definer Agent — Agent 3 of the ClimaSync AI pipeline.

Takes a DisasterContext + RiskReport and calls OpenAI to generate a
prioritised list of operational tasks. Each task is then persisted to
the `tasks` table with status='pending_approval' and created_by_type='ai'.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.base_agent import BaseAgent
from app.modules.agents.schemas import DisasterContext, PersistedTask, RiskReport, TaskDefinition

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal schema for LLM response (wraps the list in a top-level object
# so JSON mode always returns a single JSON object, not an array)
# ---------------------------------------------------------------------------


class _TaskListResponse(BaseModel):
    tasks: list[TaskDefinition] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an emergency response coordinator for Pakistan's National Disaster Management Authority (NDMA).

Given a disaster event, its risk report, and the available response window, your job is to define a concrete list of operational tasks that NGOs must execute to mitigate harm and provide aid.

Rules:
- Generate between 3 and 8 tasks — no more, no less.
- Each task must have a clear, actionable label and description.
- Use ONLY these task_type values: ambulance | boat | medical | food | evacuation | shelter
- Set priority based on risk_level: critical events require ≥2 "critical" priority tasks.
- required_quantity must be a realistic integer (do not invent huge numbers).
- target_location_name must be a specific location in Pakistan (city/village/district level).
- Include a brief reasoning for each task explaining why it is needed.

IMPORTANT: Return a single JSON object with a "tasks" key containing an array of task objects.
Each task object must match this exact schema:
{
  "task_label": "<string>",
  "description": "<string>",
  "task_type": "ambulance" | "boat" | "medical" | "food" | "evacuation" | "shelter",
  "required_quantity": <integer ≥ 1>,
  "priority": "low" | "medium" | "high" | "critical",
  "estimated_duration_hours": <integer ≥ 1>,
  "target_location_name": "<string>",
  "reasoning": "<string>"
}

Example response:
{"tasks": [{"task_label": "Deploy flood rescue boats", "description": "...", "task_type": "boat", "required_quantity": 5, "priority": "critical", "estimated_duration_hours": 48, "target_location_name": "Sukkur, Sindh", "reasoning": "..."}]}"""


class TaskDefinerAgent(BaseAgent):
    """Generates mitigation task definitions using OpenAI and persists them to DB."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__()
        self._db = db

    async def run(
        self,
        context: DisasterContext,
        risk_report: RiskReport,
    ) -> list[PersistedTask]:
        """Generate tasks, persist them, and return PersistedTask list."""
        logger.info(
            "[TaskDefinerAgent] defining tasks for event_id=%s risk_level=%s",
            context.event_id,
            risk_report.risk_level,
        )

        user_prompt = self._build_prompt(context, risk_report)
        response = await self._call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=_TaskListResponse,
        )

        tasks = response.tasks
        logger.info("[TaskDefinerAgent] %d tasks generated", len(tasks))

        persisted = await self._persist_tasks(context.event_id, tasks)
        return persisted

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, context: DisasterContext, report: RiskReport) -> str:
        return f"""Define the operational tasks required for the following disaster event.

## Disaster Context
- Event ID: {context.event_id}
- Type: {context.event_type}
- Title: {context.title}
- Location: {context.location_name or "Unknown"}, {context.district or ""}, {context.province or ""}, Pakistan
- Coordinates: lat={context.latitude:.4f}, lon={context.longitude:.4f}
- Affected population estimate: {report.affected_population_estimate:,}

## Risk Report
- Risk Level: {report.risk_level.upper()}
- Severity Score: {report.severity_score}/10
- Key Risk Factors: {", ".join(report.key_risk_factors)}
- Response Window: {report.recommended_response_window_hours} hours
- Estimated Damage: PKR {report.estimated_damage_pkr:,} (approx.) if {report.estimated_damage_pkr} else "unknown"
- Analyst Reasoning: {report.reasoning}

## Available NGO Resources (summary)
{self._summarise_ngo_resources(context)}

Generate the task list JSON now."""

    @staticmethod
    def _summarise_ngo_resources(context: DisasterContext) -> str:
        if not context.nearby_ngos:
            return "No verified NGOs available nearby."
        lines: list[str] = []
        for ngo in context.nearby_ngos[:5]:  # cap at 5 for prompt size
            lines.append(
                f"- {ngo.org_name} ({ngo.base_city or 'unknown city'}): "
                f"ambulances={ngo.ambulances}, boats={ngo.rescue_boats}, "
                f"doctors={ngo.doctors}, food_capacity={ngo.food_packets_capacity}, "
                f"shelter_capacity={ngo.shelter_capacity}"
            )
        return "\n".join(lines)

    async def _persist_tasks(
        self,
        event_id: uuid.UUID,
        tasks: list[TaskDefinition],
    ) -> list[PersistedTask]:
        """Insert tasks into the DB and return them with their generated task_ids."""
        persisted: list[PersistedTask] = []
        now = datetime.now(timezone.utc)

        for task_def in tasks:
            # Raw INSERT using text() to avoid ORM complexity with PostGIS geometry
            insert_sql = text("""
                INSERT INTO tasks (
                    task_id, event_id, task_label, description,
                    task_type, required_quantity, priority,
                    target_location_name, estimated_duration_hours,
                    status, created_by_type,
                    created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), :event_id, :task_label, :description,
                    :task_type, :required_quantity, :priority,
                    :target_location_name, :estimated_duration_hours,
                    'pending_approval', 'ai',
                    :now, :now
                )
                RETURNING task_id
            """)

            result = await self._db.execute(
                insert_sql,
                {
                    "event_id": event_id,
                    "task_label": task_def.task_label,
                    "description": task_def.description,
                    "task_type": task_def.task_type,
                    "required_quantity": task_def.required_quantity,
                    "priority": task_def.priority,
                    "target_location_name": task_def.target_location_name,
                    "estimated_duration_hours": task_def.estimated_duration_hours,
                    "now": now,
                },
            )
            row = result.fetchone()
            if row:
                persisted.append(PersistedTask(task_id=row.task_id, definition=task_def))

        await self._db.commit()
        logger.info("[TaskDefinerAgent] persisted %d tasks for event_id=%s", len(persisted), event_id)
        return persisted
