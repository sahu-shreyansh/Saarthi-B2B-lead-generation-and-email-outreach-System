import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database.database import get_db
from app.core.deps import get_current_user_and_org
from app.database.models import Lead

router = APIRouter(prefix="/intelligence", tags=["AI Intelligence"])

class ScoreRequest(BaseModel):
    lead_id: str

@router.post("/score")
def score_lead_endpoint(
    req: ScoreRequest,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """
    Triggers the autonomous AI scoring pipeline for a single lead.
    """
    current_user, active_org_id, role = deps
    
    try:
        lead_uuid = uuid.UUID(req.lead_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Lead ID")
    
    # Verify lead exists and belongs to org
    lead = db.query(Lead).filter(Lead.id == lead_uuid, Lead.organization_id == active_org_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    # Kick off celery task
    from app.tasks.lead_pipeline import score_lead_task
    task = score_lead_task.delay(str(lead.id))
    
    return {"message": "AI Scoring Pipeline started", "task_id": str(task.id)}

@router.post("/enrich")
def enrich_lead_endpoint(
    req: ScoreRequest,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """
    Triggers the data enrichment pipeline for a single lead.
    """
    current_user, active_org_id, role = deps
    
    try:
        lead_uuid = uuid.UUID(req.lead_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Lead ID")
    
    lead = db.query(Lead).filter(Lead.id == lead_uuid, Lead.organization_id == active_org_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    # Kick off celery task
    from app.tasks.lead_pipeline import extract_metadata_task
    task = extract_metadata_task.delay(str(lead.id))
    
    return {"message": "AI Enrichment Pipeline started", "task_id": str(task.id)}

@router.get("/score/{lead_id}")
def get_score(
    lead_id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """
    Retrieves the latest AI score and enrichment data for a lead.
    """
    current_user, active_org_id, role = deps
    try:
        lead_uuid = uuid.UUID(lead_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Lead ID")
        
    lead = db.query(Lead).filter(Lead.id == lead_uuid, Lead.organization_id == active_org_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get the latest score entry from lead_scores table
    from app.database.models import LeadScore
    latest_score = db.query(LeadScore).filter(
        LeadScore.lead_id == lead_uuid
    ).order_by(LeadScore.created_at.desc()).first()
    
    return {
        "lead_id": str(lead.id),
        "score": latest_score.score if latest_score else lead.score,
        "factors": latest_score.factors if latest_score else {},
        "created_at": latest_score.created_at.isoformat() if latest_score else None
    }
