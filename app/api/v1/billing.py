from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any
import enum
from datetime import datetime, timedelta

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.subscription import Subscription, SubscriptionStatus, PlanType, SubscriptionPlan
from app.schemas.billing import SubscriptionCreate, SubscriptionResponse, PlanResponse
from app.services.mpesa_service import mpesa_service
from typing import List, Optional

router = APIRouter()

@router.get("/plans", response_model=List[PlanResponse])
async def get_plans(db: AsyncSession = Depends(get_db)) -> List[PlanResponse]:
    """
    Returns the available subscription plans from the database.
    """
    result = await db.execute(select(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).order_by(SubscriptionPlan.monthly_price.asc()))
    return result.scalars().all()

@router.get("/plan-details", response_model=PlanResponse)
async def get_active_plan_details(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PlanResponse:
    """
    Returns the feature details for the user's current active plan.
    """
    from app.api.deps import _get_effective_subscription
    
    # 1. Get current plan type (STARTER default)
    plan_type = "STARTER"
    if current_user.role == "ADMIN" or current_user.is_superuser:
        plan_type = "ENTERPRISE"
    else:
        sub = await _get_effective_subscription(db, current_user)
        if sub:
            plan_type = sub.plan_type
            
    # 2. Fetch full plan details from DB
    result = await db.execute(select(SubscriptionPlan).filter(SubscriptionPlan.plan_type == plan_type))
    plan = result.scalars().first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan configuration not found")
        
    return plan

@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe(
    payload: SubscriptionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initiates a subscription using M-Pesa STK Push.
    """
    if current_user.role not in ["FARMER", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Farm Owners can manage subscriptions."
        )

    # 1. Fetch Plan Details from DB for Pricing
    result = await db.execute(select(SubscriptionPlan).filter(SubscriptionPlan.plan_type == payload.plan_type))
    plan = result.scalars().first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan configuration not found.")

    try:
        if payload.billing_period == "monthly":
            amount = int(float(plan.monthly_price))
        else:
            amount = int(float(plan.yearly_price))
    except (ValueError, TypeError):
        raise HTTPException(status_code=500, detail="Plan price configuration is invalid (numeric expected).")

    # Normalize Phone Number
    phone = payload.phone_number.strip()
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("0"):
        phone = "254" + phone[1:]

    # 2. Create Pending Subscription Record
    subscription = Subscription(
        user_id=current_user.id,
        plan_type=payload.plan_type,
        billing_period=payload.billing_period,
        status=SubscriptionStatus.PENDING,
        amount=str(amount),
        phone_number=phone,
        mpesa_reference=f"SUB-{current_user.id}-{int(datetime.now().timestamp())}"
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    # 3. Trigger M-Pesa STK Push
    try:
        response = await mpesa_service.initiate_stk_push(
            phone=phone,
            amount=amount,
            reference=subscription.mpesa_reference
        )
        # Save CheckoutRequestID
        checkout_request_id = response.get('CheckoutRequestID')
        if checkout_request_id:
            subscription.checkout_request_id = checkout_request_id
            await db.commit()
            
    except Exception as e:
        await db.delete(subscription)
        await db.commit()
        error_msg = str(e)
        if "M-Pesa API Error" in error_msg:
            # Pass the upstream error message cleanly
            raise HTTPException(status_code=502, detail=error_msg)
        
        # Generic fallback
        print(f"Subscription Error: {e}") # Ensure it's logged
        raise HTTPException(status_code=500, detail="Internal Server Error during subscription processing.")

    return subscription

@router.post("/mpesa/callback")
async def mpesa_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives callback from Safaricom.
    """
    data = await request.json()
    print(f"M-Pesa Callback Data: {data}") # Log incoming data

    try:
        # Extract Body or use existing structure
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        merchant_request_id = stk_callback.get('MerchantRequestID')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        
        print(f"Callback result: {result_code} - {result_desc}")

        if not checkout_request_id:
            print("No CheckoutRequestID in callback")
            return {"status": "ignored", "reason": "No CheckoutRequestID"}

        # Find subscription
        result = await db.execute(select(Subscription).filter(
            Subscription.checkout_request_id == checkout_request_id
        ))
        subscription = result.scalars().first()

        if subscription:
            if result_code == 0:
                # Payment Successful
                print(f"Activating subscription for reference: {subscription.mpesa_reference}")
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.start_date = datetime.now()
                
                # Use billing_period for duration
                if subscription.billing_period == "yearly":
                    subscription.end_date = datetime.now() + timedelta(days=365)
                else:
                    subscription.end_date = datetime.now() + timedelta(days=30)
            else:
                # Payment Failed / Cancelled
                print(f"Payment failed for reference {subscription.mpesa_reference}: {result_desc}")
                subscription.status = SubscriptionStatus.CANCELLED
                # Optionally store result_desc

            await db.commit()
            return {"status": "processed", "result_code": result_code}

        # If not subscription, try Sale lookup
        from app.db.models.finance import Sale, Expenditure
        from app.db.models.inventory import InventoryItem
        
        result_sale = await db.execute(select(Sale).filter(
            Sale.checkout_request_id == checkout_request_id
        ))
        sale = result_sale.scalars().first()

        if sale:
            if result_code == 0:
                print(f"Verifying sale for reference: {sale.id}")
                callback_metadata = stk_callback.get('CallbackMetadata', {})
                items = callback_metadata.get('Item', [])
                for element in items:
                     if element.get('Name') == 'MpesaReceiptNumber':
                          sale.mpesa_transaction_id = element.get('Value')
                          break
            await db.commit()
            return {"status": "processed", "result_code": result_code}

        # Try Expenditure lookup (Supplies / Marketplace)
        result_exp = await db.execute(select(Expenditure).filter(
            Expenditure.checkout_request_id == checkout_request_id
        ))
        exp = result_exp.scalars().first()

        if exp:
            if result_code == 0:
                print(f"Verifying supply order: {exp.id}")
                callback_metadata = stk_callback.get('CallbackMetadata', {})
                items = callback_metadata.get('Item', [])
                for element in items:
                     if element.get('Name') == 'MpesaReceiptNumber':
                          exp.mpesa_transaction_id = element.get('Value')
                          break
                
                # Automated Inventory Update
                if exp.inventory_item_id and exp.quantity:
                    result_item = await db.execute(select(InventoryItem).filter(InventoryItem.id == exp.inventory_item_id))
                    item = result_item.scalars().first()
                    if item:
                        item.current_stock += exp.quantity
                        print(f"Stock incremented for {item.name}: +{exp.quantity}")

            await db.commit()
            return {"status": "processed", "result_code": result_code}

        print(f"No match for CheckoutRequestID: {checkout_request_id}")
        return {"status": "ignored", "reason": "No matching entity found"}

    except Exception as e:
        print(f"Error processing callback: {e}")
        return {"status": "error", "detail": str(e)}


@router.get("/my-subscription", response_model=SubscriptionResponse)
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current active subscription for the user.
    """
    from app.api.deps import _get_effective_subscription

    # 1. Admins and Superusers get auto-Enterprise
    if current_user.role == "ADMIN" or current_user.is_superuser:
        return SubscriptionResponse(
            id=current_user.id,
            user_id=current_user.id,
            plan_type=PlanType.ENTERPRISE,
            status=SubscriptionStatus.ACTIVE,
            start_date=None,
            end_date=None,
            mpesa_reference=None,
            billing_period=None
        )

    # 2. Lookup Inherited/Effective Subscription
    sub = await _get_effective_subscription(db, current_user)

    if not sub:
        # Return a dummy starter plan if none found
        return SubscriptionResponse(
            id=current_user.id,
            user_id=current_user.id,
            plan_type=PlanType.STARTER,
            status=SubscriptionStatus.ACTIVE,
            start_date=None,
            end_date=None,
            mpesa_reference=None,
            billing_period=None
        )
    return sub

@router.post("/simulate-callback")
async def simulate_callback(
    mpesa_reference: str,
    db: AsyncSession = Depends(get_db)
):
    """
    DEV ONLY: Simulate a successful M-Pesa callback to activate a subscription.
    """
    result = await db.execute(select(Subscription).filter(Subscription.mpesa_reference == mpesa_reference))
    sub = result.scalars().first()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    sub.status = SubscriptionStatus.ACTIVE
    sub.start_date = datetime.now()
    
    # Use billing_period for duration
    if sub.billing_period == "yearly":
        sub.end_date = datetime.now() + timedelta(days=365)
    else:
        sub.end_date = datetime.now() + timedelta(days=30)

    await db.commit()
    return {"status": "success", "message": "Subscription activated"}
