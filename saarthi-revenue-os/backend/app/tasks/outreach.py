import datetime
from sqlalchemy.orm import Session
from app.workers.celery_app import celery_app
from app.database.database import SessionLocal
from app.database.models import Lead, Campaign, Sequence, SequenceStep, CampaignEmail, SendingAccount
from app.services.email_sender import EmailSender

@celery_app.task(name="process_outbound_sequence_task")
def process_outbound_sequence_task():
    """
    Stateless worker that runs periodically to detect due leads.
    Logic:
    1. Find leads with status='pending' and next_action_at <= now.
    2. Determine next step in sequence.
    3. Send personalized email.
    4. Update lead stage and schedule next step.
    """
    db = SessionLocal()
    try:
        # Use timezone-aware UTC now
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # 1. Fetch leads due for action
        # next_action_at being NULL counts as due if status is pending (initial contact)
        due_leads = db.query(Lead).filter(
            Lead.status == "pending",
            (Lead.next_action_at <= now) | (Lead.next_action_at.is_(None))
        ).all()
        
        if not due_leads:
            print("OUTREACH_WORKER: No due leads found at this time.")
            return "No due leads found."

        processed_count = 0
        for lead in due_leads:
            # 2. Identify Campaign & Sequence
            if not lead.campaign_id:
                lead.status = "error"
                lead.metadata_["error"] = "Lead has no assigned campaign"
                continue

            campaign = db.query(Campaign).filter(Campaign.id == lead.campaign_id).first()
            if not campaign:
                lead.status = "error"
                lead.metadata_["error"] = f"Campaign {lead.campaign_id} not found"
                continue
                
            if not campaign.sequence_id:
                lead.status = "error"
                lead.metadata_["error"] = "No sequence assigned to campaign"
                continue
            
            # 3. Find Next Step
            # Note: current_step_number starts at 0 for new leads
            next_step_num = lead.current_step_number + 1
            step = db.query(SequenceStep).filter(
                SequenceStep.sequence_id == campaign.sequence_id,
                SequenceStep.step_number == next_step_num
            ).first()
            
            if not step:
                # No more steps left in the sequence
                print(f"OUTREACH_WORKER: Lead {lead.id} has completed the sequence.")
                lead.status = "completed"
                continue
                
            # 4. Pick a Sending Account
            # Round-robin or priority could be added here. Currently grabbing first active.
            account = db.query(SendingAccount).filter(
                SendingAccount.organization_id == lead.organization_id,
                SendingAccount.is_active == True
            ).first()
            
            if not account:
                print(f"OUTREACH_WORKER: No active sending account for org {lead.organization_id}")
                lead.metadata_["error"] = "No active sending accounts found"
                continue
            
            # 5. Personalize and Send
            subject = EmailSender.personalize_template(step.template_subject or campaign.name, lead)
            body = EmailSender.personalize_template(step.template_body or "", lead)
            
            # Check for threading: find the latest message ID sent to this lead for this campaign
            prev_email = db.query(CampaignEmail).filter(
                CampaignEmail.lead_id == lead.id,
                CampaignEmail.campaign_id == campaign.id
            ).order_by(CampaignEmail.created_at.desc()).first()
            
            msg_id = EmailSender.send_email(
                account=account,
                to_email=lead.contact_email,
                subject=subject,
                body=body,
                thread_msg_id=prev_email.message_id if prev_email else None
            )
            
            if msg_id:
                # 6. Success: Track communication and Schedule
                
                # Log the sent email
                new_email = CampaignEmail(
                    campaign_id=campaign.id,
                    lead_id=lead.id,
                    sequence_step_id=step.id,
                    subject=subject,
                    body=body,
                    message_id=msg_id,
                    status="sent",
                    sent_at=now
                )
                db.add(new_email)
                
                # Advance Lead Stage
                lead.current_step_number = next_step_num
                
                # Schedule next step based on wait_days
                wait_days = step.wait_days if step.wait_days is not None else 3
                lead.next_action_at = now + datetime.timedelta(days=wait_days)
                
                # Explicitly keep as pending so the worker picks it up again when next_action_at passes
                lead.status = "pending"
                
                processed_count += 1
                print(f"OUTREACH_WORKER: Successfully processed Step {next_step_num} for lead {lead.id}")
            else:
                # Failed to send via SMTP
                lead.metadata_["error"] = "Email sending failed. Check SMTP settings."
                print(f"OUTREACH_WORKER: Failed to send email for lead {lead.id}")
        
        db.commit()
        return f"Processed {processed_count} outreach actions."
        
    except Exception as e:
        print(f"OUTREACH_WORKER_ERROR: {str(e)}")
        db.rollback()
        return f"Error: {str(e)}"
    finally:
        db.close()
