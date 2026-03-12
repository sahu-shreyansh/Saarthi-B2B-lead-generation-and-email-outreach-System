import csv
import io
import uuid
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Campaign, CampaignEmail, Lead
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

class SequenceStepSchema(BaseModel):
    id: Optional[str] = None
    step_number: int
    step_type: str = "email"
    wait_days: int = 1
    template_subject: Optional[str] = None
    template_body: Optional[str] = None

class SequenceSchema(BaseModel):
    id: Optional[str] = None
    name: str
    steps: List[SequenceStepSchema] = []

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

@router.post("/{id}/upload")
async def upload_leads_csv(
    id: str,
    file: UploadFile = File(...),
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

    content = await file.read()
    decoded = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    
    # Normalization mapping
    field_map = {
        "first name": "first_name",
        "last name": "last_name",
        "email": "contact_email",
        "contact email": "contact_email",
        "title": "title",
        "job title": "title",
        "company": "company",
        "company name": "company",
        "website": "website",
        "linkedin": "linkedin_url",
        "linkedin url": "linkedin_url"
    }

    leads_count = 0
    for row in reader:
        # Normalize keys
        normalized_row = {}
        for k, v in row.items():
            if not k: continue
            clean_k = k.lower().strip()
            if clean_k in field_map:
                normalized_row[field_map[clean_k]] = v
            else:
                # Keep as metadata if not in map
                if "metadata" not in normalized_row:
                    normalized_row["metadata"] = {}
                normalized_row["metadata"][k] = v

        # Split contact_name if only full name provided
        if "contact_name" in row and row["contact_name"] and not normalized_row.get("first_name"):
            name_parts = row["contact_name"].split(" ", 1)
            normalized_row["first_name"] = name_parts[0]
            if len(name_parts) > 1:
                normalized_row["last_name"] = name_parts[1]

        # Basic validation: must have email
        if not normalized_row.get("contact_email"):
            continue

        # Create Lead
        new_lead = Lead(
            organization_id=active_org_id,
            campaign_id=camp_uuid,
            **{k: v for k, v in normalized_row.items() if k != "metadata"}
        )
        if "metadata" in normalized_row:
            new_lead.metadata_ = normalized_row["metadata"]
            
        db.add(new_lead)
        leads_count += 1

    db.commit()
    return {"message": f"Successfully uploaded {leads_count} leads", "count": leads_count}

@router.get("/{id}/sequence", response_model=Optional[SequenceSchema])
def get_campaign_sequence(
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
        
    if not camp.sequence_id:
        return None
        
    from app.database.models import Sequence, SequenceStep
    seq = db.query(Sequence).filter(Sequence.id == camp.sequence_id).first()
    if not seq:
        return None
        
    steps = db.query(SequenceStep).filter(SequenceStep.sequence_id == seq.id).order_by(SequenceStep.step_number).all()
    
    return {
        "id": str(seq.id),
        "name": seq.name,
        "steps": [
            {
                "id": str(s.id),
                "step_number": s.step_number,
                "step_type": s.step_type,
                "wait_days": s.wait_days,
                "template_subject": s.template_subject,
                "template_body": s.template_body
            } for s in steps
        ]
    }

@router.post("/{id}/sequence", response_model=SequenceSchema)
def update_campaign_sequence(
    id: str,
    schema: SequenceSchema,
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
        
    from app.database.models import Sequence, SequenceStep
    
    # Get or create sequence
    if not camp.sequence_id:
        seq = Sequence(organization_id=active_org_id, name=schema.name)
        db.add(seq)
        db.flush() # get seq.id
        camp.sequence_id = seq.id
    else:
        seq = db.query(Sequence).filter(Sequence.id == camp.sequence_id).first()
        if not seq:
             # This should not happen if data integrity is kept, but handle anyway
             seq = Sequence(organization_id=active_org_id, name=schema.name)
             db.add(seq)
             db.flush()
             camp.sequence_id = seq.id
        seq.name = schema.name
        
    # Replace steps (simplest for now)
    db.query(SequenceStep).filter(SequenceStep.sequence_id == seq.id).delete()
    
    saved_steps = []
    for step_data in schema.steps:
        new_step = SequenceStep(
            sequence_id=seq.id,
            step_number=step_data.step_number,
            step_type=step_data.step_type,
            wait_days=step_data.wait_days,
            template_subject=step_data.template_subject,
            template_body=step_data.template_body
        )
        db.add(new_step)
        saved_steps.append(new_step)
        
    db.commit()
    
    return {
        "id": str(seq.id),
        "name": seq.name,
        "steps": [
            {
                "id": str(s.id),
                "step_number": s.step_number,
                "step_type": s.step_type,
                "wait_days": s.wait_days,
                "template_subject": s.template_subject,
                "template_body": s.template_body
            } for s in saved_steps
        ]
    }
