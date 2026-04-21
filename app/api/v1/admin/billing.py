"""admin/billing.py — Subscription and plan management endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_admin_user, get_db
from app.db.models.subscription import (PlanType, Subscription,
                                        SubscriptionPlan, SubscriptionStatus)
from app.db.models.user import User
from app.schemas.billing import (PlanCreate, PlanResponse, PlanUpdate,
                                 SubscriptionOverride, SubscriptionResponse)
from app.services.audit_service import log_action

router = APIRouter()

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total_count: int
    total_pages: int
    current_page: int


class AdminTransaction(BaseModel):
    id: UUID
    user_email: str
    plan: str
    amount: str
    status: str
    date: datetime
    mpesa_ref: Optional[str]


class AdminSubscription(BaseModel):
    id: UUID
    user_email: str
    plan_type: str
    status: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    amount: Optional[str]
    mpesa_reference: Optional[str]


@router.put("/users/{user_id}/subscription", response_model=SubscriptionResponse)
async def update_user_subscription(
    user_id: str,
    override: SubscriptionOverride,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Override or create a user's active subscription (Admin only)."""
    user_res = await db.execute(select(User).filter(User.id == user_id))
    user = user_res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .order_by(Subscription.created_at.desc())
    )
    sub = result.scalars().first()

    now = datetime.now(timezone.utc)
    details = override.model_dump(exclude_unset=True)

    if sub:
        sub.plan_type = override.plan_type
        if override.end_date:
            sub.end_date = override.end_date
        if override.amount:
            sub.amount = override.amount
        if override.status:
            sub.status = override.status
        sub.updated_at = now
    else:
        sub = Subscription(
            user_id=user_id,
            plan_type=override.plan_type,
            status=override.status or SubscriptionStatus.ACTIVE,
            start_date=now,
            end_date=override.end_date or (now + timedelta(days=365)),
            amount=override.amount or "0",
            mpesa_reference=f"MANUAL-{current_admin.id}-{int(now.timestamp())}",
        )
        db.add(sub)

    await db.commit()
    await db.refresh(sub)

    await log_action(
        db=db,
        action="MANUAL_SUBSCRIPTION_OVERRIDE",
        user_id=current_admin.id,
        resource_type="Subscription",
        resource_id=str(sub.id),
        details=details,
    )
    return sub


@router.post("/users/{user_id}/plan")
async def assign_user_plan(
    user_id: UUID,
    payload: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Manually assign a plan to a user. Cancels any existing active subscription."""
    result = await db.execute(select(User).filter(User.id == user_id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="User not found")

    existing_result = await db.execute(
        select(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    for sub in existing_result.scalars().all():
        sub.status = SubscriptionStatus.CANCELLED
        sub.end_date = datetime.now(timezone.utc)

    new_sub = Subscription(
        user_id=user_id,
        plan_type=payload.plan_type,
        status=SubscriptionStatus.ACTIVE,
        amount="0",
        start_date=datetime.now(timezone.utc),
        mpesa_reference=f"MANUAL-{current_admin.id}-{int(datetime.now(timezone.utc).timestamp())}",
    )
    db.add(new_sub)
    await db.commit()
    return {"status": "success", "message": f"Assigned {payload.plan_type} to user"}


@router.post("/subscriptions/{sub_id}/cancel")
async def cancel_subscription(
    sub_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Force cancel a subscription."""
    result = await db.execute(select(Subscription).filter(Subscription.id == sub_id))
    sub = result.scalars().first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.status = SubscriptionStatus.CANCELLED
    sub.end_date = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "success", "message": "Subscription cancelled"}


@router.get("/transactions", response_model=PaginatedResponse[AdminTransaction])
async def get_transactions(
    limit: int = 50,
    skip: int = 0,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """List all subscriptions (transactions) securely."""
    query = select(Subscription).options(joinedload(Subscription.user))
    if search:
        query = query.join(User).filter(
            or_(
                User.email.ilike(f"%{search}%"),
                Subscription.plan_type.ilike(f"%{search}%"),
            )
        )

    total_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total_res.scalar() or 0

    result = await db.execute(
        query.order_by(Subscription.created_at.desc()).offset(skip).limit(limit)
    )
    subs = result.scalars().all()

    return PaginatedResponse(
        items=[
            AdminTransaction(
                id=s.id,
                user_email=s.user.email if s.user else "Unknown",
                plan=s.plan_type,
                amount=s.amount or "0",
                status=s.status,
                date=s.created_at,
                mpesa_ref=s.mpesa_reference,
            )
            for s in subs
        ],
        total_count=total_count,
        total_pages=(total_count + limit - 1) // limit if limit > 0 else 1,
        current_page=(skip // limit) + 1 if limit > 0 else 1,
    )


@router.get("/subscriptions/all", response_model=PaginatedResponse[AdminSubscription])
async def get_all_user_subscriptions(
    limit: int = 50,
    skip: int = 0,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """List all user subscriptions with details (Admin only)."""
    query = select(Subscription).options(joinedload(Subscription.user))
    if search:
        query = query.join(User).filter(
            or_(
                User.email.ilike(f"%{search}%"),
                Subscription.plan_type.ilike(f"%{search}%"),
                Subscription.status.ilike(f"%{search}%"),
                Subscription.mpesa_reference.ilike(f"%{search}%"),
            )
        )

    total_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total_res.scalar() or 0

    result = await db.execute(
        query.order_by(Subscription.created_at.desc()).offset(skip).limit(limit)
    )
    subs = result.scalars().all()

    return PaginatedResponse(
        items=[
            AdminSubscription(
                id=s.id,
                user_email=s.user.email if s.user else "Deleted User",
                plan_type=s.plan_type,
                status=s.status,
                start_date=s.start_date,
                end_date=s.end_date,
                amount=s.amount,
                mpesa_reference=s.mpesa_reference,
            )
            for s in subs
        ],
        total_count=total_count,
        total_pages=(total_count + limit - 1) // limit if limit > 0 else 1,
        current_page=(skip // limit) + 1 if limit > 0 else 1,
    )


# ── Plan Management ─────────────────────────────────────────────────────────


@router.get("/plans", response_model=List[PlanResponse])
async def get_admin_plans(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """List all subscription plan configurations."""
    result = await db.execute(
        select(SubscriptionPlan).order_by(SubscriptionPlan.monthly_price.desc())
    )
    return result.scalars().all()


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def update_subscription_plan(
    plan_id: UUID,
    plan_in: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Update a specific subscription plan's pricing or features."""
    result = await db.execute(
        select(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    update_data = plan_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    await db.commit()
    await db.refresh(plan)

    await log_action(
        db,
        "UPDATE_PLAN",
        current_admin.id,
        "SubscriptionPlan",
        str(plan.id),
        update_data,
    )
    return plan


@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription_plan(
    plan_in: PlanCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Create a new subscription plan."""
    existing = await db.execute(
        select(SubscriptionPlan).filter(SubscriptionPlan.plan_type == plan_in.plan_type)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan type {plan_in.plan_type} already exists",
        )

    plan = SubscriptionPlan(**plan_in.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    await log_action(
        db,
        "CREATE_PLAN",
        current_admin.id,
        "SubscriptionPlan",
        str(plan.id),
        plan_in.model_dump(),
    )
    return plan


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Delete a subscription plan."""
    result = await db.execute(
        select(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    await db.delete(plan)
    await db.commit()
    await log_action(
        db,
        "DELETE_PLAN",
        current_admin.id,
        "SubscriptionPlan",
        str(plan_id),
        {"plan_type": plan.plan_type},
    )
