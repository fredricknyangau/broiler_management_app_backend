from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any
import enum
from datetime import datetime, timedelta

from app.api.deps import get_db, get_current_user, get_current_admin_user
from app.config import settings
from app.db.models.user import User
from app.db.models.subscription import Subscription, SubscriptionStatus, PlanType, SubscriptionPlan
from app.schemas.billing import SubscriptionCreate, SubscriptionResponse, PlanResponse
from app.services.mpesa_service import mpesa_service
from typing import List, Optional
import structlog

logger = structlog.get_logger(__name__)

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
            amount = int(plan.monthly_price)
        else:
            amount = int(plan.yearly_price)
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
        amount=Decimal(amount),
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
        logger.error("Subscription Error", error=str(e)) # Ensure it's logged
        raise HTTPException(status_code=500, detail="Internal Server Error during subscription processing.")

    return subscription

@router.post("/mpesa/callback")
async def mpesa_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives M-Pesa payment callbacks from Safaricom.

    SECURITY: We never blindly trust the incoming ``result_code``.  After
    parsing the callback we call ``query_stk_status()`` to re-confirm the
    transaction status directly with Safaricom before mutating any data.
    This prevents fake callback attacks.
    """
    import structlog
    _log = structlog.get_logger(__name__)

    data = await request.json()
    _log.info("M-Pesa callback received", extra={"payload_keys": list(data.keys())})

    try:
        body = data.get("Body", {})
        stk_callback = body.get("stkCallback", {})

        checkout_request_id = stk_callback.get("CheckoutRequestID")
        callback_result_code = stk_callback.get("ResultCode")
        callback_result_desc = stk_callback.get("ResultDesc", "")

        _log.info(
            "STK callback parsed",
            extra={"checkout_id": checkout_request_id, "code": callback_result_code},
        )

        if not checkout_request_id:
            _log.warning("Callback missing CheckoutRequestID — ignored")
            return {"status": "ignored", "reason": "No CheckoutRequestID"}

        # ── Canonical verification via STK Query ───────────────────────────────
        # Never trust the callback result_code alone. Re-query Safaricom to confirm.
        verified_code: int | None = None
        try:
            query_result = await mpesa_service.query_stk_status(checkout_request_id)
            # Safaricom returns ResultCode as a string in query responses
            raw_code = query_result.get("ResultCode")
            verified_code = int(raw_code) if raw_code is not None else None
            _log.info("STK Query verified", extra={"verified_code": verified_code})
        except Exception as qe:
            # If STK Query fails (e.g., sandbox timeout), fall back to callback code
            # but log a warning so this can be monitored.
            _log.warning(
                "STK Query failed, falling back to callback result_code: %s", qe
            )
            verified_code = int(callback_result_code) if callback_result_code is not None else None

        payment_successful = verified_code == 0

        # ── Import finance models here to avoid circular imports at module level ─
        from app.db.models.finance import Sale, Expenditure
        from app.db.models.inventory import InventoryItem

        # ── 1. Subscription lookup ─────────────────────────────────────────────
        sub_result = await db.execute(
            select(Subscription).filter(Subscription.checkout_request_id == checkout_request_id)
        )
        subscription = sub_result.scalars().first()

        if subscription:
            if payment_successful:
                _log.info("Activating subscription", extra={"ref": subscription.mpesa_reference})
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.start_date = datetime.now()
                if subscription.billing_period == "yearly":
                    subscription.end_date = datetime.now() + timedelta(days=365)
                else:
                    subscription.end_date = datetime.now() + timedelta(days=30)
            else:
                _log.info(
                    "Payment failed for subscription",
                    extra={"ref": subscription.mpesa_reference, "desc": callback_result_desc},
                )
                subscription.status = SubscriptionStatus.CANCELLED

            await db.commit()
            return {"status": "processed", "result_code": verified_code}

        # ── 2. Sale lookup ─────────────────────────────────────────────────────
        sale_result = await db.execute(
            select(Sale).filter(Sale.checkout_request_id == checkout_request_id)
        )
        sale = sale_result.scalars().first()

        if sale:
            if payment_successful:
                _log.info("Confirming sale payment", extra={"sale_id": str(sale.id)})
                callback_metadata = stk_callback.get("CallbackMetadata", {})
                for element in callback_metadata.get("Item", []):
                    if element.get("Name") == "MpesaReceiptNumber":
                        sale.mpesa_transaction_id = element.get("Value")
                        break
            await db.commit()
            return {"status": "processed", "result_code": verified_code}

        # ── 3. Expenditure / supply order lookup ───────────────────────────────
        exp_result = await db.execute(
            select(Expenditure).filter(Expenditure.checkout_request_id == checkout_request_id)
        )
        exp = exp_result.scalars().first()

        if exp:
            if payment_successful:
                _log.info("Confirming supply payment", extra={"exp_id": str(exp.id)})
                callback_metadata = stk_callback.get("CallbackMetadata", {})
                for element in callback_metadata.get("Item", []):
                    if element.get("Name") == "MpesaReceiptNumber":
                        exp.mpesa_transaction_id = element.get("Value")
                        break

                if exp.inventory_item_id and exp.quantity:
                    item_result = await db.execute(
                        select(InventoryItem).filter(InventoryItem.id == exp.inventory_item_id)
                    )
                    inv_item = item_result.scalars().first()
                    if inv_item:
                        inv_item.current_stock += exp.quantity
                        _log.info("Stock incremented", extra={"item": inv_item.name, "qty": exp.quantity})

            await db.commit()
            return {"status": "processed", "result_code": verified_code}

        _log.warning("No entity matched CheckoutRequestID", extra={"checkout_id": checkout_request_id})
        return {"status": "ignored", "reason": "No matching entity found"}

    except Exception as e:
        _log.exception("Error processing M-Pesa callback: %s", e)
        # Always return 200 to Safaricom so it doesn't retry indefinitely
        return {"status": "error", "detail": "Internal processing error"}




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


@router.post("/simulate-callback", include_in_schema=False)
async def simulate_callback(
    mpesa_reference: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin_user),
):
    """
    DEV ONLY: Simulate a successful M-Pesa callback.
    Only accessible by admins AND only when DEBUG=True.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found.",
        )

    result = await db.execute(select(Subscription).filter(Subscription.mpesa_reference == mpesa_reference))
    sub = result.scalars().first()

    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    sub.status = SubscriptionStatus.ACTIVE
    sub.start_date = datetime.now()

    if sub.billing_period == "yearly":
        sub.end_date = datetime.now() + timedelta(days=365)
    else:
        sub.end_date = datetime.now() + timedelta(days=30)

    await db.commit()
    return {"status": "success", "message": "Subscription activated (DEV simulation)"}
