"""Task Allocator Agent — Agent 4 of the ClimaSync AI pipeline.

Matches persisted tasks to nearby NGOs based on resource capabilities
and proximity. Updates the tasks table with assigned_ngo_id and creates
in-app notifications for each NGO.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.base_agent import BaseAgent
from app.modules.agents.schemas import (
    AllocationMap,
    DisasterContext,
    NgoSummary,
    PersistedTask,
    TaskAllocation,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal schema for LLM response
# ---------------------------------------------------------------------------


class _AllocationResponse(BaseModel):
    allocations: list[TaskAllocation] = Field(default_factory=list)
    unallocated_task_ids: list[uuid.UUID] = Field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a logistics coordinator for Pakistan's National Disaster Management Authority (NDMA).

Your job is to assign disaster response tasks to the most suitable NGOs based on:
1. Resource match — does the NGO have the resources required by the task type?
2. Capacity — does the NGO have sufficient quantity?
3. Proximity — prefer NGOs closest to the disaster location.

Resource mapping rules:
- task_type "ambulance"  → requires ambulances > 0
- task_type "boat"       → requires rescue_boats > 0
- task_type "medical"    → requires doctors > 0 OR paramedics > 0
- task_type "food"       → requires food_packets_capacity > 0
- task_type "evacuation" → requires trucks > 0 OR four_wheel_vehicles > 0
- task_type "shelter"    → requires shelter_capacity > 0

If no NGO can handle a task, add its task_id to unallocated_task_ids.
Each NGO can handle at most 2 tasks — distribute load fairly.

IMPORTANT: Return a single JSON object matching this schema exactly:
{
  "allocations": [
    {
      "task_id": "<uuid string>",
      "assigned_ngo_id": "<uuid string>",
      "ngo_name": "<string>",
      "match_reason": "<string>",
      "confidence": <float 0.0-1.0>
    }
  ],
  "unallocated_task_ids": ["<uuid string>", ...],
  "summary": "<string>"
}"""


class TaskAllocatorAgent(BaseAgent):
    """Assigns tasks to NGOs and writes allocations back to the DB."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__()
        self._db = db

    async def run(
        self,
        persisted_tasks: list[PersistedTask],
        context: DisasterContext,
    ) -> AllocationMap:
        """Allocate all persisted tasks to NGOs and return the AllocationMap."""
        if not persisted_tasks:
            return AllocationMap(summary="No tasks to allocate.")

        if not context.nearby_ngos:
            unallocated = [pt.task_id for pt in persisted_tasks]
            return AllocationMap(
                unallocated_task_ids=unallocated,
                summary="No verified NGOs available for allocation.",
            )

        logger.info(
            "[TaskAllocatorAgent] allocating %d tasks to %d NGOs for event_id=%s",
            len(persisted_tasks),
            len(context.nearby_ngos),
            context.event_id,
        )

        user_prompt = self._build_prompt(persisted_tasks, context.nearby_ngos, context)
        response = await self._call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=_AllocationResponse,
        )

        allocation_map = AllocationMap(
            allocations=response.allocations,
            unallocated_task_ids=response.unallocated_task_ids,
            summary=response.summary,
        )

        await self._apply_allocations(allocation_map, context.event_id)

        logger.info(
            "[TaskAllocatorAgent] allocated=%d unallocated=%d",
            len(allocation_map.allocations),
            len(allocation_map.unallocated_task_ids),
        )
        return allocation_map

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        persisted_tasks: list[PersistedTask],
        ngos: list[NgoSummary],
        context: DisasterContext,
    ) -> str:
        task_lines: list[str] = []
        for pt in persisted_tasks:
            d = pt.definition
            task_lines.append(
                f'- task_id="{pt.task_id}" | type={d.task_type} | qty={d.required_quantity}'
                f' | priority={d.priority} | location="{d.target_location_name}"'
                f' | label="{d.task_label}"'
            )

        ngo_lines: list[str] = []
        for ngo in ngos:
            ngo_lines.append(
                f'- ngo_id="{ngo.ngo_id}" | name="{ngo.org_name}" | city={ngo.base_city or "?"}'
                f' | ambulances={ngo.ambulances} | boats={ngo.rescue_boats}'
                f' | doctors={ngo.doctors} | paramedics={ngo.paramedics}'
                f' | trucks={ngo.trucks} | 4wd={ngo.four_wheel_vehicles}'
                f' | food_cap={ngo.food_packets_capacity} | shelter_cap={ngo.shelter_capacity}'
                f' | volunteers={ngo.volunteers_available}'
            )

        return f"""Assign the following disaster response tasks to the best-matched NGOs.

## Disaster Context
- Type: {context.event_type}
- Location: {context.location_name or "Unknown"}, {context.province or ""}, Pakistan
- Disaster coordinates: lat={context.latitude:.4f}, lon={context.longitude:.4f}

## Tasks to Allocate
{chr(10).join(task_lines)}

## Available NGOs
{chr(10).join(ngo_lines)}

Return the allocation JSON now."""

    async def _apply_allocations(
        self,
        allocation_map: AllocationMap,
        event_id: uuid.UUID,
    ) -> None:
        """Write allocations to DB and create notifications for each NGO."""
        now = datetime.now(timezone.utc)

        # Group allocations by NGO for batch notification creation
        ngo_task_map: dict[uuid.UUID, list[TaskAllocation]] = {}

        for alloc in allocation_map.allocations:
            # Update task row
            update_sql = text("""
                UPDATE tasks
                SET assigned_ngo_id = :ngo_id,
                    status = 'pending_acceptance',
                    assigned_at = :now,
                    updated_at = :now
                WHERE task_id = :task_id
            """)
            await self._db.execute(
                update_sql,
                {
                    "ngo_id": alloc.assigned_ngo_id,
                    "now": now,
                    "task_id": alloc.task_id,
                },
            )

            ngo_task_map.setdefault(alloc.assigned_ngo_id, []).append(alloc)

        # Create one notification per NGO
        for ngo_id, allocs in ngo_task_map.items():
            task_count = len(allocs)
            task_ids_str = ", ".join(str(a.task_id) for a in allocs)
            notif_sql = text("""
                INSERT INTO notifications (
                    notification_id, user_id, title, message,
                    notification_type, related_event_id,
                    is_read, created_at
                ) VALUES (
                    gen_random_uuid(), :user_id,
                    :title, :message,
                    'task_assigned', :event_id,
                    false, :now
                )
            """)
            await self._db.execute(
                notif_sql,
                {
                    "user_id": ngo_id,
                    "title": f"New Task Assignment — {task_count} task(s) assigned",
                    "message": (
                        f"You have been assigned {task_count} disaster response task(s). "
                        f"Task IDs: {task_ids_str}. "
                        f"Please review and accept them in the ClimaSync dashboard."
                    ),
                    "event_id": event_id,
                    "now": now,
                },
            )

        await self._db.commit()
        logger.debug(
            "[TaskAllocatorAgent] DB commit done — %d allocations, %d NGO notifications",
            len(allocation_map.allocations),
            len(ngo_task_map),
        )
