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

@router.get("/stats")
def get_system_stats(
    db: Session = Depends(get_db),
    current_superuser: User = Depends(get_current_active_superuser),
):
    """
    Get system-wide statistics.
    """
    total_users = db.query(func.count(User.id)).scalar()
    total_flocks = db.query(func.count(Flock.id)).scalar()
    active_flocks = db.query(func.count(Flock.id)).filter(Flock.status == 'active').scalar()
    
    return {
        "total_users": total_users,
        "total_flocks": total_flocks,
        "active_flocks": active_flocks,
    }
