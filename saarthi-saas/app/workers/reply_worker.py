"""
Reply Worker — 15-minute cron job.
Polls Gmail inbox, matches threadIds against outreach_logs,
classifies replies (regex-first for OOO, LLM fallback).
"""

import re
import base64
import structlog
import httpx
from datetime import datetime

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import OutreachLog, Conversation, Message, Lead, SendingAccount
from app.services.gmail_service import GmailService
from app.core.config import settings

log = structlog.get_logger("reply_worker")

OOO_PATTERNS = [
    r"out of office", r"away from (the )?office", r"on leave",
    r"automatic(ally)? reply", r"auto.reply", r"vacation",
    r"will be back", r"currently unavailable", r"away until", r"on holiday",
]
_OOO_RE = re.compile("|".join(OOO_PATTERNS), re.IGNORECASE)


def _extract_body_text(message: dict) -> str:
    try:
        payload = message.get("payload", {})
        parts = payload.get("parts", [])

        def _decode(data: str) -> str:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

        if not parts and payload.get("body", {}).get("data"):
            return _decode(payload["body"]["data"])

        for part in parts:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return _decode(part["body"]["data"])

        for part in parts:
            data = part.get("body", {}).get("data", "")
            if data:
                return _decode(data)
    except Exception as e:
        log.warning("reply_worker.body_extract_failed", error=str(e))
    return ""


async def _classify_reply(body: str) -> str:
    prompt = (
        'Classify the intent of this email reply. '
        'Return JSON only: {"reply_type": "POSITIVE" | "NEGATIVE" | "NEUTRAL", "confidence": 0-1}\n\n'
        f"Email:\n{body[:1500]}"
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            import json
            parsed = json.loads(resp.json()["choices"][0]["message"]["content"])
            return parsed.get("reply_type", "NEUTRAL").upper()
    except Exception as e:
        log.error("reply_worker.llm_failed", error=str(e))
        return "NEUTRAL"


async def poll_replies():
    """
    Called by APScheduler every 15 minutes.
    Finds new replies in Gmail inbox and updates outreach_logs.
    """
    log.info("reply_worker.started")

    async with AsyncSessionLocal() as db:
        # Get all sending accounts to iterate
        accounts_q = await db.execute(select(SendingAccount).where(SendingAccount.is_active == True))
        accounts = accounts_q.scalars().all()

        if not accounts:
            log.info("reply_worker.no_sending_accounts")
            # Still check with mock service for demo
            await _poll_for_account(db, GmailService())
            return

        for account in accounts:
            gmail = GmailService(token_json=account.token_json)
            await _poll_for_account(db, gmail)

        await db.commit()

    log.info("reply_worker.complete")


async def _poll_for_account(db, gmail: GmailService):
    # Get all known thread_ids
    logs_q = await db.execute(
        select(OutreachLog.thread_id, OutreachLog.id)
        .where(OutreachLog.reply_status == "NO_REPLY")
        .where(OutreachLog.thread_id != "")
    )
    thread_map = {}
    for thread_id, log_id in logs_q.all():
        thread_map.setdefault(thread_id, []).append(log_id)

    if not thread_map:
        return

    messages = gmail.list_inbox_messages("is:inbox newer_than:1d")
    if not messages:
        return

    for stub in messages:
        thread_id = stub.get("threadId")
        if not thread_id or thread_id not in thread_map:
            continue

        msg = gmail.get_message(stub["id"])
        if not msg:
            continue

        body = _extract_body_text(msg)
        received_at = datetime.utcnow()

        # OOO regex first
        if _OOO_RE.search(body):
            reply_type = "OOO"
        else:
            reply_type = await _classify_reply(body)

        # Update all outreach_log rows with this thread_id
        for log_id in thread_map[thread_id]:
            log_q = await db.execute(select(OutreachLog).where(OutreachLog.id == log_id))
            entry = log_q.scalar_one_or_none()
            if entry:
                entry.reply_status = "REPLIED"
                entry.reply_type = reply_type
                entry.followup_status = "STOPPED"

        # Update lead status
        # Get lead from first log entry
        first_log_q = await db.execute(
            select(OutreachLog).where(OutreachLog.id == thread_map[thread_id][0])
        )
        first_log = first_log_q.scalar_one_or_none()
        if first_log:
            lead_q = await db.execute(select(Lead).where(Lead.id == first_log.lead_id))
            lead = lead_q.scalar_one_or_none()
            if lead:
                lead.status = "REPLIED"

            # Save reply as message in conversation
            conv_q = await db.execute(
                select(Conversation).where(Conversation.thread_id == thread_id)
            )
            conv = conv_q.scalar_one_or_none()
            if conv:
                reply_msg = Message(
                    conversation_id=conv.id,
                    sender_type="LEAD",
                    message_id=stub["id"],
                    body=body,
                    sent_at=received_at,
                )
                db.add(reply_msg)
                conv.last_message_at = received_at
