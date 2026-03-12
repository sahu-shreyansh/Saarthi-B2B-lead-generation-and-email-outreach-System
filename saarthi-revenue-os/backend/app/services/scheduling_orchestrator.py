from sqlalchemy.orm import Session
from app.database.models import Lead, EmailReply, InboxThread, InboxMessage, SendingAccount, CampaignEmail
from app.services.meeting_scheduler import MeetingSchedulerService
from app.services.auto_reply_service import AutoReplyService
from app.services.email_sender import EmailSender
import datetime

class SchedulingOrchestrator:
    """
    Coordinates the automated response flow when a lead requests a meeting.
    Steps:
    1. Generate/Fetch Booking Link
    2. Generate AI reply using thread history
    3. Send reply via EmailSender
    4. Update communication history
    """
    
    @staticmethod
    def handle_meeting_request(db: Session, reply_id: str):
        print(f"SCHEDULING_ORCHESTRATOR: Handling meeting request for reply {reply_id}")
        
        # 1. Fetch Context
        reply = db.query(EmailReply).filter(EmailReply.id == reply_id).first()
        if not reply:
            return
            
        lead = db.query(Lead).filter(Lead.id == reply.lead_id).first()
        if not lead:
            return
            
        # Get a sending account for the org
        account = db.query(SendingAccount).filter(
            SendingAccount.organization_id == lead.organization_id,
            SendingAccount.is_active == True
        ).first()
        if not account:
            print("SCHEDULING_ORCHESTRATOR: No active sending account found.")
            return

        # 2. Get Booking Link
        scheduler = MeetingSchedulerService(db)
        booking_link = scheduler.get_booking_link(str(lead.organization_id), str(account.id))
        
        # 3. Compile Thread History for AI
        thread = db.query(InboxThread).filter(InboxThread.lead_id == lead.id).order_by(InboxThread.latest_message_at.desc()).first()
        thread_history = ""
        if thread:
            messages = db.query(InboxMessage).filter(InboxMessage.thread_id == thread.id).order_by(InboxMessage.received_at.asc()).all()
            for m in messages:
                thread_history += f"{'PROSPECT' if m.direction == 'incoming' else 'SDR'}: {m.body}\n\n"
        else:
            thread_history = f"PROSPECT: {reply.content}"

        # 4. Generate AI Reply
        ai_body = AutoReplyService.generate_reply(
            db=db,
            organization_id=str(lead.organization_id),
            message_id=reply_id,
            thread_history=thread_history,
            intent=reply.intent,
            booking_link=booking_link
        )

        # 5. Send Reply
        subject = f"Re: Meeting request - {lead.company or 'Saarthi'}"
        
        # Try to find the last message-id to thread properly
        last_outbound = db.query(CampaignEmail).filter(
            CampaignEmail.lead_id == lead.id
        ).order_by(CampaignEmail.created_at.desc()).first()
        
        msg_id = EmailSender.send_email(
            account=account,
            to_email=lead.contact_email,
            subject=subject,
            body=ai_body,
            thread_msg_id=last_outbound.message_id if last_outbound else None
        )
        
        if msg_id:
            # 6. Record the outbound message in Inbox/Threads
            if not thread:
                # This should usually exist because of the webhook, but safety first
                thread = InboxThread(
                    organization_id=lead.organization_id,
                    lead_id=lead.id,
                    subject=subject,
                    status="active"
                )
                db.add(thread)
                db.flush()

            new_msg = InboxMessage(
                thread_id=thread.id,
                direction="outgoing",
                sender_email=account.email,
                sender_name="Saarthi AI Agent",
                subject=subject,
                body=ai_body,
                intent="auto_reply",
                is_processed=True
            )
            db.add(new_msg)
            
            thread.latest_message_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            print(f"SCHEDULING_ORCHESTRATOR: Automated reply sent successfully to {lead.contact_email}")
        else:
            print("SCHEDULING_ORCHESTRATOR: Failed to send automated reply.")
