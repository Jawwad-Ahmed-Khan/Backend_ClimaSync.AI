"""Tasks module dependency components."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.service import TaskService


def get_task_repository(session: Annotated[AsyncSession, Depends(get_db)]) -> TaskRepository:
    return TaskRepository(session)


def get_task_service(
    repo: Annotated[TaskRepository, Depends(get_task_repository)],
) -> TaskService:
    return TaskService(repo=repo)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
