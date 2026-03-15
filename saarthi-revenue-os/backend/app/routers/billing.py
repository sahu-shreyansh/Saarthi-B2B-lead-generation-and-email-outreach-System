import uuid
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db, get_platform_db, BaseRepository
from app.database.models import Subscription, User
from app.core.deps import get_current_user, get_current_org_id

router = APIRouter(prefix="/billing", tags=["Billing"])

class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    monthly_credit_limit: int
    credits_used: int
    emails_sent_this_month: int
    updated_at: str

@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: Session = Depends(get_platform_db)
):
    from app.database.models import UsageTracking
    import datetime
    
    # 1. Get Subscription
    sub = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
    
    if not sub:
        # Create default FREE subscription if it somehow doesn't exist
        sub = Subscription(
            organization_id=org_id,
            plan="FREE",
            status="ACTIVE",
            monthly_credit_limit=100,
            credits_used=0
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        
    # 2. Get Usage for current month
    month_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")
    usage = db.query(UsageTracking).filter(
        UsageTracking.organization_id == org_id,
        UsageTracking.month == month_str
    ).first()
    
    return {
        "plan": sub.plan,
        "status": sub.status,
        "monthly_credit_limit": sub.monthly_credit_limit,
        "credits_used": sub.credits_used,
        "emails_sent_this_month": usage.emails_sent if usage else 0,
        "updated_at": sub.updated_at.isoformat()
    }

# --- Stripe Webhooks would go here normally ---
@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe events (checkout.session.completed, etc.)
    Note: OrgIsolationMiddleware exempts this path.
    """
    # Verify stripe signature...
    # Update Subscription status...
    return {"status": "success"}
