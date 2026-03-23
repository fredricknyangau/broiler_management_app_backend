from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_
from sqlalchemy.orm import joinedload
from typing import List, Any, Optional, Generic, TypeVar
from uuid import UUID
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Dict

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
from app.db.models.audit import AuditLog
from app.schemas.audit import AuditLogResponse

router = APIRouter()

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total_count: int
    total_pages: int
    current_page: int

@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List all users with pagination and search
    """
    query = select(User)
    if search:
        query = query.filter(or_(User.email.ilike(f"%{search}%"), User.full_name.ilike(f"%{search}%")))
        
    total_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total_res.scalar() or 0
    
    result = await db.execute(query.order_by(User.created_at.desc()).offset(skip).limit(limit))
    users = result.scalars().all()
    
    return PaginatedResponse(
        items=users,
        total_count=total_count,
        total_pages=(total_count + limit - 1) // limit if limit > 0 else 1,
        current_page=(skip // limit) + 1 if limit > 0 else 1
    )

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
    active_flocks: int = 0
    users_growth_percent: float = 0.0
    revenue_growth_percent: float = 0.0
    users_by_plan: Dict[str, int] = {}
    mrr: float = 0.0

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

@router.put("/users/{user_id}/subscription", response_model=SubscriptionResponse)
async def update_user_subscription(
    user_id: UUID,
    plan_update: PlanUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Override or create a user's active subscription (Admin only).
    """
    user_res = await db.execute(select(User).filter(User.id == user_id))
    user = user_res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).order_by(Subscription.created_at.desc())
    )
    sub = result.scalars().first()

    now = datetime.now()
    if sub:
        sub.plan_type = plan_update.plan_type
        sub.updated_at = now
    else:
        sub = Subscription(
            user_id=user_id,
            plan_type=plan_update.plan_type,
            status=SubscriptionStatus.ACTIVE,
            start_date=now,
            end_date=now + timedelta(days=365)
        )
        db.add(sub)

    await db.commit()
    await db.refresh(sub)

    await log_action(
        db=db,
        action="UPDATE_SUBSCRIPTION",
        user_id=current_admin.id,
        resource_type="Subscription",
        details=f"Updated user {user_id} plan to {plan_update.plan_type}"
    )

    return sub

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
    
    users_by_plan = {}
    revenue = 0.0
    mrr = 0.0
    price_map = {"STARTER": 0.0, "PROFESSIONAL": 3500.0, "ENTERPRISE": 10000.0}
    
    for sub in active_subs:
        try:
            if getattr(sub, 'amount', None):
                revenue += float(sub.amount)
        except:
            pass
        plan = str(sub.plan_type).upper()
        users_by_plan[plan] = users_by_plan.get(plan, 0) + 1
        mrr += price_map.get(plan, 0.0)
            
    # Calculate M-o-M Growth
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    
    users_tm_res = await db.execute(select(func.count(User.id)).filter(User.created_at >= thirty_days_ago))
    users_lm_res = await db.execute(select(func.count(User.id)).filter(User.created_at >= sixty_days_ago, User.created_at < thirty_days_ago))
    users_tm = users_tm_res.scalar() or 0
    users_lm = users_lm_res.scalar() or 0
    users_growth = ((users_tm - users_lm) / users_lm * 100.0) if users_lm > 0 else (100.0 if users_tm > 0 else 0.0)
    
    rev_tm_res = await db.execute(select(Subscription).filter(Subscription.created_at >= thirty_days_ago, Subscription.status == SubscriptionStatus.ACTIVE))
    rev_lm_res = await db.execute(select(Subscription).filter(Subscription.created_at >= sixty_days_ago, Subscription.created_at < thirty_days_ago, Subscription.status == SubscriptionStatus.ACTIVE))
    
    def sum_rev(subs):
        return sum(float(s.amount) for s in subs if s.amount and s.amount.replace('.','',1).isdigit())
        
    rev_tm = sum_rev(rev_tm_res.scalars().all())
    rev_lm = sum_rev(rev_lm_res.scalars().all())
    rev_growth = ((rev_tm - rev_lm) / rev_lm * 100.0) if rev_lm > 0 else (100.0 if rev_tm > 0 else 0.0)
            
    return AdminStats(
        total_users=total_users.scalar() or 0,
        active_users=active_users.scalar() or 0,
        active_subscriptions=active_subs_count,
        total_revenue_est=revenue,
        total_flocks=total_flocks.scalar() or 0,
        active_flocks=active_flocks.scalar() or 0,
        users_growth_percent=round(users_growth, 2),
        revenue_growth_percent=round(rev_growth, 2),
        users_by_plan=users_by_plan,
        mrr=mrr
    )

@router.get("/transactions", response_model=PaginatedResponse[AdminTransaction])
async def get_transactions(
    limit: int = 50,
    skip: int = 0,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    List all subscriptions (transactions) securely.
    """
    query = select(Subscription).options(joinedload(Subscription.user))
    if search:
        query = query.join(User).filter(or_(User.email.ilike(f"%{search}%"), Subscription.plan_type.ilike(f"%{search}%")))
        
    total_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total_res.scalar() or 0

    result = await db.execute(
        query.order_by(Subscription.created_at.desc())
        .offset(skip).limit(limit)
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
    
    return PaginatedResponse(
        items=results,
        total_count=total_count,
        total_pages=(total_count + limit - 1) // limit if limit > 0 else 1,
        current_page=(skip // limit) + 1 if limit > 0 else 1
    )

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
async def get_system_configs(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    List all system configurations (Admin only)
    """
    result = await db.execute(select(SystemConfig))
    configs = list(result.scalars().all())
    
    # Auto-seed Phase 4 typed defaults
    existing_keys = {c.key for c in configs}
    defaults = {
        "MAINTENANCE_MODE": "false",
        "REGISTRATION_OPEN": "true",
        "GLOBAL_BANNER": ""
    }
    
    added_new = False
    for key, val in defaults.items():
        if key not in existing_keys:
            new_conf = SystemConfig(key=key, value=val, category="system", is_encrypted=False)
            db.add(new_conf)
            configs.append(new_conf)
            added_new = True
            
    if added_new:
        await db.commit()
        
    return configs

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


# --- Audit Logs ---

@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get system audit logs (Admin only)
    """
    query = select(AuditLog).options(joinedload(AuditLog.user))
    if search:
        query = query.join(User, isouter=True).filter(
            or_(
                AuditLog.action.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                AuditLog.resource_type.ilike(f"%{search}%")
            )
        )
        
    total_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total_res.scalar() or 0

    result = await db.execute(
        query.order_by(AuditLog.timestamp.desc())
        .offset(skip).limit(limit)
    )
    logs = result.scalars().all()
    
    # Map user_email for frontend friendly response
    for log in logs:
        if log.user:
            log.user_email = log.user.email
            
    return PaginatedResponse(
        items=logs,
        total_count=total_count,
        total_pages=(total_count + limit - 1) // limit if limit > 0 else 1,
        current_page=(skip // limit) + 1 if limit > 0 else 1
    )


class AggregateAnalytics(BaseModel):
    date: str
    total_revenue: float = 0.0
    total_expenses: float = 0.0
    total_birds: int = 0

@router.get("/analytics/aggregate", response_model=List[AggregateAnalytics])
async def get_aggregate_analytics(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get system-wide aggregate financial and flock metrics grouped by date (last 6 months).
    """
    today = datetime.now().date()
    start_date = today - timedelta(days=180)

    sales_stmt = select(Sale.date, func.sum(Sale.amount).label("amount")).filter(Sale.date >= start_date).group_by(Sale.date)
    sales_res = await db.execute(sales_stmt)
    sales = {r.date: r.amount for r in sales_res.all()}

    expenses_stmt = select(Expenditure.date, func.sum(Expenditure.amount).label("amount")).filter(Expenditure.date >= start_date).group_by(Expenditure.date)
    expenses_res = await db.execute(expenses_stmt)
    expenses = {r.date: r.amount for r in expenses_res.all()}

    flocks_stmt = select(Flock.start_date, func.sum(Flock.initial_count).label("birds")).filter(Flock.start_date >= start_date).group_by(Flock.start_date)
    flocks_res = await db.execute(flocks_stmt)
    flocks = {r.start_date: r.birds for r in flocks_res.all()}

    all_dates = sorted(set(list(sales.keys()) + list(expenses.keys()) + list(flocks.keys())))
    result = []
    for d in all_dates:
        result.append(AggregateAnalytics(
            date=d.strftime("%Y-%m-%d"),
            total_revenue=float(sales.get(d, 0)),
            total_expenses=float(expenses.get(d, 0)),
            total_birds=int(flocks.get(d, 0))
        ))

    return result

