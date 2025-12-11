from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from typing import List, Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.api.deps import get_db, get_current_admin_user
from app.db.models.user import User, UserRole
from app.db.models.finance import Sale, Expenditure
from app.db.models.flock import Flock
from app.schemas.user import UserResponse, UserUpdate
from app.services.audit_service import log_action
from app.db.models.subscription import Subscription, SubscriptionStatus, PlanType
from app.db.models.subscription import Subscription, SubscriptionStatus, PlanType
from app.db.models.role import Role
from app.db.models.config import SystemConfig
from app.schemas.billing import SubscriptionResponse
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse
from app.schemas.config import SystemConfigCreate, SystemConfigUpdate, SystemConfigResponse

router = APIRouter()

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List all users (Admin only)
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return users

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_status(
    user_id: str,
    user_update: UserUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user's status or role (Admin only)
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Prevent removing own admin status/role accidentally
    if str(user.id) == str(current_admin.id):
         if update_data.get("is_superuser") is False:
             pass 
         if update_data.get("role") and update_data.get("role") != "ADMIN":
             pass # Warn or block self-demotion? Allowing for now.

    for field, value in update_data.items():
        setattr(user, field, value)

    # db.add(user)
    await db.commit()
    await db.refresh(user)

    await log_action(
        db=db,
        action="UPDATE_USER",
        user_id=current_admin.id,
        resource_type="User",
        resource_id=str(user.id),
        details=update_data
    )

    return user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user (Admin only)
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if str(user.id) == str(current_admin.id):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    await db.delete(user)
    await db.commit()

    await log_action(
        db=db,
        action="DELETE_USER",
        user_id=current_admin.id,
        resource_type="User",
        resource_id=str(user_id)
    )

    return {"message": "User deleted successfully"}

class AdminStats(BaseModel):
    total_users: int
    active_users: int
    active_subscriptions: int
    total_revenue_est: float
    total_flocks: int
    active_flocks: int

class AdminTransaction(BaseModel):
    id: UUID
    user_email: str
    plan: str
    amount: str
    status: str
    date: datetime
    mpesa_ref: Optional[str]

class PlanUpdate(BaseModel):
    plan_type: PlanType

@router.get("/stats", response_model=AdminStats)
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Get system-wide statistics including billing.
    """
    total_users = await db.execute(select(func.count(User.id)))
    active_users = await db.execute(select(func.count(User.id)).filter(User.is_active == True))
    
    total_flocks = await db.execute(select(func.count(Flock.id)))
    active_flocks = await db.execute(select(func.count(Flock.id)).filter(Flock.status == 'active'))
    
    active_subs_result = await db.execute(select(Subscription).filter(Subscription.status == SubscriptionStatus.ACTIVE))
    active_subs = active_subs_result.scalars().all()
    active_subs_count = len(active_subs)
    
    revenue = 0.0
    for sub in active_subs:
        try:
            if sub.amount:
                revenue += float(sub.amount)
        except:
            pass
            
    return AdminStats(
        total_users=total_users.scalar() or 0,
        active_users=active_users.scalar() or 0,
        active_subscriptions=active_subs_count,
        total_revenue_est=revenue,
        total_flocks=total_flocks.scalar() or 0,
        active_flocks=active_flocks.scalar() or 0
    )

@router.get("/transactions", response_model=List[AdminTransaction])
async def get_transactions(
    limit: int = 50,
    skip: int = 0,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    List all subscriptions (transactions).
    """
    result = await db.execute(
        select(Subscription)
        .options(joinedload(Subscription.user)) # Eager load user
        .order_by(Subscription.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    subs = result.scalars().all()
    
    results = []
    for sub in subs:
        results.append(AdminTransaction(
            id=sub.id,
            user_email=sub.user.email if sub.user else "Unknown",
            plan=sub.plan_type,
            amount=sub.amount or "0",
            status=sub.status,
            date=sub.created_at,
            mpesa_ref=sub.mpesa_reference
        ))
    return results

@router.post("/users/{user_id}/plan")
async def assign_user_plan(
    user_id: UUID,
    payload: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Manually assign a plan to a user. Cancels any existing active subscription.
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Cancel existing
    existing_result = await db.execute(select(Subscription).filter(
        Subscription.user_id == user_id, 
        Subscription.status == SubscriptionStatus.ACTIVE
    ))
    existing = existing_result.scalars().all()
    for sub in existing:
        sub.status = SubscriptionStatus.CANCELLED
        sub.end_date = datetime.now()
    
    # Create new free/manual subscription
    new_sub = Subscription(
        user_id=user_id,
        plan_type=payload.plan_type,
        status=SubscriptionStatus.ACTIVE,
        amount="0", # Manual assignment usually implies free/comped 
        start_date=datetime.now(),
        mpesa_reference=f"MANUAL-{current_admin.id}-{int(datetime.now().timestamp())}"
    )
    db.add(new_sub)
    await db.commit()
    
    return {"status": "success", "message": f"Assigned {payload.plan_type} to user"}

@router.post("/subscriptions/{sub_id}/cancel")
async def cancel_subscription(
    sub_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Force cancel a subscription.
    """
    result = await db.execute(select(Subscription).filter(Subscription.id == sub_id))
    sub = result.scalars().first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    sub.status = SubscriptionStatus.CANCELLED
    sub.end_date = datetime.now()
    await db.commit()
    
    return {"status": "success", "message": "Subscription cancelled"}


# --- Role Management ---

@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """List all available roles."""
    result = await db.execute(select(Role).offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create a new custom role."""
    # Check if exists
    existing = await db.execute(select(Role).filter(Role.name == role_in.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Role with this name already exists")
    
    role = Role(**role_in.model_dump())
    db.add(role)
    await db.commit()
    await db.refresh(role)
    
    await log_action(db, "CREATE_ROLE", current_admin.id, "Role", str(role.id), role_in.model_dump())
    return role

@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update a role's permissions or description."""
    result = await db.execute(select(Role).filter(Role.id == role_id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    update_data = role_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)
        
    await db.commit()
    await db.refresh(role)
    
    await log_action(db, "UPDATE_ROLE", current_admin.id, "Role", str(role.id), update_data)
    return role

@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete a custom role."""
    result = await db.execute(select(Role).filter(Role.id == role_id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if users are assigned to this role (basic check, can be improved)
    # Since User.role is a string, we check that string
    users_with_role = await db.execute(select(User).filter(User.role == role.name))
    if users_with_role.scalars().first():
        raise HTTPException(status_code=400, detail="Cannot delete role that is assigned to users")

    await db.delete(role)
    await db.commit()
    
    await log_action(db, "DELETE_ROLE", current_admin.id, "Role", str(role.id))
    return {"status": "success", "message": "Role deleted"}


# --- System Configuration ---

@router.get("/config", response_model=List[SystemConfigResponse])
async def get_system_config(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all system configurations (Admin only)."""
    result = await db.execute(select(SystemConfig))
    return result.scalars().all()

@router.post("/config", response_model=SystemConfigResponse)
async def create_or_update_config(
    config_in: SystemConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create or update a configuration key."""
    result = await db.execute(select(SystemConfig).filter(SystemConfig.key == config_in.key))
    existing = result.scalars().first()
    
    if existing:
        # Update
        for field, value in config_in.model_dump(exclude={"key"}).items(): # key is immutable-ish for update content
            setattr(existing, field, value)
        db_obj = existing
        action = "UPDATE_CONFIG"
    else:
        # Create
        db_obj = SystemConfig(**config_in.model_dump())
        db.add(db_obj)
        action = "CREATE_CONFIG"
        
    await db.commit()
    await db.refresh(db_obj)
    
    await log_action(db, action, current_admin.id, "SystemConfig", str(db_obj.id), {"key": config_in.key})
    return db_obj
