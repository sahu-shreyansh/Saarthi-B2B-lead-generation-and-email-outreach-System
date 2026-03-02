from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.db.session import get_db
from app.db.models import User, Campaign, Conversation, Message, Lead
from app.core.deps import get_current_user
from app.services.gmail_service import get_gmail_service

router = APIRouter()


@router.get("/conversations")
async def list_conversations(
    filter: Optional[str] = None,  # all | replied | no_reply | ooo | positive | negative
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get user's campaign IDs
    cq = await db.execute(select(Campaign.id).where(Campaign.user_id == user.id))
    campaign_ids = [r[0] for r in cq.all()]

    if not campaign_ids:
        return []

    query = (
        select(Conversation)
        .where(Conversation.campaign_id.in_(campaign_ids))
        .order_by(Conversation.last_message_at.desc())
        .limit(200)
    )
    result = await db.execute(query)
    conversations = result.scalars().all()

    out = []
    for conv in conversations:
        # Get lead info
        lead_q = await db.execute(select(Lead).where(Lead.id == conv.lead_id))
        lead = lead_q.scalar_one_or_none()

        # Get latest message
        msg_q = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.sent_at.desc())
            .limit(1)
        )
        latest = msg_q.scalar_one_or_none()

        # Get reply status from outreach log
        from app.db.models import OutreachLog
        log_q = await db.execute(
            select(OutreachLog)
            .where(OutreachLog.lead_id == conv.lead_id)
            .order_by(OutreachLog.sent_at.desc())
            .limit(1)
        )
        latest_log = log_q.scalar_one_or_none()
        reply_status = latest_log.reply_status if latest_log else "NO_REPLY"
        reply_type = latest_log.reply_type if latest_log else ""

        # Apply filter
        if filter and filter != "all":
            if filter == "replied" and reply_status != "REPLIED":
                continue
            if filter == "no_reply" and reply_status != "NO_REPLY":
                continue
            if filter == "ooo" and reply_type != "OOO":
                continue
            if filter == "positive" and reply_type != "POSITIVE":
                continue
            if filter == "negative" and reply_type != "NEGATIVE":
                continue

        out.append({
            "id": str(conv.id),
            "thread_id": conv.thread_id,
            "lead_name": lead.name if lead else "",
            "lead_email": lead.email if lead else "",
            "lead_company": lead.company if lead else "",
            "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else "",
            "last_snippet": (latest.body[:120] + "...") if latest and len(latest.body) > 120 else (latest.body if latest else ""),
            "reply_status": reply_status,
            "reply_type": reply_type,
        })

    return out


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv_q = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = conv_q.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Ownership check
    cq = await db.execute(
        select(Campaign).where(Campaign.id == conv.campaign_id, Campaign.user_id == user.id)
    )
    if not cq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get all messages
    msgs_q = await db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.sent_at.asc())
    )
    messages = msgs_q.scalars().all()

    lead_q = await db.execute(select(Lead).where(Lead.id == conv.lead_id))
    lead = lead_q.scalar_one_or_none()

    return {
        "id": str(conv.id),
        "thread_id": conv.thread_id,
        "lead": {
            "id": str(lead.id) if lead else "",
            "name": lead.name if lead else "",
            "email": lead.email if lead else "",
            "company": lead.company if lead else "",
        },
        "messages": [
            {
                "id": str(m.id),
                "sender_type": m.sender_type,
                "subject": m.subject,
                "body": m.body,
                "sent_at": m.sent_at.isoformat() if m.sent_at else "",
            }
            for m in messages
        ],
    }


class ReplyRequest(BaseModel):
    conversation_id: str
    body: str
    subject: Optional[str] = ""


@router.post("/reply")
async def send_reply(
    body: ReplyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv_q = await db.execute(select(Conversation).where(Conversation.id == body.conversation_id))
    conv = conv_q.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Ownership check
    cq = await db.execute(
        select(Campaign).where(Campaign.id == conv.campaign_id, Campaign.user_id == user.id)
    )
    if not cq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    lead_q = await db.execute(select(Lead).where(Lead.id == conv.lead_id))
    lead = lead_q.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Get the latest message_id for In-Reply-To header
    msg_q = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.sent_at.desc())
        .limit(1)
    )
    latest_msg = msg_q.scalar_one_or_none()

    # Send via Gmail
    gmail = get_gmail_service(user.id, db)
    subject = body.subject or (f"Re: {latest_msg.subject}" if latest_msg else "Re: Follow up")
    result = await gmail.send(
        to=lead.email,
        subject=subject,
        html_body=f"<pre style='font-family:sans-serif;white-space:pre-wrap'>{body.body}</pre>",
        reply_to_message_id=latest_msg.message_id if latest_msg else None,
        thread_id=conv.thread_id,
    )

    sent_at = datetime.utcnow()

    # Save message
    message = Message(
        conversation_id=conv.id,
        sender_type="USER",
        message_id=result["message_id"],
        subject=subject,
        body=body.body,
        sent_at=sent_at,
    )
    db.add(message)

    # Update conversation timestamp
    conv.last_message_at = sent_at

    return {
        "status": "sent",
        "message_id": result["message_id"],
        "thread_id": result["thread_id"],
    }
