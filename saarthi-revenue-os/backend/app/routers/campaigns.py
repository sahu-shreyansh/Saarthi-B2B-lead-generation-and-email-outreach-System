import uuid
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Campaign, CampaignEmail
from app.core.deps import get_current_user_and_org

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

class CampaignCreate(BaseModel):
    name: str
    target_score: Optional[int] = 50
    email_template: Optional[str] = None
    daily_limit: Optional[int] = 100

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    target_score: Optional[int] = None
    email_template: Optional[str] = None
    daily_limit: Optional[int] = None
    status: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None

class CampaignResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    target_score: int
    email_template: Optional[str]
    daily_limit: int
    status: str
    stats: Dict[str, Any]
    created_at: str
    updated_at: str

class CampaignEmailResponse(BaseModel):
    id: str
    campaign_id: str
    lead_id: str
    subject: Optional[str]
    body: Optional[str]
    status: str
    sent_at: Optional[str]
    created_at: str

@router.post("", response_model=CampaignResponse)
def create_campaign(
    schema: CampaignCreate,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    
    camp = Campaign(
        organization_id=active_org_id,
        name=schema.name,
        target_score=schema.target_score,
        email_template=schema.email_template,
        daily_limit=schema.daily_limit,
        status="draft",
        stats={"sent": 0, "opened": 0, "clicked": 0, "replied": 0}
    )
    db.add(camp)
    db.commit()
    db.refresh(camp)
    
    return {
        "id": str(camp.id),
        "organization_id": str(camp.organization_id),
        "name": camp.name,
        "target_score": camp.target_score,
        "email_template": camp.email_template,
        "daily_limit": camp.daily_limit,
        "status": camp.status,
        "stats": camp.stats,
        "created_at": camp.created_at.isoformat(),
        "updated_at": camp.updated_at.isoformat()
    }

@router.get("", response_model=List[CampaignResponse])
def list_campaigns(
    skip: int = 0, limit: int = 100,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    campaigns = db.query(Campaign).filter(Campaign.organization_id == active_org_id).order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(c.id),
            "organization_id": str(c.organization_id),
            "name": c.name,
            "target_score": c.target_score,
            "email_template": c.email_template,
            "daily_limit": c.daily_limit,
            "status": c.status,
            "stats": c.stats,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat()
        } for c in campaigns
    ]

@router.get("/{id}", response_model=CampaignResponse)
def get_campaign(
    id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        camp_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Campaign ID")
        
    camp = db.query(Campaign).filter(Campaign.id == camp_uuid, Campaign.organization_id == active_org_id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    return {
        "id": str(camp.id),
        "organization_id": str(camp.organization_id),
        "name": camp.name,
        "target_score": camp.target_score,
        "email_template": camp.email_template,
        "daily_limit": camp.daily_limit,
        "status": camp.status,
        "stats": camp.stats,
        "created_at": camp.created_at.isoformat(),
        "updated_at": camp.updated_at.isoformat()
    }

@router.patch("/{id}", response_model=CampaignResponse)
def update_campaign(
    id: str,
    schema: CampaignUpdate,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        camp_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Campaign ID")
        
    camp = db.query(Campaign).filter(Campaign.id == camp_uuid, Campaign.organization_id == active_org_id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    update_data = schema.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(camp, key, value)
        
    db.commit()
    db.refresh(camp)
    
    return {
        "id": str(camp.id),
        "organization_id": str(camp.organization_id),
        "name": camp.name,
        "target_score": camp.target_score,
        "email_template": camp.email_template,
        "daily_limit": camp.daily_limit,
        "status": camp.status,
        "stats": camp.stats,
        "created_at": camp.created_at.isoformat(),
        "updated_at": camp.updated_at.isoformat()
    }

@router.post("/{id}/start")
def start_campaign(
    id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        camp_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Campaign ID")
        
    camp = db.query(Campaign).filter(Campaign.id == camp_uuid, Campaign.organization_id == active_org_id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    camp.status = "active"
    db.commit()
    
    camp.status = "active"
    db.commit()
    
    # Use PipelineOrchestrator instead of direct delay
    from app.services.pipeline_orchestrator import PipelineOrchestrator
    task_id = PipelineOrchestrator.start_campaign(db, str(camp.id))
    
    return {"message": "Campaign started", "task_id": task_id}

@router.post("/{id}/pause")
def pause_campaign(
    id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        camp_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Campaign ID")
        
    camp = db.query(Campaign).filter(Campaign.id == camp_uuid, Campaign.organization_id == active_org_id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    camp.status = "paused"
    db.commit()
    
    return {"message": "Campaign paused"}

@router.get("/{id}/emails", response_model=List[CampaignEmailResponse])
def list_campaign_emails(
    id: str,
    skip: int = 0, limit: int = 100,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        camp_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Campaign ID")
        
    # verify ownership
    camp = db.query(Campaign).filter(Campaign.id == camp_uuid, Campaign.organization_id == active_org_id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    emails = db.query(CampaignEmail).filter(CampaignEmail.campaign_id == camp_uuid).order_by(CampaignEmail.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(e.id),
            "campaign_id": str(e.campaign_id),
            "lead_id": str(e.lead_id),
            "subject": e.subject,
            "body": e.body,
            "status": e.status,
            "sent_at": e.sent_at.isoformat() if e.sent_at else None,
            "created_at": e.created_at.isoformat()
        } for e in emails
    ]

@router.get("/{id}/stats")
def get_campaign_stats(
    id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        camp_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Campaign ID")
        
    camp = db.query(Campaign).filter(Campaign.id == camp_uuid, Campaign.organization_id == active_org_id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    return camp.stats
