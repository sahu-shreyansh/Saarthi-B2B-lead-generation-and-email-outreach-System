"""
Sequence Worker — Daily cron job.
Queries active campaigns and their leads to send initial emails (Step 0)
and followups (Step 1+) based on the customizable sequence_config.
"""

import structlog
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.db.models import OutreachLog, Lead, Conversation, Message, Campaign, SendingAccount
from app.services.gmail_service import GmailService

log = structlog.get_logger("sequence_worker")

async def run_sequences():
    """Called by APScheduler daily."""
    today = date.today()
    log.info("sequence_worker.started", today=today.isoformat())

    async with AsyncSessionLocal() as db:
        # Get all active campaigns that have a sequence config
        campaigns_q = await db.execute(select(Campaign).where(Campaign.status == "active"))
        campaigns = campaigns_q.scalars().all()

        if not campaigns:
            log.info("sequence_worker.no_active_campaigns")
            return

        sent_count = 0

        for campaign in campaigns:
            sequence_steps = campaign.sequence_config
            if not sequence_steps or not isinstance(sequence_steps, list):
                continue
            
            # 1. Process NEW leads (Step 0)
            if len(sequence_steps) > 0:
                step_0 = sequence_steps[0]
                new_leads_q = await db.execute(
                    select(Lead)
                    .where(Lead.campaign_id == campaign.id)
                    .where(Lead.status == "NEW")
                    # only send if email is valid or catch_all
                    .where(Lead.email_status.in_(["valid", "catch_all", "unknown"]))
                )
                new_leads = new_leads_q.scalars().all()

                for lead in new_leads:
                    try:
                        sent = await _send_step(db, campaign, lead, step_0, 0, today)
                        if sent:
                            sent_count += 1
                    except Exception as e:
                        log.error("sequence_worker.failed_step0", lead_id=str(lead.id), error=str(e))

            # 2. Process IN_SEQUENCE leads (Step 1+)
            # Find logs that are pending followup today or earlier
            pending_q = await db.execute(
                select(OutreachLog)
                .join(Lead, OutreachLog.lead_id == Lead.id)
                .where(OutreachLog.campaign_id == campaign.id)
                .where(OutreachLog.reply_status == "NO_REPLY")
                .where(OutreachLog.followup_status == "PENDING")
                .where(OutreachLog.next_followup_due <= today)
                .where(Lead.status == "IN_SEQUENCE")
            )
            pending_logs = pending_q.scalars().all()

            for entry in pending_logs:
                try:
                    next_step_idx = entry.sequence_step + 1
                    
                    if next_step_idx >= len(sequence_steps):
                        # Sequence completed!
                        entry.followup_status = "STOPPED"
                        continue

                    step_config = sequence_steps[next_step_idx]

                    # Get lead
                    lead_q = await db.execute(select(Lead).where(Lead.id == entry.lead_id))
                    lead = lead_q.scalar_one_or_none()
                    if not lead:
                        entry.followup_status = "STOPPED"
                        continue

                    sent = await _send_step(db, campaign, lead, step_config, next_step_idx, today, previous_log=entry)
                    if sent:
                        sent_count += 1

                except Exception as e:
                    log.error("sequence_worker.failed_followup", lead_id=str(entry.lead_id), error=str(e))

        await db.commit()
        log.info("sequence_worker.complete", total_sent=sent_count)


async def _send_step(db, campaign, lead, step_config, step_idx, today, previous_log=None):
    # Determine the sender (mocking logic or real fetching)
    # Get the user's active sending account if any
    account_q = await db.execute(
        select(SendingAccount).where(SendingAccount.user_id == campaign.user_id, SendingAccount.is_active == True)
    )
    account = account_q.scalars().first()
    
    if account:
        gmail = GmailService(token_json=account.token_json)
    else:
        gmail = GmailService() # fallback for demo/stub

    # Substitute variables
    name = lead.name.split()[0] if lead.name else "there"
    company = lead.company or "your organization"
    
    raw_subject = step_config.get("subject", "Following up")
    raw_body = step_config.get("body", "")

    # Very basic variable substitution
    subject = raw_subject.replace("{{name}}", name).replace("{{company}}", company)
    body_text = raw_body.replace("{{name}}", name).replace("{{company}}", company)
    
    html_body = f"<pre style='font-family:sans-serif;white-space:pre-wrap'>{body_text}</pre>"
    
    # Threading logic for replies
    reply_to = previous_log.message_id if previous_log else None
    thread_id = previous_log.thread_id if previous_log else None
    
    # For followups, some people want identical subject to force threading
    if previous_log and step_idx > 0:
        if not subject.lower().startswith("re:"):
            subject = f"Re: {previous_log.subject}"

    # Send the email!
    result = await gmail.send(
        to=lead.email,
        subject=subject,
        html_body=html_body,
        reply_to_message_id=reply_to,
        thread_id=thread_id,
    )

    sent_at = datetime.utcnow()
    
    # Calculate next delay
    delay_days = step_config.get("delay", 3)
    if delay_days == 0 and step_idx == 0:
        # Step 0 delay is 0, but if we need a followup, we look at the NEXT step's delay
        # Wait, the delay is defined on the step itself. 
        # If step 1 has delay=2, it means wait 2 days AFTER step 0.
        sequence_steps = campaign.sequence_config
        if len(sequence_steps) > 1:
            delay_days = sequence_steps[1].get("delay", 3)
        else:
            delay_days = 0
            
    elif step_idx > 0:
        sequence_steps = campaign.sequence_config
        if step_idx + 1 < len(sequence_steps):
             delay_days = sequence_steps[step_idx + 1].get("delay", 3)
        else:
             delay_days = 0
             
    followup_due = today + timedelta(days=delay_days)

    if previous_log:
        previous_log.followup_status = "STOPPED"

    new_log = OutreachLog(
        campaign_id=campaign.id,
        lead_id=lead.id,
        sequence_step=step_idx,
        thread_id=result.get("thread_id", ""),
        message_id=result.get("message_id", ""),
        subject=subject,
        body=body_text,
        sent_at=sent_at,
        reply_status="NO_REPLY",
        followup_status="PENDING" if delay_days > 0 else "STOPPED",
        next_followup_due=followup_due,
    )
    db.add(new_log)

    # Conversation logic
    if thread_id:
        conv_q = await db.execute(select(Conversation).where(Conversation.thread_id == thread_id))
        conv = conv_q.scalar_one_or_none()
    else:
        conv = None
        
    if not conv:
        conv = Conversation(
            campaign_id=campaign.id,
            lead_id=lead.id,
            thread_id=result.get("thread_id", ""),
            last_message_at=sent_at,
        )
        db.add(conv)
        await db.flush()
    else:
        conv.last_message_at = sent_at

    msg = Message(
        conversation_id=conv.id,
        sender_type="USER",
        message_id=result.get("message_id", ""),
        subject=subject,
        body=body_text,
        sent_at=sent_at,
    )
    db.add(msg)
    
    # Update lead status
    lead.status = "IN_SEQUENCE"
    
    return True
