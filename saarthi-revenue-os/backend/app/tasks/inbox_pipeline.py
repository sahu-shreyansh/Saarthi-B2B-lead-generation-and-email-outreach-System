import time
import uuid
from loguru import logger
from celery import shared_task
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.database.models import InboxThread, InboxMessage, Lead, Meeting, WorkerLog
from app.services.inbox_classification_service import InboxClassificationService
from app.services.auto_reply_service import AutoReplyService
from app.services.email_sender import EmailSenderService

@shared_task(name="fetch_new_messages_task", bind=True)
def fetch_new_messages_task(self, organization_id: str):
    logger.info(f"Fetching new messages for org {organization_id}")
    db = SessionLocal()
    start_time = time.time()
    try:
        # Mock fetching from IMAP / Google Workspace
        # In a real app we would use imaplib or Google API here
        time.sleep(1)
        
        org_uuid = uuid.UUID(organization_id)
        
        # Simulate creating a mock incoming message for an active thread
        # 1. Find a Thread
        thread = db.query(InboxThread).filter(InboxThread.organization_id == org_uuid).first()
        if thread:
            new_msg = InboxMessage(
                thread_id=thread.id,
                direction="incoming",
                sender_email="prospect@example.com",
                sender_name="John Doe",
                subject="Re: " + (thread.subject or "Touching base"),
                body="Sounds interesting. Can we chat next Tuesday?",
                intent="unknown"
            )
            db.add(new_msg)
            db.commit()
            db.refresh(new_msg)
            
            # Immediately classify it
            classify_message_task.delay(str(new_msg.id))
            
    except Exception as e:
        logger.error(f"Fetch messages failed: {str(e)}")
    finally:
        runtime = time.time() - start_time
        log = WorkerLog(task_id=str(self.request.id or uuid.uuid4()), task_name="fetch_new_messages", runtime_seconds=runtime, status="SUCCESS", error_logs="")
        db.add(log)
        db.commit()
        db.close()

@shared_task(name="classify_message_task", bind=True)
def classify_message_task(self, message_id: str):
    logger.info(f"Classifying message {message_id}")
    db = SessionLocal()
    start_time = time.time()
    try:
        msg_uuid = uuid.UUID(message_id)
        msg = db.query(InboxMessage).filter(InboxMessage.id == msg_uuid).first()
        if not msg:
            return
        
        # Get organization_id through thread
        thread = db.query(InboxThread).filter(InboxThread.id == msg.thread_id).first()
            
        intent = InboxClassificationService.classify_message(
            db, str(thread.organization_id) if thread else "unknown", str(msg.id), msg.subject, msg.body
        )
        msg.intent = intent
        msg.is_processed = True
        db.commit()
        
        # Depending on intent, trigger auto reply
        if intent in ["positive", "ooo", "not_interested"]:
            generate_reply_task.delay(str(msg.id))
            
    except Exception as e:
        logger.error(f"Classify message failed: {str(e)}")
    finally:
        runtime = time.time() - start_time
        log = WorkerLog(task_id=str(self.request.id or uuid.uuid4()), task_name="classify_message", runtime_seconds=runtime, status="SUCCESS", error_logs="")
        db.add(log)
        db.commit()
        db.close()

@shared_task(name="generate_reply_task", bind=True)
def generate_reply_task(self, message_id: str):
    logger.info(f"Generating AI reply for {message_id}")
    db = SessionLocal()
    start_time = time.time()
    try:
        msg_uuid = uuid.UUID(message_id)
        msg = db.query(InboxMessage).filter(InboxMessage.id == msg_uuid).first()
        if not msg:
            return
        
        # Get organization_id through thread
        thread = db.query(InboxThread).filter(InboxThread.id == msg.thread_id).first()
        org_id = str(thread.organization_id) if thread else "unknown"
            
        history = "Previous message: " + (msg.body or "")
        
        reply_body = AutoReplyService.generate_reply(
            db, org_id, str(msg.id), history, msg.intent, "https://calendly.com/mock"
        )
        msg.ai_response = reply_body
        
        # Save outgoing message
        out_msg = InboxMessage(
            thread_id=msg.thread_id,
            direction="outgoing",
            sender_email="sdr@saarthi.io",
            sender_name="SDR",
            subject="Re: " + (msg.subject or ""),
            body=reply_body,
            intent="n/a",
        )
        db.add(out_msg)
        db.commit()
        
        # Trigger sending asynchronously
        import asyncio
        async def run_async_send():
            return await EmailSenderService.send_email(
                provider="smtp", 
                to_email=msg.sender_email,
                subject=out_msg.subject,
                body=out_msg.body
            )
        asyncio.run(run_async_send())
        
    except Exception as e:
        logger.error(f"Generate reply failed: {str(e)}")
    finally:
        runtime = time.time() - start_time
        log = WorkerLog(task_id=str(self.request.id or uuid.uuid4()), task_name="generate_reply", runtime_seconds=runtime, status="SUCCESS", error_logs="")
        db.add(log)
        db.commit()
        db.close()

@shared_task(name="schedule_meeting_task", bind=True)
def schedule_meeting_task(self, lead_id: str, meeting_id: str):
    logger.info(f"Confirming meeting {meeting_id} for lead {lead_id}")
    db = SessionLocal()
    start_time = time.time()
    try:
        lead_uuid = uuid.UUID(lead_id)
        meeting_uuid = uuid.UUID(meeting_id)
        
        lead = db.query(Lead).filter(Lead.id == lead_uuid).first()
        meeting = db.query(Meeting).filter(Meeting.id == meeting_uuid).first()
        
        if lead and meeting:
            import asyncio
            body = f"Hi {lead.contact_name},\n\nLooking forward to our call regarding {meeting.title} on {meeting.scheduled_time}.\nJoin link: {meeting.meeting_link}"
            async def run_async_send():
                return await EmailSenderService.send_email("smtp", lead.contact_email, f"Meeting Confirmed: {meeting.title}", body)
            asyncio.run(run_async_send())
            
    except Exception as e:
        logger.error(f"Schedule meeting failed: {str(e)}")
    finally:
        runtime = time.time() - start_time
        log = WorkerLog(task_id=str(self.request.id or uuid.uuid4()), task_name="schedule_meeting", runtime_seconds=runtime, status="SUCCESS", error_logs="")
        db.add(log)
        db.commit()
        db.close()
