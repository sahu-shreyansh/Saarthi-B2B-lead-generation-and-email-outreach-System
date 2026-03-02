from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, date, timedelta

from app.db.session import get_db
from app.db.models import (
    User, Campaign, Lead, OutreachLog, Conversation, Message,
    Subscription, UsageTracking,
)
from app.core.deps import get_current_user
from app.services.gmail_service import get_gmail_service

router = APIRouter()


class SendRequest(BaseModel):
    lead_id: str
    subject: str
    body: str


@router.post("/send")
async def send_email(
    body: SendRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Check usage limits
    month_str = date.today().strftime("%Y-%m")
    usage_q = await db.execute(
        select(UsageTracking).where(
            UsageTracking.user_id == user.id,
            UsageTracking.month == month_str,
        )
    )
    usage = usage_q.scalar_one_or_none()
    if not usage:
        usage = UsageTracking(user_id=user.id, month=month_str, emails_sent=0)
        db.add(usage)
        await db.flush()

    sub_q = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = sub_q.scalar_one_or_none()
    limit = sub.monthly_limit if sub else 100

    if usage.emails_sent >= limit:
        raise HTTPException(status_code=402, detail="Monthly email limit reached. Upgrade your plan.")

    # 2. Get lead + campaign (ownership check)
    lead_q = await db.execute(select(Lead).where(Lead.id == body.lead_id))
    lead = lead_q.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    camp_q = await db.execute(
        select(Campaign).where(Campaign.id == lead.campaign_id, Campaign.user_id == user.id)
    )
    campaign = camp_q.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # 3. Check for existing thread (for reply continuation)
    existing_log_q = await db.execute(
        select(OutreachLog)
        .where(OutreachLog.lead_id == lead.id)
        .order_by(OutreachLog.sent_at.desc())
        .limit(1)
    )
    existing_log = existing_log_q.scalar_one_or_none()

    # 4. Send via Gmail
    gmail = get_gmail_service(user.id, db)
    result = await gmail.send(
        to=lead.email,
        subject=body.subject,
        html_body=f"<pre style='font-family:sans-serif;white-space:pre-wrap'>{body.body}</pre>",
        reply_to_message_id=existing_log.message_id if existing_log and existing_log.thread_id else None,
        thread_id=existing_log.thread_id if existing_log and existing_log.thread_id else None,
    )

    sent_at = datetime.utcnow()
    sequence_step = (existing_log.sequence_step + 1) if existing_log else 1
    followup_due = date.today() + timedelta(days=3)

    # 5. Append to outreach_logs
    log_entry = OutreachLog(
        campaign_id=campaign.id,
        lead_id=lead.id,
        sequence_step=sequence_step,
        thread_id=result["thread_id"],
        message_id=result["message_id"],
        subject=body.subject,
        body=body.body,
        sent_at=sent_at,
        reply_status="NO_REPLY",
        followup_status="PENDING",
        next_followup_due=followup_due,
    )
    db.add(log_entry)

    # 6. Create/update conversation
    conv_q = await db.execute(
        select(Conversation).where(Conversation.thread_id == result["thread_id"])
    )
    conversation = conv_q.scalar_one_or_none()
    if not conversation:
        conversation = Conversation(
            campaign_id=campaign.id,
            lead_id=lead.id,
            thread_id=result["thread_id"],
            last_message_at=sent_at,
        )
        db.add(conversation)
        await db.flush()
    else:
        conversation.last_message_at = sent_at

    # 7. Save message
    message = Message(
        conversation_id=conversation.id,
        sender_type="USER",
        message_id=result["message_id"],
        subject=body.subject,
        body=body.body,
        sent_at=sent_at,
    )
    db.add(message)

    # 8. Update lead status
    lead.status = "IN_SEQUENCE"

    # 9. Increment usage
    usage.emails_sent += 1

    return {
        "status": "sent",
        "message_id": result["message_id"],
        "thread_id": result["thread_id"],
        "sequence_step": sequence_step,
    }
