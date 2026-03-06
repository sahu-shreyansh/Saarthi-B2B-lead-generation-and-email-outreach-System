import uuid
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db, BaseRepository
from app.database.models import Subscription, User
from app.core.deps import get_current_user, get_current_org_id

router = APIRouter(prefix="/billing", tags=["Billing"])

class SubscriptionResponse(BaseModel):
    plan_type: str
    status: str
    monthly_email_limit: int
    monthly_lead_limit: int

@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    repo = BaseRepository(Subscription, db, org_id)
    sub = repo.get_multi(limit=1)
    
    if not sub:
        # Create default FREE subscription if it somehow doesn't exist
        sub_obj = repo.create(obj_in={
            "plan": "FREE",
            "status": "ACTIVE",
            "monthly_credit_limit": 100
        })
        return sub_obj
        
    return sub[0]

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
