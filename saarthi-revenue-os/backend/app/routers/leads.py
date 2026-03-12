import uuid
from datetime import datetime
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database.database import get_db
from app.database.models import Lead
from app.core.deps import get_current_user_and_org

router = APIRouter(prefix="/leads", tags=["Leads"])

class LeadCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    email_verified: Optional[bool] = False
    title: Optional[str] = None
    company: Optional[str] = None
    company_name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    score: Optional[int] = 0
    status: Optional[str] = "pending"
    current_step_number: Optional[int] = 0
    next_action_at: Optional[datetime] = None
    source: Optional[str] = "manual"
    metadata: Optional[Dict[str, Any]] = Field(default={}, alias="metadata_")

class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    email_verified: Optional[bool] = None
    title: Optional[str] = None
    company: Optional[str] = None
    company_name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    score: Optional[int] = None
    status: Optional[str] = None
    current_step_number: Optional[int] = None
    next_action_at: Optional[datetime] = None
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata_")

class LeadResponse(LeadCreate):
    id: uuid.UUID
    organization_id: uuid.UUID
    campaign_id: Optional[uuid.UUID] = None
    
    model_config = {"from_attributes": True, "populate_by_name": True}

class BulkLeadCreate(BaseModel):
    leads: List[LeadCreate]


@router.post("", response_model=LeadResponse)
def create_lead(
    schema: LeadCreate,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    
    lead_data = schema.model_dump()
    lead_data['metadata_'] = lead_data.pop('metadata', {})
    
    new_lead = Lead(organization_id=active_org_id, **lead_data)
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    
    return new_lead

@router.post("/bulk-create", response_model=List[LeadResponse])
def bulk_create_leads(
    schema: BulkLeadCreate,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    created_leads = []
    
    for lead_item in schema.leads:
        lead_data = lead_item.model_dump()
        lead_data['metadata_'] = lead_data.pop('metadata', {})
        new_lead = Lead(organization_id=active_org_id, **lead_data)
        db.add(new_lead)
        created_leads.append(new_lead)
        
    db.commit()
    
    return created_leads


@router.get("", response_model=List[LeadResponse])
def list_leads(
    campaign_id: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    score_min: Optional[int] = Query(None),
    score_max: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0, 
    limit: int = 100,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    query = db.query(Lead).filter(Lead.organization_id == active_org_id)
    
    if campaign_id:
        try:
            camp_uuid = uuid.UUID(campaign_id)
            query = query.filter(Lead.campaign_id == camp_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Campaign ID")

    if industry:
        query = query.filter(Lead.industry.ilike(f"%{industry}%"))
    if status:
        query = query.filter(Lead.status == status)
    if score_min is not None:
        query = query.filter(Lead.score >= score_min)
    if score_max is not None:
        query = query.filter(Lead.score <= score_max)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                Lead.company_name.ilike(search_fmt),
                Lead.contact_name.ilike(search_fmt),
                Lead.contact_email.ilike(search_fmt)
            )
        )
            
    leads = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()
    return leads

@router.get("/{id}", response_model=LeadResponse)
def get_lead(
    id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    
    try:
        lead_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Lead ID")
        
    lead = db.query(Lead).filter(Lead.id == lead_uuid, Lead.organization_id == active_org_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    return lead

@router.patch("/{id}", response_model=LeadResponse)
def update_lead(
    id: str,
    schema: LeadUpdate,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        lead_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Lead ID")
        
    lead = db.query(Lead).filter(Lead.id == lead_uuid, Lead.organization_id == active_org_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    update_data = schema.model_dump(exclude_unset=True)
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")
        
    for key, value in update_data.items():
        setattr(lead, key, value)
        
    db.commit()
    db.refresh(lead)
    
    return lead

@router.delete("/{id}")
def delete_lead(
    id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        lead_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Lead ID")
        
    lead = db.query(Lead).filter(Lead.id == lead_uuid, Lead.organization_id == active_org_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    db.delete(lead)
    db.commit()
    return {"message": "Lead deleted successfully"}
