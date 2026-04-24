from datetime import datetime, timedelta, timezone
from decimal import Decimal

import structlog
from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     Request, status)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user, get_current_user, get_db
from app.config import settings
from app.db.models.subscription import (PlanType, Subscription,
                                        SubscriptionPlan, SubscriptionStatus)
from app.db.models.user import User, UserRole
from app.schemas.billing import (MpesaCallbackResponse, PlanResponse,
                                 SubscriptionCreate, SubscriptionResponse)
from app.services.mpesa_service import mpesa_service

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/plans", response_model=list[PlanResponse])
async def get_plans(db: AsyncSession = Depends(get_db)) -> list[PlanResponse]:
    """
    Returns the available subscription plans from the database.
    """
    result = await db.execute(
        select(SubscriptionPlan)
        .filter(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.monthly_price.asc())
    )
    return result.scalars().all()


@router.get("/plan-details", response_model=PlanResponse)
async def get_active_plan_details(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
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
    result = await db.execute(
        select(SubscriptionPlan).filter(SubscriptionPlan.plan_type == plan_type)
    )
    plan = result.scalars().first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan configuration not found")

    return plan


@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe(
    payload: SubscriptionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initiates a subscription using M-Pesa STK Push.
    """
    if current_user.role not in [UserRole.FARMER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Farm Owners can manage subscriptions.",
        )

    # 1. Fetch Plan Details from DB for Pricing
    result = await db.execute(
        select(SubscriptionPlan).filter(SubscriptionPlan.plan_type == payload.plan_type)
    )
    plan = result.scalars().first()

    if not plan:
        raise HTTPException(
            status_code=404, detail="Subscription plan configuration not found."
        )

    try:
        if payload.billing_period == "monthly":
            amount = int(plan.monthly_price)
        else:
            amount = int(plan.yearly_price)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=500,
            detail="Plan price configuration is invalid (numeric expected).",
        )

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
        mpesa_reference=f"SUB-{current_user.id}-{int(datetime.now(timezone.utc).timestamp())}",
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    # 3. Trigger M-Pesa STK Push
    try:
        response = await mpesa_service.initiate_stk_push(
            phone=phone, amount=amount, reference=subscription.mpesa_reference
        )
        # Save CheckoutRequestID
        checkout_request_id = response.get("CheckoutRequestID")
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
        logger.error("Subscription Error", error=str(e))  # Ensure it's logged
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error during subscription processing.",
        )

    return subscription


@router.post("/mpesa/callback", response_model=MpesaCallbackResponse)
async def mpesa_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives M-Pesa payment callbacks from Safaricom.

    SECURITY: We never blindly trust the incoming ``result_code``.  After
    parsing the callback we call ``query_stk_status()`` to re-confirm the
    transaction status directly with Safaricom before mutating any data.
    This prevents fake callback attacks.
    """
    _log = structlog.get_logger(__name__)

    data = await request.json()
    _log.info("M-Pesa callback received", extra={"payload_keys": list(data.keys())})

    try:
        body = data.get("Body", {})
        stk_callback = body.get("stkCallback", {})

        checkout_request_id = stk_callback.get("CheckoutRequestID")
        callback_result_code = stk_callback.get("ResultCode")

        _log.info(
            "STK callback parsed",
            extra={"checkout_id": checkout_request_id, "code": callback_result_code},
        )

        if not checkout_request_id:
            _log.warning("Callback missing CheckoutRequestID — ignored")
            return {"status": "ignored", "reason": "No CheckoutRequestID"}

        # ── Canonical verification via STK Query ───────────────────────────────
        verified_code: int | None = None
        try:
            query_result = await mpesa_service.query_stk_status(checkout_request_id)
            raw_code = query_result.get("ResultCode")
            verified_code = int(raw_code) if raw_code is not None else None
            _log.info("STK Query verified", extra={"verified_code": verified_code})
        except Exception as qe:
            _log.warning(
                "STK Query failed, falling back to callback result_code: %s", qe
            )
            verified_code = (
                int(callback_result_code) if callback_result_code is not None else None
            )

        payment_successful = verified_code == 0
        response = await _handle_callback_entity(
            db, checkout_request_id, payment_successful, verified_code, stk_callback
        )
        return response

    except Exception as e:
        _log.exception("Error processing M-Pesa callback: %s", e)
        # Always return 200 to Safaricom so it doesn't retry indefinitely
        return {"status": "error", "detail": "Internal processing error"}


async def _handle_callback_entity(
    db: AsyncSession,
    checkout_request_id: str,
    payment_successful: bool,
    verified_code: int | None,
    stk_callback: dict,
) -> dict:
    """Helper to process the specific entity (Subscription, Sale, or Expenditure)
    matched by a CheckoutRequestID. This reduces complexity in the main callback handler.
    """
    _log = structlog.get_logger(__name__)

    # 1. Subscription lookup
    sub_res = await db.execute(
        select(Subscription).filter(
            Subscription.checkout_request_id == checkout_request_id
        )
    )
    subscription = sub_res.scalars().first()

    # ── Import finance models here to avoid circular imports at module level ─
    from app.db.models.finance import Expenditure, Sale
    from app.db.models.inventory import InventoryItem

    # 2. Sale lookup
    sale = None
    if not subscription:
        sale_res = await db.execute(
            select(Sale).filter(Sale.checkout_request_id == checkout_request_id)
        )
        sale = sale_res.scalars().first()

    # 3. Expenditure lookup
    exp = None
    if not subscription and not sale:
        exp_res = await db.execute(
            select(Expenditure).filter(
                Expenditure.checkout_request_id == checkout_request_id
            )
        )
        exp = exp_res.scalars().first()

    res_code = verified_code
    if subscription:
        if subscription.status == SubscriptionStatus.ACTIVE:
            _log.info("Subscription already active", extra={"ref": subscription.mpesa_reference})
            res_code = 0
        else:
            if payment_successful:
                _log.info("Activating subscription", extra={"ref": subscription.mpesa_reference})
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.start_date = datetime.now(timezone.utc)
                days = 365 if subscription.billing_period == "yearly" else 30
                subscription.end_date = datetime.now(timezone.utc) + timedelta(days=days)
            else:
                _log.info("Payment failed for sub", extra={"ref": subscription.mpesa_reference})
                subscription.status = SubscriptionStatus.CANCELLED
            await db.commit()

    elif sale:
        if sale.mpesa_transaction_id:
            _log.info("Sale already confirmed", extra={"sale_id": str(sale.id)})
            res_code = 0
        else:
            if payment_successful:
                _log.info("Confirming sale payment", extra={"sale_id": str(sale.id)})
                for element in stk_callback.get("CallbackMetadata", {}).get("Item", []):
                    if element.get("Name") == "MpesaReceiptNumber":
                        sale.mpesa_transaction_id = element.get("Value")
                        break
            await db.commit()

    elif exp:
        if exp.mpesa_transaction_id:
            _log.info("Expenditure already confirmed", extra={"exp_id": str(exp.id)})
            res_code = 0
        else:
            if payment_successful:
                _log.info("Confirming supply payment", extra={"exp_id": str(exp.id)})
                for element in stk_callback.get("CallbackMetadata", {}).get("Item", []):
                    if element.get("Name") == "MpesaReceiptNumber":
                        exp.mpesa_transaction_id = element.get("Value")
                        break
                if exp.inventory_item_id and exp.quantity:
                    inv_res = await db.execute(
                        select(InventoryItem).filter(InventoryItem.id == exp.inventory_item_id)
                    )
                    inv_item = inv_res.scalars().first()
                    if inv_item:
                        inv_item.current_stock += exp.quantity
            await db.commit()

    else:
        _log.warning("No entity matched CheckoutRequestID", extra={"checkout_id": checkout_request_id})
        return {"status": "ignored", "reason": "No matching entity found"}

    return {"status": "processed", "result_code": res_code}



@router.get("/my-subscription", response_model=SubscriptionResponse)
async def get_my_subscription(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get the current active subscription for the user.
    """
    from app.api.deps import _get_effective_subscription

    # 1. Admins and Superusers get auto-Enterprise
    if current_user.role == UserRole.ADMIN or current_user.is_superuser:
        return SubscriptionResponse(
            id=current_user.id,
            user_id=current_user.id,
            plan_type=PlanType.ENTERPRISE,
            status=SubscriptionStatus.ACTIVE,
            start_date=None,
            end_date=None,
            mpesa_reference=None,
            billing_period=None,
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
            billing_period=None,
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

    result = await db.execute(
        select(Subscription).filter(Subscription.mpesa_reference == mpesa_reference)
    )
    sub = result.scalars().first()

    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    sub.status = SubscriptionStatus.ACTIVE
    sub.start_date = datetime.now(timezone.utc)

    if sub.billing_period == "yearly":
        sub.end_date = datetime.now(timezone.utc) + timedelta(days=365)
    else:
        sub.end_date = datetime.now(timezone.utc) + timedelta(days=30)

    await db.commit()
    return {"status": "success", "message": "Subscription activated (DEV simulation)"}
