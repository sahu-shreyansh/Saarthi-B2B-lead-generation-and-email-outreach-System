"""
AI Worker — Celery tasks for background AI agent execution.
Runs email generation and reply classification asynchronously.
"""
import logging
from app.workers.celery_app import celery_app
from app.database.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, soft_time_limit=120, name="generate_email_for_lead_task")
def generate_email_for_lead_task(
    self,
    lead_id: str,
    organization_id: str,
    mode: str = "normal",
    services: list = None,
):
    """
    Background task: generate a personalized cold email for a lead.
    mode: "normal" (paragraph services) | "classifier" (scored JSON services)
    services: list of { service_name, service_description } dicts (for classifier mode)
    """
    db = SessionLocal()
    try:
        from app.ai.services.ai_pipeline import run_email_pipeline
        result = run_email_pipeline(
            lead_id=lead_id,
            organization_id=organization_id,
            db=db,
            mode=mode,
            services=services or [],
        )
        logger.info(f"[AIWorker] Email pipeline completed for lead {lead_id}. Status: {result.get('_meta', {}).get('status', 'done')}")
        return result
    except Exception as e:
        logger.error(f"[AIWorker] generate_email_for_lead_task failed for lead {lead_id}: {e}")
        self.retry(exc=e, countdown=10, max_retries=2)
    finally:
        db.close()


@celery_app.task(bind=True, soft_time_limit=60, name="classify_reply_task")
def classify_reply_task(self, reply_id: str, organization_id: str):
    """
    Background task: classify an incoming email reply intent.
    Updates EmailReply.intent in the database on completion.
    """
    db = SessionLocal()
    try:
        from app.ai.services.ai_pipeline import run_reply_classification
        result = run_reply_classification(
            reply_id=reply_id,
            organization_id=organization_id,
            db=db,
        )
        logger.info(f"[AIWorker] Reply {reply_id} classified as '{result.get('intent', 'unknown')}'")
        return result
    except Exception as e:
        logger.error(f"[AIWorker] classify_reply_task failed for reply {reply_id}: {e}")
        self.retry(exc=e, countdown=5, max_retries=2)
    finally:
        db.close()


@celery_app.task(bind=True, soft_time_limit=60, name="extract_signals_task")
def extract_signals_task(self, lead_id: str, organization_id: str):
    """
    Background task: extract lead signals without writing an email.
    """
    db = SessionLocal()
    try:
        from app.ai.services.ai_pipeline import run_signal_extraction
        result = run_signal_extraction(
            lead_id=lead_id,
            organization_id=organization_id,
            db=db,
        )
        logger.info(f"[AIWorker] Signals extracted for lead {lead_id}")
        return result
    except Exception as e:
        logger.error(f"[AIWorker] extract_signals_task failed for lead {lead_id}: {e}")
        self.retry(exc=e, countdown=10, max_retries=2)
    finally:
        db.close()
