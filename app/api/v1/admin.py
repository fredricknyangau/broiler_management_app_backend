from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Any
from uuid import UUID

from app.api.deps import get_db, get_current_active_superuser
from app.db.models.user import User
from app.db.models.flock import Flock
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()

@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_superuser: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    List all users (Admin only)
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_status(
    user_id: str,
    user_update: UserUpdate,
    current_superuser: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    """
    Update a user's status or role (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    update_data = user_update.dict(exclude_unset=True)
    # Prevent removing own superuser status accidentally (though frontend should guard too)
    if user.id == current_superuser.id and update_data.get("is_superuser") is False:
         # Optional safety check, but letting it pass for now as admins might want to demote themselves
         pass

    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_superuser: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    """
    Delete a user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_superuser.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

from app.db.models.subscription import Subscription, SubscriptionStatus, PlanType
from app.schemas.billing import SubscriptionResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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
def get_system_stats(
    db: Session = Depends(get_db),
    current_superuser: User = Depends(get_current_active_superuser),
):
    """
    Get system-wide statistics including billing.
    """
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    
    total_flocks = db.query(func.count(Flock.id)).scalar()
    active_flocks = db.query(func.count(Flock.id)).filter(Flock.status == 'active').scalar()
    
    active_subs = db.query(Subscription).filter(Subscription.status == SubscriptionStatus.ACTIVE).all()
    active_subs_count = len(active_subs)
    
    revenue = 0.0
    for sub in active_subs:
        try:
            if sub.amount:
                revenue += float(sub.amount)
        except:
            pass
            
    return AdminStats(
        total_users=total_users or 0,
        active_users=active_users or 0,
        active_subscriptions=active_subs_count,
        total_revenue_est=revenue,
        total_flocks=total_flocks or 0,
        active_flocks=active_flocks or 0
    )

@router.get("/transactions", response_model=List[AdminTransaction])
def get_transactions(
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_active_superuser)
):
    """
    List all subscriptions (transactions).
    """
    subs = db.query(Subscription).order_by(Subscription.created_at.desc()).offset(skip).limit(limit).all()
    
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
def assign_user_plan(
    user_id: UUID,
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_active_superuser)
):
    """
    Manually assign a plan to a user. Cancels any existing active subscription.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Cancel existing
    existing = db.query(Subscription).filter(
        Subscription.user_id == user_id, 
        Subscription.status == SubscriptionStatus.ACTIVE
    ).all()
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
    db.commit()
    
    return {"status": "success", "message": f"Assigned {payload.plan_type} to user"}

@router.post("/subscriptions/{sub_id}/cancel")
def cancel_subscription(
    sub_id: UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_active_superuser)
):
    """
    Force cancel a subscription.
    """
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    sub.status = SubscriptionStatus.CANCELLED
    sub.end_date = datetime.now()
    db.commit()
    
    return {"status": "success", "message": "Subscription cancelled"}
