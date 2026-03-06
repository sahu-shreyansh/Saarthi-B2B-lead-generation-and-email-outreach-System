import logging
from sqlalchemy.orm import Session
from app.database.models import CalendarSync, SendingAccount
import uuid

logger = logging.getLogger(__name__)

class MeetingSchedulerService:
    """
    Abstracts calendar link generation. If CalendarSync exists for the org, 
    we append standard Cal.com/Calendly dynamic links.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def get_booking_link(self, org_id: str, sending_account_id: str) -> str:
        """
        Fetch the primary booking calendar link.
        Normally, this routes to a synced Cal.com or Google Calendar Oauth routing link.
        """
        # Example Implementation retrieving configured org default string:
        sync_record = self.db.query(CalendarSync).filter_by(org_id=org_id).first()
        
        if sync_record and sync_record.last_sync_token:
            # Construct a dynamic backend proxy link that redirects to OAuth calendar
            link = f"https://saarthi.ai/book/{org_id}/{sending_account_id}"
            logger.info(f"[MeetingScheduler] Generated proxy link: {link}")
            return link
            
        logger.warning("[MeetingScheduler] No active CalendarSync found. Using generic placeholder.")
        return "https://cal.com/meeting"
