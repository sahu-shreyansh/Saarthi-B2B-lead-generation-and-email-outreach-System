import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db, AsyncSessionLocal
from app.db.models import User, Subscription
from app.core.deps import get_current_user
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter()


PLAN_MAP = {
    "starter": {"price_id": settings.STRIPE_PRICE_STARTER, "monthly_limit": 1000},
    "pro": {"price_id": settings.STRIPE_PRICE_PRO, "monthly_limit": 5000},
}


@router.post("/create-checkout-session")
async def create_checkout_session(
    plan: str = "starter",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if plan not in PLAN_MAP:
        raise HTTPException(status_code=400, detail="Invalid plan. Use 'starter' or 'pro'.")

    plan_info = PLAN_MAP[plan]

    # Get or create Stripe customer
    sub_q = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = sub_q.scalar_one_or_none()

    if sub and sub.stripe_customer_id:
        customer_id = sub.stripe_customer_id
    else:
        customer = stripe.Customer.create(email=user.email)
        customer_id = customer.id
        if sub:
            sub.stripe_customer_id = customer_id
        else:
            sub = Subscription(
                user_id=user.id,
                stripe_customer_id=customer_id,
                plan_type="free",
                monthly_limit=100,
            )
            db.add(sub)

    # Create checkout session
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": plan_info["price_id"], "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.FRONTEND_URL}/settings?billing=success",
        cancel_url=f"{settings.FRONTEND_URL}/settings?billing=cancel",
        metadata={"user_id": str(user.id), "plan": plan},
    )

    return {"checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session_data = event["data"]["object"]
        user_id = session_data.get("metadata", {}).get("user_id")
        plan = session_data.get("metadata", {}).get("plan", "starter")
        stripe_subscription_id = session_data.get("subscription")

        if user_id and plan in PLAN_MAP:
            async with AsyncSessionLocal() as db:
                sub_q = await db.execute(
                    select(Subscription).where(Subscription.user_id == user_id)
                )
                sub = sub_q.scalar_one_or_none()
                if sub:
                    sub.plan_type = plan
                    sub.subscription_status = "active"
                    sub.monthly_limit = PLAN_MAP[plan]["monthly_limit"]
                    sub.stripe_subscription_id = stripe_subscription_id or ""
                    await db.commit()

    elif event["type"] == "customer.subscription.deleted":
        sub_data = event["data"]["object"]
        stripe_sub_id = sub_data.get("id")

        async with AsyncSessionLocal() as db:
            sub_q = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
            )
            sub = sub_q.scalar_one_or_none()
            if sub:
                sub.subscription_status = "canceled"
                sub.plan_type = "free"
                sub.monthly_limit = 100
                await db.commit()

    return {"status": "ok"}
