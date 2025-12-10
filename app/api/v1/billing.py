from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any
import enum
from datetime import datetime, timedelta

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.subscription import Subscription, SubscriptionStatus, PlanType
from app.schemas.billing import SubscriptionCreate, SubscriptionResponse
from app.services.mpesa_service import mpesa_service

router = APIRouter()

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
    # 1. Determine Amount
    amount = 0
    if payload.plan_type == "PROFESSIONAL":
        amount = 500 if payload.billing_period == "monthly" else 5000
    elif payload.plan_type == "ENTERPRISE":
        # Enterprise is usually custom, but let's put a placeholder
        amount = 10000 
    else:
        raise HTTPException(status_code=400, detail="Invalid plan type")

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

        if not subscription:
            print(f"Subscription not found for CheckoutRequestID: {checkout_request_id}")
            return {"status": "ignored", "reason": "Subscription not found"}

        if result_code == 0:
            # Payment Successful
            print(f"Activating subscription for reference: {subscription.mpesa_reference}")
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.start_date = datetime.now()
            
            # Re-infer duration (logic duplicated from simulate)
            try:
                amt = float(subscription.amount)
                if amt < 2000: 
                     subscription.end_date = datetime.now() + timedelta(days=30)
                else:
                     subscription.end_date = datetime.now() + timedelta(days=365)
            except:
                subscription.end_date = datetime.now() + timedelta(days=30)
        else:
            # Payment Failed / Cancelled
            print(f"Payment failed for reference {subscription.mpesa_reference}: {result_desc}")
            subscription.status = SubscriptionStatus.CANCELLED
            # Optionally store result_desc

        await db.commit()
        return {"status": "processed", "result_code": result_code}

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
    # Find the latest active subscription
    result = await db.execute(
        select(Subscription).filter(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).order_by(Subscription.created_at.desc())
    )
    sub = result.scalars().first()

    if not sub:
        # Return a dummy starter plan if none found
        return SubscriptionResponse(
            id=current_user.id, # Hacky ID
            user_id=current_user.id,
            plan_type=PlanType.STARTER,
            status=SubscriptionStatus.ACTIVE,
            start_date=None,
            end_date=None,
            mpesa_reference=None
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
    
    # Infer duration from amount
    try:
        amt = float(sub.amount)
        if amt < 2000: # Threshold for monthly
             sub.end_date = datetime.now() + timedelta(days=30)
        else:
             sub.end_date = datetime.now() + timedelta(days=365)
    except:
        # Fallback
        sub.end_date = datetime.now() + timedelta(days=30)

    await db.commit()
    return {"status": "success", "message": "Subscription activated"}
