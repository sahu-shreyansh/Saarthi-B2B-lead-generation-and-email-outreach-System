import time
import uuid
import datetime
from loguru import logger
from celery import shared_task
from sqlalchemy import and_, not_

from app.database.database import SessionLocal
from app.database.models import Campaign, Lead, CampaignEmail, InboxThread, InboxMessage, WorkerLog, SendingAccount
from app.providers.llm.openrouter_provider import OpenRouterProvider
from app.services.email_sender import EmailSender
from app.providers.llm.prompt_templates import SYSTEM_PROMPT, FOLLOWUP_GENERATION_PROMPT

@shared_task(name="run_followup_campaign", bind=True)
def run_followup_campaign(self):
    """
    Background worker that scans for leads who haven't replied after 3 days
    and triggers an automated follow-up.
    """
    logger.info("Starting automated follow-up scan")
    db = SessionLocal()
    start_time = time.time()
    followup_count = 0
    
    try:
        # 1. Find leads who are 'contacted' but haven't replied
        # We look for leads where status='contacted' and no incoming messages in their threads
        three_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=3)
        
        leads_to_followup = db.query(Lead).filter(
            Lead.status == "contacted",
            Lead.updated_at <= three_days_ago
        ).all()
        
        ai = OpenRouterProvider(db=db)
        
        for lead in leads_to_followup:
            # Check if they have an active thread with incoming messages
            thread = db.query(InboxThread).filter(InboxThread.lead_id == lead.id).first()
            if thread:
                has_reply = db.query(InboxMessage).filter(
                    InboxMessage.thread_id == thread.id,
                    InboxMessage.direction == "incoming"
                ).first()
                if has_reply:
                    logger.info(f"Lead {lead.id} already replied. Skipping follow-up.")
                    continue

            # 2. Check if we already sent a follow-up recently
            last_email = db.query(CampaignEmail).filter(
                CampaignEmail.lead_id == lead.id
            ).order_by(CampaignEmail.created_at.desc()).first()
            
            if last_email and last_email.created_at > three_days_ago:
                continue

            # 3. Generate Follow-up Email
            logger.info(f"Generating follow-up for lead {lead.id}")
            
            prompt = FOLLOWUP_GENERATION_PROMPT.format() # Follow-up prompt in templates is static for now
            
            reply_body = ai.generate(
                prompt_type="followup",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                org_id=str(lead.organization_id),
                use_fast_model=True
            )
            
            # 4. Fetch active sending account for the org
            account = db.query(SendingAccount).filter(
                SendingAccount.organization_id == lead.organization_id,
                SendingAccount.is_active == True
            ).first()

            if account:
                msg_id = EmailSender.send_email(
                    account=account,
                    to_email=lead.contact_email,
                    subject=f"Re: Touching base",
                    body=reply_body
                )
                success = msg_id is not None
            else:
                logger.error(f"No active sending account for org {lead.organization_id}")
                success = False
            
            if success:
                # Update lead metadata to track follow-up
                meta_data = lead.metadata_ or {}
                meta_data["last_followup_at"] = datetime.datetime.utcnow().isoformat()
                meta_data["followups_sent"] = meta_data.get("followups_sent", 0) + 1
                lead.metadata_ = meta_data
                followup_count += 1
                
        db.commit()
    except Exception as e:
        logger.error(f"Follow-up campaign failed: {str(e)}")
        db.rollback()
    finally:
        runtime = time.time() - start_time
        log = WorkerLog(
            task_id=str(self.request.id or uuid.uuid4()), 
            task_name="run_followup_campaign", 
            runtime_seconds=runtime, 
            status="SUCCESS", 
            error_logs=""
        )
        db.add(log)
        db.commit()
        db.close()
        
    return f"Follow-up scan complete. Sent {followup_count} emails."
