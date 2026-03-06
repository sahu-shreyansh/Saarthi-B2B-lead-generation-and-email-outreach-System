from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from app.database.database import get_db
from app.database.models import EmailEvent, Lead
from app.core.settings import settings

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)

class EmailProviderEvent(BaseModel):
    event_type: str  # sent, opened, clicked, bounced, complained
    message_id: str
    email: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

@router.post("/email/event")
async def handle_email_event(
    event: EmailProviderEvent,
    db: Session = Depends(get_db),
    x_webhook_token: Optional[str] = Header(None)
):
    """
    Ingests events from email providers (Resend, SendGrid, etc.)
    and updates internal lead/event status.
    """
    # Simple security check if token is configured
    if settings.WEBHOOK_SECRET and x_webhook_token != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    logger.info(f"Processing {event.event_type} event for {event.email}")

    # 1. Log the event
    db_event = EmailEvent(
        message_id=event.message_id,
        event_type=event.event_type,
        meta=event.metadata or {}
    )
    db.add(db_event)

    # 2. Update Lead status if applicable
    # We find the lead by email. Note: In reality, we'd use a unique tracking ID in the email metadata.
    lead = db.query(Lead).filter(Lead.contact_email == event.email).first()
    if lead:
        if event.event_type == "opened":
            lead.status = "OPENED"
        elif event.event_type == "clicked":
            lead.status = "CLICKED"
        elif event.event_type == "bounced":
            lead.status = "BOUNCED"
        elif event.event_type == "complained":
            lead.status = "UNSUBSCRIBED"
        
        db.add(lead)

    db.commit()
    return {"status": "success"}
