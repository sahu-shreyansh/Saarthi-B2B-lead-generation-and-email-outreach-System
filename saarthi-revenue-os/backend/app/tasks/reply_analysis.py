from app.workers.celery_app import celery_app
from app.database.database import SessionLocal
from app.database.models import EmailReply, Lead, Campaign
from app.services.reply_classifier import ReplyClassifier

@celery_app.task(name="classify_reply_task")
def classify_reply_task(reply_id: str):
    """
    Task to classify an email reply using AI and update lead/campaign status.
    """
    db = SessionLocal()
    try:
        reply = db.query(EmailReply).filter(EmailReply.id == reply_id).first()
        if not reply:
            return f"Error: Reply {reply_id} not found."
            
        lead = db.query(Lead).filter(Lead.id == reply.lead_id).first()
        if not lead:
            return f"Error: Lead for reply {reply_id} not found."
            
        # Classify the content
        intent = ReplyClassifier.classify_reply(
            db=db,
            organization_id=str(lead.organization_id),
            content=reply.content
        )
        
        # Update Reply
        reply.intent = intent
        
        # Update Lead Status based on intent
        if intent in ["interested", "meeting_request"]:
            lead.status = intent
            # Stop sequence for this lead
            lead.next_action_at = None
        elif intent == "not_interested":
            lead.status = "not_interested"
            # Stop sequence
            lead.next_action_at = None
        elif intent == "out_of_office":
            # Just mark intent, maybe delay next step by 5 days?
            import datetime
            if lead.next_action_at:
                lead.next_action_at += datetime.timedelta(days=7)
        
        db.commit()
        
        # 4. Trigger Auto-Scheduling Orchestrator (Phase 18)
        if intent in ["interested", "meeting_request"]:
            from app.services.scheduling_orchestrator import SchedulingOrchestrator
            try:
                SchedulingOrchestrator.handle_meeting_request(db, reply_id)
            except Exception as e:
                print(f"CLASSIFY_REPLY_TASK: Auto-scheduling failed: {str(e)}")

        return f"Classified reply {reply_id} as {intent}."
        
    except Exception as e:
        print(f"CLASSIFY_REPLY_TASK_ERROR: {str(e)}")
        db.rollback()
        return f"Error: {str(e)}"
    finally:
        db.close()
