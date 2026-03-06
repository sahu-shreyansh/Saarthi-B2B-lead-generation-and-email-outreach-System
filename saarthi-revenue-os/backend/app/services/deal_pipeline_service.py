import logging
from sqlalchemy.orm import Session
from app.database.models import Lead, LeadStageHistory
from typing import Optional

logger = logging.getLogger(__name__)

class DealPipelineService:
    """
    Kanban engine governing Lead progression.
    Validates stage transitions and injects immutable history tracking records.
    """
    
    # Strict Left-to-Right funnel order
    STAGE_ORDER = {
        "NEW": 0,
        "CONTACTED": 1,
        "INTERESTED": 2,
        "MEETING_BOOKED": 3,
        "NEGOTIATING": 4,
        "CLOSED_WON": 5,
        "CLOSED_LOST": 5 # Terminal states share level
    }

    def __init__(self, db: Session):
        self.db = db

    def change_deal_stage(self, lead: Lead, new_stage: str, changed_by: Optional[str] = None) -> bool:
        """
        Transitions the lead stage securely and tracks the history.
        """
        old_stage = lead.deal_stage
        
        if new_stage not in self.STAGE_ORDER:
            logger.error(f"[DealPipeline] Rejected strict transition: Unrecognized stage '{new_stage}'")
            return False
            
        # Optional: Apply strict forward-only rules or enable resets. We'll allow free movement 
        # for flexibility but log every single transaction strictly.
        
        logger.info(f"[DealPipeline] Transitioning Lead {lead.id} from {old_stage} -> {new_stage}")
        
        lead.deal_stage = new_stage
        self.db.add(lead)
        
        history_record = LeadStageHistory(
            org_id=lead.org_id,
            lead_id=lead.id,
            from_stage=old_stage,
            to_stage=new_stage,
            changed_by=changed_by
        )
        
        self.db.add(history_record)
        self.db.commit()
        return True
