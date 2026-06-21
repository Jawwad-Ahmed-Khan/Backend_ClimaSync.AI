"""Tasks REST API Controller."""

import uuid

from fastapi import APIRouter, Path, Query, Request

from app.core.limiter import limiter
from app.modules.admin.dependencies import CurrentAdminDep
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.tasks.dependencies import TaskServiceDep
from app.modules.tasks.schemas import (
    TaskCreate,
    TaskResponse,
    TaskStatusHistoryResponse,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get(
    "",
    response_model=list[TaskResponse],
    summary="List Operational Tasks",
    description="If Admin, lists all. If NGO, strictly lists assigned target tasks.",
)
async def list_tasks(
    current_user: CurrentUserDep,
    service: TaskServiceDep,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve filtered assignments."""
    return await service.list_tasks(
        limit=limit, 
        offset=offset, 
        user_role=current_user.role, 
        user_id=current_user.user_id
    )


@router.get(
    "/event/{event_id}",
    response_model=list[TaskResponse],
    summary="List tasks for a specific disaster event",
)
async def list_tasks_by_event(
    current_user: CurrentUserDep,
    service: TaskServiceDep,
    event_id: uuid.UUID = Path(...),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve tasks belonging to a specific disaster event."""
    return await service.list_tasks_by_event(
        event_id=event_id,
        limit=limit,
        offset=offset,
        user_role=current_user.role,
        user_id=current_user.user_id
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get Detailed Task",
)
async def get_task(
    current_user: CurrentUserDep,
    service: TaskServiceDep,
    task_id: uuid.UUID = Path(...),
):
    """Fetch task explicitly applying NGO ownership blocks."""
    return await service.get_task(
        task_id=task_id, 
        user_role=current_user.role, 
        user_id=current_user.user_id
    )


@router.get(
    "/{task_id}/history",
    response_model=list[TaskStatusHistoryResponse],
    summary="Extract Audit Log for Task",
)
async def get_task_history(
    current_user: CurrentUserDep,
    service: TaskServiceDep,
    task_id: uuid.UUID = Path(...),
):
    """Audit logs."""
    task = await service.get_task(
        task_id=task_id, 
        user_role=current_user.role, 
        user_id=current_user.user_id
    )
    return task.history


@router.post(
    "",
    response_model=TaskResponse,
    summary="Create New Field Task",
    description="Requires Admin / Super Admin. Dispatches new unallocated task.",
)
@limiter.limit("5/minute")
async def create_task(
    request: Request,
    data: TaskCreate,
    current_admin: CurrentAdminDep,
    service: TaskServiceDep,
):
    """Generate operational requirement."""
    return await service.create_task(
        payload=data, 
        creator_id=current_admin.user_id, 
        creator_type="admin"
    )


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update Task (Permissions enforce structure)",
    description="NGOs can only update standard tracking limits. Admins can update core values.",
)
async def update_task(
    data: TaskUpdate,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
    task_id: uuid.UUID = Path(...)
):
    """Modify assignment and trigger Immutable History Patches automatically."""
    return await service.update_task(
        task_id=task_id,
        payload=data,
        modifier_id=current_user.user_id,
        user_role=current_user.role
    )
