from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from jose import JWTError, jwt
from uuid import UUID

from app.db.session import get_db
from app.db.models.user import User, UserRole
from app.db.models.subscription import Subscription, SubscriptionStatus, PlanType
from app.core.security import SECRET_KEY, ALGORITHM

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extract and validate JWT token, return current user.
    Usage: current_user: User = Depends(get_current_user)
    """
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Async query
    result = await db.execute(select(User).filter(User.id == UUID(user_id)))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def set_tenant_context(db: AsyncSession, user: User):
    """
    Set PostgreSQL session variable for RLS.
    Call this after getting current_user in protected routes.
    """
    await db.execute(
        text(f"SET LOCAL app.current_user_id = '{str(user.id)}'")
    )
    await db.commit()


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Legacy dependency for superusers.
    """
    if not current_user.is_superuser and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to check if current user is an admin.
    """
    if current_user.role != UserRole.ADMIN and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

def get_current_manager_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to check if current user is a manager or admin.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

def get_current_non_viewer(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to check if current user is NOT a viewer (i.e., can edit/create data).
    """
    if current_user.role == UserRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot create or modify records"
        )
    return current_user

async def _get_effective_subscription(db: AsyncSession, user: User) -> Subscription | None:
    """
    Looks up an active subscription for the user directly, or via Farm membership
    if they are a Manager/Viewer on a Farm owned by a subscriber.
    """
    from app.db.models.farm_member import FarmMember
    from app.db.models.farm import Farm

    # 1. Direct Ownership Lookup (e.g. Farmer)
    result = await db.execute(
        select(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        )
    )
    sub = result.scalars().first()
    if sub:
        return sub

    # 2. Member Inheritance Lookup (e.g. Manager/Viewer)
    member_result = await db.execute(
        select(FarmMember).where(FarmMember.user_id == user.id)
    )
    membership = member_result.scalars().first()
    if membership:
        farm_result = await db.execute(select(Farm).where(Farm.id == membership.farm_id))
        farm = farm_result.scalar_one_or_none()
        if farm:
            owner_sub_result = await db.execute(
                select(Subscription).filter(
                    Subscription.user_id == farm.owner_id,
                    Subscription.status == SubscriptionStatus.ACTIVE
                )
            )
            return owner_sub_result.scalars().first()

    return None

async def check_professional_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> bool:
    """
    Dependency to verify user has an active Professional or Enterprise plan.
    Throws 403 Forbidden if they are on the Starter tier.
    Supports Farm membership inheritance.
    """
    sub = await _get_effective_subscription(db, current_user)
    
    if not sub or sub.plan_type == PlanType.STARTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a Professional Plan subscription on the Farm Account."
        )
        
    return True

async def check_enterprise_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> bool:
    """
    Dependency to verify user has an active Enterprise plan.
    Throws 403 Forbidden if they are on Starter or Professional tiers.
    Supports Farm membership inheritance.
    """
    sub = await _get_effective_subscription(db, current_user)
    
    if not sub or sub.plan_type != PlanType.ENTERPRISE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires an Enterprise Plan subscription on the Farm Account."
        )
        
    return True
