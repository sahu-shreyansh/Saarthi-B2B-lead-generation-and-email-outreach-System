import logging
import datetime
import re
from sqlalchemy.exc import IntegrityError
from app.workers.celery_app import celery_app
from app.database.database import SessionLocal
from app.database.models import SendingAccount, OutreachLog, Conversation, Message, Lead
from app.providers.scraping.factory import get_provider

logger = logging.getLogger(__name__)

def detect_bounce_type(subject: str, body: str, raw_headers: dict) -> str:
    """
    Enterprise DSN Parsing.
    Looks for standardized SMTP status codes in headers or body to accurately
    classify HARD (5.x.x) vs SOFT (4.x.x) bounces.
    """
    subject_lower = subject.lower() if subject else ""
    body_lower = body.lower() if body else ""
    
    # 1. Check raw headers for standard DSN flags (if provider payload includes them)
    # Often found in x-failed-recipients or diagnostic-code
    diagnostic = raw_headers.get("Diagnostic-Code", "").lower()
    if diagnostic:
        if "5." in diagnostic: return "HARD"
        if "4." in diagnostic: return "SOFT"
        
    # 2. Regex search for SMTP codes in the body
    # Looks for patterns like "5.1.1" or "Status: 5.4.1"
    smtp_match = re.search(r'\b([45])\.\d{1,3}\.\d{1,3}\b', body_lower)
    if smtp_match:
        code_prefix = smtp_match.group(1)
        if code_prefix == "5": return "HARD"
        if code_prefix == "4": return "SOFT"

    # 3. Fallback string matching for prominent bounce phrases
    hard_phrases = ["address not found", "does not exist", "unroutable", "invalid recipient"]
    soft_phrases = ["mailbox full", "quota exceeded", "temporarily deferred", "server too busy"]
    
    for phrase in hard_phrases:
        if phrase in body_lower or phrase in subject_lower:
            return "HARD"
            
    for phrase in soft_phrases:
        if phrase in body_lower or phrase in subject_lower:
            return "SOFT"

    # Not a bounce
    return "NONE"


@celery_app.task(bind=True, soft_time_limit=300)
def detect_replies_task(self):
    """
    Polls connected active sending accounts for new replies, matches them, 
    and classifies responses (Human Reply vs Bounce vs OOO).
    """
    db = SessionLocal()
    try:
        accounts = db.query(SendingAccount).filter(SendingAccount.is_active == True).all()

        for account in accounts:
            try:
                # 1. Initialize abstract provider
                provider = get_provider(account.provider, {
                    "token": "...", # Typically loaded from secure store
                    "refresh_token": account.refresh_token, # Decrypt in prod
                    "client_id": "...", 
                    "client_secret": "...",
                    "email_address": account.email
                })
                
                # Fetch recent messages (e.g., since yesterday)
                since_ts = int((datetime.datetime.now() - datetime.timedelta(days=1)).timestamp())
                new_replies = provider.fetch_replies(since_timestamp=since_ts)

                for reply in new_replies:
                    try:
                        # 2. Match Thread
                        normalized_thread = provider.normalize_thread_id(reply["thread_id"])
                        conversation = db.query(Conversation).filter_by(thread_id=normalized_thread).first()
                        if not conversation:
                            continue # Not our thread

                        # Ensure idempotency lock prior to processing
                        # provider + message_id is guaranteed UNIQUE by DB
                        msg = Message(
                            org_id=conversation.org_id,
                            conversation_id=conversation.id,
                            direction="INBOUND",
                            provider=account.provider,
                            message_id=reply["message_id"],
                            subject=reply.get("subject", ""),
                            body=reply["body"],
                            raw_payload=reply.get("raw_payload", {}),
                            sent_at=reply["date"]
                        )
                        db.add(msg)
                        db.commit()

                        # 3. Analyze content for Bounces
                        bounce_type = detect_bounce_type(
                            subject=reply.get("subject", ""),
                            body=reply["body"],
                            raw_headers=reply.get("raw_payload", {}).get("headers", {})
                        )

                        # 4. Update Outreach & Lead State
                        outreach = db.query(OutreachLog).filter_by(
                            thread_id=normalized_thread, org_id=conversation.org_id
                        ).first()
                        
                        if outreach:
                            lead = db.query(Lead).filter_by(id=outreach.lead_id).first()
                            
                            if bounce_type in ["HARD", "SOFT"]:
                                # Handle Bounce
                                outreach.status = "BOUNCED"
                                outreach.followup_status = "STOPPED"
                                
                                if lead:
                                    lead.bounce_status = bounce_type
                                    lead.bounce_count += 1
                                    if bounce_type == "HARD" or lead.bounce_count > 3:
                                        lead.status = "BOUNCED"
                            else:
                                # Handle normal Human Reply
                                if outreach.reply_status == "NO_REPLY":
                                    outreach.reply_status = "REPLIED"
                                    outreach.followup_status = "STOPPED"
                                    
                                    if lead:
                                        lead.status = "REPLIED"
                                        
                            # Update Conversation
                            conversation.last_message_at = reply["date"]
                            conversation.is_unread = True
                            
                        db.commit()

                    except IntegrityError:
                        db.rollback()
                        logger.debug(f"Idempotent skip: Duplicate message {reply['message_id']}")
                        continue

            except Exception as e:
                logger.error(f"Error checking replies for account {account.id}: {e}")
                
    finally:
        db.close()
