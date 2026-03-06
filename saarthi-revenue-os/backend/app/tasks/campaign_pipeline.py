import time
import uuid
from loguru import logger
from celery import shared_task

from app.database.database import SessionLocal
from app.database.models import Campaign, Lead, CampaignEmail, WorkerLog, EmailEvent
from app.services.email_generation_service import EmailGenerationService
from app.services.email_sender import EmailSenderService

@shared_task(name="run_campaign", bind=True)
def run_campaign(self, campaign_id: str):
    """
    Finds leads for an active campaign that haven't been emailed yet, 
    generates emails for them using OpenRouter, and sends them.
    """
    logger.info(f"Running campaign {campaign_id}")
    db = SessionLocal()
    start_time = time.time()
    
    try:
        camp_uuid = uuid.UUID(campaign_id)
        campaign = db.query(Campaign).filter(Campaign.id == camp_uuid).first()
        if not campaign or campaign.status != "active":
            return "Campaign not active or missing"
            
        # Find leads belonging to this org that match the campaign criteria
        # For simplicity in rebuild, just grab NEW un-contacted leads in the org
        # In full production, this might map leads through a campaign_leads junction
        leads = db.query(Lead).filter(
            Lead.organization_id == campaign.organization_id,
            Lead.status == "new"
        ).limit(campaign.daily_limit).all()
        
        sent_count = 0
        for lead in leads:
            # 1. Generate Email via AI
            subject, body = EmailGenerationService.generate_cold_email(
                db=db,
                organization_id=str(campaign.organization_id),
                campaign_id=campaign_id,
                lead_data={"name": lead.contact_name, "company": lead.company_name, "industry": lead.industry},
                email_template=campaign.email_template or "Write a standard value-prop email."
            )
            
            # 2. Record intent to send
            camp_email = CampaignEmail(
                campaign_id=camp_uuid,
                lead_id=lead.id,
                subject=subject,
                body=body,
                status="draft"
            )
            db.add(camp_email)
            db.commit()
            db.refresh(camp_email)
            
            # 3. Trigger Async Sending Task
            send_email_task.delay(str(camp_email.id), str(campaign.organization_id))
            
            # 4. Update Lead Status
            lead.status = "contacted"
            sent_count += 1
            
        # Update Campaign Stats
        stats = campaign.stats or {}
        stats["sent"] = stats.get("sent", 0) + sent_count
        campaign.stats = stats
        db.commit()
    except Exception as e:
        logger.error(f"Campaign run failed: {str(e)}")
    finally:
        runtime = time.time() - start_time
        log = WorkerLog(task_id=str(self.request.id or uuid.uuid4()), task_name="run_campaign", runtime_seconds=runtime, status="SUCCESS", error_logs="")
        db.add(log)
        db.commit()
        db.close()


@shared_task(name="send_email_task", bind=True)
def send_email_task(self, campaign_email_id: str, organization_id: str):
    import asyncio
    logger.info(f"Sending email {campaign_email_id}")
    db = SessionLocal()
    start_time = time.time()
    
    try:
        email_uuid = uuid.UUID(campaign_email_id)
        camp_email = db.query(CampaignEmail).filter(CampaignEmail.id == email_uuid).first()
        if not camp_email:
            return
            
        lead = db.query(Lead).filter(Lead.id == camp_email.lead_id).first()
        if not lead or not lead.contact_email:
            camp_email.status = "failed"
            db.commit()
            return
            
        # Send via SendGrid or generic SMTP hook
        # Using a sync wrapper around the async email sender purely for Celery standard usage
        async def run_async_send():
            return await EmailSenderService.send_email(
                provider="smtp", # Mock provider fallback
                to_email=lead.contact_email,
                subject=camp_email.subject,
                body=camp_email.body
            )
            
        success, msg_id, meta = asyncio.run(run_async_send())
        
        if success:
            camp_email.status = "sent"
            # Track email event
            event = EmailEvent(
                campaign_email_id=email_uuid,
                event_type="sent",
                metadata_={"message_id": msg_id, "provider_response": meta}
            )
            db.add(event)
        else:
            camp_email.status = "failed"
            event = EmailEvent(
                campaign_email_id=email_uuid,
                event_type="bounced",
                metadata_={"error": msg_id}
            )
            db.add(event)
            
        db.commit()
    except Exception as e:
        logger.error(f"Send email task failed: {str(e)}")
    finally:
        runtime = time.time() - start_time
        log = WorkerLog(task_id=str(self.request.id or uuid.uuid4()), task_name="send_email_task", runtime_seconds=runtime, status="SUCCESS", error_logs="")
        db.add(log)
        db.commit()
        db.close()
