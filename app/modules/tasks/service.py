"""Tasks module business logic linking roles and validation."""

import uuid

from fastapi import HTTPException

from app.modules.tasks.models import Task
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.schemas import TaskCreate, TaskUpdate


class TaskService:
    """Core logic layer validating NGO relationships against task assignments."""

    def __init__(self, repo: TaskRepository) -> None:
        self.repo = repo

    async def list_tasks(self, limit: int = 100, offset: int = 0, user_role: str = "admin", user_id: uuid.UUID | None = None) -> list[Task]:
        """Admins see all; NGOs see only assigned tasks."""
        target_ngo_id = user_id if user_role == "ngo_user" else None
        return await self.repo.get_tasks(limit=limit, offset=offset, ngo_id=target_ngo_id)

    async def list_tasks_by_event(self, event_id: uuid.UUID, limit: int = 100, offset: int = 0, user_role: str = "admin", user_id: uuid.UUID | None = None) -> list[Task]:
        """Fetch tasks for an event, applying role-based NGO filtering."""
        target_ngo_id = user_id if user_role == "ngo_user" else None
        return await self.repo.get_tasks_by_event(
            event_id=event_id, 
            limit=limit, 
            offset=offset, 
            ngo_id=target_ngo_id
        )

    async def get_task(self, task_id: uuid.UUID, user_role: str = "admin", user_id: uuid.UUID | None = None) -> Task:
        """Fetch task securely ensuring ownership for NGOs."""
        task = await self.repo.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Verify ownership if ngo
        if user_role == "ngo_user" and task.assigned_ngo_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden. Task not assigned to your NGO.")
            
        return task

    async def create_task(self, payload: TaskCreate, creator_id: uuid.UUID, creator_type: str = "admin") -> Task:
        """Create new ops task dictating standard logic."""
        data = payload.model_dump(exclude_unset=True)
        data["created_by_type"] = creator_type
        
        return await self.repo.create_task(data=data, creator_id=creator_id)

    async def update_task(
        self, 
        task_id: uuid.UUID, 
        payload: TaskUpdate, 
        modifier_id: uuid.UUID, 
        user_role: str = "admin"
    ) -> Task:
        """Patches task properties enforcing domain restrictions."""
        # This will independently throw a 403 if an NGO attempts fetching another NGO's task!
        task = await self.get_task(task_id, user_role, modifier_id)
        
        updates = payload.model_dump(exclude_unset=True)
        
        # Admin restricts:
        if user_role == "ngo_user" and "assigned_ngo_id" in updates:
            raise HTTPException(status_code=403, detail="Forbidden. NGOs cannot reassign tasks privately.")
            
        # Extract the change reason out of the updates dict cleanly to stop ORM failing
        change_reason = updates.pop("change_reason", None)
        
        return await self.repo.update_task(
            task=task,
            updates=updates,
            modifier_id=modifier_id,
            change_reason=change_reason
        )
