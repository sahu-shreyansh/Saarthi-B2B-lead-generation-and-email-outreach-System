import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database.database import get_db
from app.database.models import InboxThread, InboxMessage
from app.core.deps import get_current_user_and_org

router = APIRouter(prefix="/inbox", tags=["Inbox"])

class ThreadResponse(BaseModel):
    id: str
    organization_id: str
    lead_id: Optional[str]
    subject: Optional[str]
    status: str
    latest_message_at: str

class MessageResponse(BaseModel):
    id: str
    thread_id: str
    direction: str
    sender_email: Optional[str]
    sender_name: Optional[str]
    subject: Optional[str]
    body: Optional[str]
    intent: str
    ai_response: Optional[str]
    is_processed: bool
    received_at: str

class IncomingWebhookRequest(BaseModel):
    sender_email: str
    sender_name: Optional[str] = None
    subject: str
    body: str

@router.post("/webhook")
def incoming_email_webhook(
    payload: IncomingWebhookRequest,
    db: Session = Depends(get_db)
):
    """
    Experimental webhook to push real incoming emails into the pipeline.
    It matches the sender_email to an existing Lead and Thread.
    """
    from app.database.models import Lead, InboxThread, InboxMessage
    from app.tasks.inbox_pipeline import classify_message_task

    # 1. Find the lead
    lead = db.query(Lead).filter(Lead.contact_email == payload.sender_email).first()
    if not lead:
         # In prod, we might create a discovery lead here, but for now we only process known leads
         raise HTTPException(status_code=404, detail="Sender not recognized as an existing lead.")

    # 2. Find or create a thread
    thread = db.query(InboxThread).filter(InboxThread.lead_id == lead.id).order_by(InboxThread.latest_message_at.desc()).first()
    if not thread:
        thread = InboxThread(
            organization_id=lead.organization_id,
            lead_id=lead.id,
            subject=payload.subject,
            status="active"
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)

    # 3. Create the message
    new_msg = InboxMessage(
        thread_id=thread.id,
        direction="incoming",
        sender_email=payload.sender_email,
        sender_name=payload.sender_name or lead.contact_name,
        subject=payload.subject,
        body=payload.body,
        intent="unknown"
    )
    db.add(new_msg)
    
    # Update thread latest activity
    import datetime
    thread.latest_message_at = datetime.datetime.utcnow()
    
    db.commit()
    db.refresh(new_msg)

    # 4. Trigger Classification
    from app.services.pipeline_orchestrator import PipelineOrchestrator
    PipelineOrchestrator.trigger_classification(db, str(new_msg.id))

    return {"status": "accepted", "message_id": str(new_msg.id), "thread_id": str(thread.id)}

@router.get("", response_model=List[ThreadResponse])
def list_threads(
    skip: int = 0, limit: int = 50,
    status: Optional[str] = Query(None),
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    query = db.query(InboxThread).filter(InboxThread.organization_id == active_org_id)
    
    if status:
        query = query.filter(InboxThread.status == status)
        
    threads = query.order_by(desc(InboxThread.latest_message_at)).offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(t.id),
            "organization_id": str(t.organization_id),
            "lead_id": str(t.lead_id) if t.lead_id else None,
            "subject": t.subject,
            "status": t.status,
            "latest_message_at": t.latest_message_at.isoformat()
        } for t in threads
    ]

@router.get("/{thread_id}/messages", response_model=List[MessageResponse])
def get_thread_messages(
    thread_id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Thread UUID")
        
    thread = db.query(InboxThread).filter(InboxThread.id == thread_uuid, InboxThread.organization_id == active_org_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    messages = db.query(InboxMessage).filter(InboxMessage.thread_id == thread_uuid).order_by(InboxMessage.received_at.asc()).all()
    
    return [
        {
            "id": str(m.id),
            "thread_id": str(m.thread_id),
            "direction": m.direction,
            "sender_email": m.sender_email,
            "sender_name": m.sender_name,
            "subject": m.subject,
            "body": m.body,
            "intent": m.intent,
            "ai_response": m.ai_response,
            "is_processed": m.is_processed,
            "received_at": m.received_at.isoformat()
        } for m in messages
    ]

@router.post("/process")
def trigger_inbox_processing(
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    # Kicks off the Celery pipeline to fetch new messages from email provider
    from app.services.pipeline_orchestrator import PipelineOrchestrator
    task_id = PipelineOrchestrator.process_inbox(db, str(active_org_id))
    
    return {"message": "Inbox processing started", "task_id": task_id}

@router.post("/{thread_id}/reply")
def reply_to_thread(
    thread_id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """Triggers AI reply generation and sending."""
    current_user, active_org_id, role = deps
    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Thread UUID")
        
    thread = db.query(InboxThread).filter(InboxThread.id == thread_uuid, InboxThread.organization_id == active_org_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Needs to get the latest message in thread to reply to
    latest_msg = db.query(InboxMessage).filter(InboxMessage.thread_id == thread_uuid, InboxMessage.direction == "incoming").order_by(InboxMessage.received_at.desc()).first()
    if not latest_msg:
         raise HTTPException(status_code=400, detail="No incoming messages to reply to")
         
    # Triggers AI reply generation and sending
    from app.services.pipeline_orchestrator import PipelineOrchestrator
    task_id = PipelineOrchestrator.trigger_reply(db, str(latest_msg.id))
    
    return {"message": "Reply pipeline started", "task_id": task_id}

@router.post("/{thread_id}/classify")
def classify_thread(
    thread_id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """Triggers AI intent classification on the latest message."""
    current_user, active_org_id, role = deps
    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Thread UUID")
        
    thread = db.query(InboxThread).filter(InboxThread.id == thread_uuid, InboxThread.organization_id == active_org_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    latest_msg = db.query(InboxMessage).filter(InboxMessage.thread_id == thread_uuid, InboxMessage.direction == "incoming").order_by(InboxMessage.received_at.desc()).first()
    if not latest_msg:
         raise HTTPException(status_code=400, detail="No incoming messages to classify")

    # Triggers AI intent classification
    from app.services.pipeline_orchestrator import PipelineOrchestrator
    task_id = PipelineOrchestrator.trigger_classification(db, str(latest_msg.id))
    
    return {"message": "Classification pipeline started", "task_id": task_id}
