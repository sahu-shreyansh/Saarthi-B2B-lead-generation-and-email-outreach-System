import uuid
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database.database import get_db
from app.database.models import Lead
from app.core.deps import get_current_user_and_org

router = APIRouter(prefix="/leads", tags=["Leads"])

class LeadCreate(BaseModel):
    company_name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    score: Optional[int] = 0
    status: Optional[str] = "new"
    source: Optional[str] = "manual"
    metadata: Optional[Dict[str, Any]] = {}

class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    score: Optional[int] = None
    status: Optional[str] = None
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class LeadResponse(LeadCreate):
    id: str
    organization_id: str

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
    
    response_data = {
        "id": str(new_lead.id),
        "organization_id": str(new_lead.organization_id),
        "company_name": new_lead.company_name,
        "website": new_lead.website,
        "industry": new_lead.industry,
        "location": new_lead.location,
        "description": new_lead.description,
        "contact_name": new_lead.contact_name,
        "contact_email": new_lead.contact_email,
        "score": new_lead.score,
        "status": new_lead.status,
        "source": new_lead.source,
        "metadata": new_lead.metadata_
    }
    return response_data

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
    
    responses = []
    for lead in created_leads:
        responses.append({
            "id": str(lead.id),
            "organization_id": str(lead.organization_id),
            "company_name": lead.company_name,
            "website": lead.website,
            "industry": lead.industry,
            "location": lead.location,
            "description": lead.description,
            "contact_name": lead.contact_name,
            "contact_email": lead.contact_email,
            "score": lead.score,
            "status": lead.status,
            "source": lead.source,
            "metadata": lead.metadata_
        })
    return responses


@router.get("", response_model=List[LeadResponse])
def list_leads(
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
    
    return [
        {
            "id": str(l.id),
            "organization_id": str(l.organization_id),
            "company_name": l.company_name,
            "website": l.website,
            "industry": l.industry,
            "location": l.location,
            "description": l.description,
            "contact_name": l.contact_name,
            "contact_email": l.contact_email,
            "score": l.score,
            "status": l.status,
            "source": l.source,
            "metadata": l.metadata_
        } for l in leads
    ]

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
        
    return {
        "id": str(lead.id),
        "organization_id": str(lead.organization_id),
        "company_name": lead.company_name,
        "website": lead.website,
        "industry": lead.industry,
        "location": lead.location,
        "description": lead.description,
        "contact_name": lead.contact_name,
        "contact_email": lead.contact_email,
        "score": lead.score,
        "status": lead.status,
        "source": lead.source,
        "metadata": lead.metadata_
    }

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
    
    return {
        "id": str(lead.id),
        "organization_id": str(lead.organization_id),
        "company_name": lead.company_name,
        "website": lead.website,
        "industry": lead.industry,
        "location": lead.location,
        "description": lead.description,
        "contact_name": lead.contact_name,
        "contact_email": lead.contact_email,
        "score": lead.score,
        "status": lead.status,
        "source": lead.source,
        "metadata": lead.metadata_
    }

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
