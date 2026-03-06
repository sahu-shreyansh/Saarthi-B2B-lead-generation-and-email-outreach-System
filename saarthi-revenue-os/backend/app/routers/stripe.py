from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
import json

from app.database.database import get_db
from app.services.billing import UsageService
from app.workers.stripe_worker import process_stripe_event_task
import stripe

router = APIRouter(prefix="/webhooks/stripe", tags=["Billing"])

from app.core.settings import settings

@router.post("")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Idempotent Stripe Webhook Receiver.
    Must immediately return 200 OK after inserting event_id to prevent Stripe retries.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # 1. Validate Signature 
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured in .env")
        
    try:
        event_obj = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        event = event_obj.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


    event_id = event.get("id")
    event_type = event.get("type")

    if not event_id:
         raise HTTPException(status_code=400, detail="Missing event_id")

    # 2. Idempotency Check via UsageService
    is_new, msg = UsageService.process_stripe_webhook_event(
        db=db, 
        event_id=event_id, 
        event_type=event_type, 
        payload=event
    )

    if not is_new:
        # It's a duplicate - simply return early with 200 to satisfy Stripe retry hook
        return {"status": "ignored", "detail": msg}

    # 3. Offload Heavy Processing to Async Celery queue to prevent HTTP blocking
    process_stripe_event_task.delay(event_id=event_id)
    
    return {"status": "success", "detail": "Event queued for asynchronous processing"}
