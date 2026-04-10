"""Tasks module repository logic."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.tasks.models import Task, TaskStatusHistory


class TaskRepository:
    """Repository applying task fetching and immutable status transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_tasks(self, limit: int = 100, offset: int = 0, ngo_id: uuid.UUID | None = None) -> list[Task]:
        """Fetch tasks, optionally restricting to an NGO."""
        stmt = select(Task)
        if ngo_id:
            stmt = stmt.where(Task.assigned_ngo_id == ngo_id)
        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_task_by_id(self, task_id: uuid.UUID) -> Task | None:
        """Fetch singular task."""
        stmt = select(Task).options(selectinload(Task.history)).where(Task.task_id == task_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_task(self, data: dict[str, Any], creator_id: uuid.UUID | None = None) -> Task:
        """Create a new task and establish its base history."""
        task = Task(**data)
        self.session.add(task)
        await self.session.flush()

        # Log genesis history
        history_entry = TaskStatusHistory(
            task_id=task.task_id,
            old_status=None,
            new_status=task.status,
            changed_by=creator_id,
            change_reason="Task initialized"
        )
        self.session.add(history_entry)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def update_task(
        self, 
        task: Task, 
        updates: dict[str, Any], 
        modifier_id: uuid.UUID | None = None, 
        change_reason: str | None = None
    ) -> Task:
        """Update fields. If status changes, inject a history log."""
        old_status = task.status
        new_status = updates.get("status")

        for key, value in updates.items():
            setattr(task, key, value)
            
        self.session.add(task)

        # Trigger history recording ONLY if status fundamentally changes
        if new_status and new_status != old_status:
            history_entry = TaskStatusHistory(
                task_id=task.task_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=modifier_id,
                change_reason=change_reason or "Status updated via API patch"
            )
            self.session.add(history_entry)

        await self.session.flush()
        await self.session.refresh(task)
        return task
