import logging
from app.workers.celery_app import celery_app
from app.database.database import SessionLocal
from app.database.models import StripeEvent, Subscription

logger = logging.getLogger(__name__)

@celery_app.task(name="app.workers.stripe_worker.process_stripe_event_task", bind=True, max_retries=3)
def process_stripe_event_task(self, event_id: str):
    """
    Asynchronously processes an ingested Stripe Webhook.
    Responsible for updating the Subscription record and credit balances.
    """
    db = SessionLocal()
    try:
        # 1. Fetch the queued event
        event = db.query(StripeEvent).filter(StripeEvent.event_id == event_id).first()
        if not event or event.processed:
            logger.info(f"Stripe event {event_id} already processed or missing.")
            return

        event_type = event.type
        payload = event.payload

        # 2. Extract Customer and Subscription info
        data_obj = payload.get("data", {}).get("object", {})
        customer_id = data_obj.get("customer")
        
        if not customer_id:
            logger.warning(f"No customer found in Stripe event {event_id}")
            event.processed = True
            db.commit()
            return
            
        # 3. Handle specific event types (e.g. payment_succeeded)
        if event_type == "invoice.payment_succeeded":
            logger.info(f"Processing payment_succeeded for customer {customer_id}")
            # Locate the subscription
            sub = db.query(Subscription).filter(
                Subscription.stripe_customer_id == customer_id
            ).with_for_update().first()
            
            if sub:
                # E.g., Restock credits on successful monthly invoice
                # Let's assume a basic restock logic based on plan
                # Standard refill could be reading the limits
                sub.credits_used = 0 
                sub.status = "ACTIVE"
                # Event marked processed
                event.processed = True
                db.commit()
                logger.info(f"Successfully restocked credits for org {sub.org_id}")
            else:
                logger.warning(f"No subscription found for stripe customer {customer_id}")
                
        elif event_type == "customer.subscription.deleted":
            logger.info(f"Processing subscription_deleted for customer {customer_id}")
            sub = db.query(Subscription).filter(
                Subscription.stripe_customer_id == customer_id
            ).with_for_update().first()
            if sub:
                sub.status = "CANCELED"
                event.processed = True
                db.commit()
                logger.info(f"Successfully canceled subscription for org {sub.org_id}")

        else:
            # Mark other events as processed so they don't block
            event.processed = True
            db.commit()

    except Exception as exc:
        db.rollback()
        logger.error(f"Error processing stripe event {event_id}: {exc}")
        # Automatically retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        db.close()
