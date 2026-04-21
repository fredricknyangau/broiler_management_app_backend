from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (get_current_non_viewer, get_current_user, get_db,
                          set_tenant_context)
from app.db.models.scheduled_task import ScheduledTask
from app.db.models.user import User
from app.schemas.scheduled_task import (ScheduledTaskCreate,
                                        ScheduledTaskResponse,
                                        ScheduledTaskUpdate)

router = APIRouter()


@router.get("/", response_model=List[ScheduledTaskResponse])
async def read_tasks(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """List user's scheduled tasks."""
    await set_tenant_context(db, current_user)
    stmt = select(ScheduledTask).filter(ScheduledTask.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "/", response_model=ScheduledTaskResponse, status_code=status.HTTP_201_CREATED
)
async def create_task(
    task_in: ScheduledTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Create a new scheduled task."""
    await set_tenant_context(db, current_user)

    if task_in.recurrence_interval is not None:
        from app.db.models.subscription import (PlanType, Subscription,
                                                SubscriptionStatus)

        sub_res = await db.execute(
            select(Subscription)
            .filter(
                Subscription.user_id == current_user.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
            .order_by(Subscription.created_at.desc())
        )
        sub = sub_res.scalars().first()
        current_plan = sub.plan_type if sub else PlanType.STARTER

        # Admins and Superusers bypass subscription locks
        if current_user.role == "ADMIN" or getattr(current_user, "is_superuser", False):
            current_plan = PlanType.ENTERPRISE

        if current_plan == PlanType.STARTER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Recurring schedules require a Professional Plan subscription.",
            )

    task_data = task_in.model_dump(exclude={"recurrence_interval"})
    task = ScheduledTask(**task_data, user_id=current_user.id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.put("/{task_id}", response_model=ScheduledTaskResponse)
async def update_task(
    task_id: UUID,
    task_in: ScheduledTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Update a task."""
    await set_tenant_context(db, current_user)
    stmt = select(ScheduledTask).filter(
        ScheduledTask.id == task_id, ScheduledTask.user_id == current_user.id
    )
    result = await db.execute(stmt)
    task = result.scalars().first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """
    Delete a scheduled task.
    """
    await set_tenant_context(db, current_user)
    stmt = select(ScheduledTask).filter(
        ScheduledTask.id == task_id, ScheduledTask.user_id == current_user.id
    )
    result = await db.execute(stmt)
    task = result.scalars().first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()
    return None
