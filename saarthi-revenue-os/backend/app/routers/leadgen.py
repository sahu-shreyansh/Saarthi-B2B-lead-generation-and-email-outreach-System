import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.core.deps import get_current_user_and_org
from app.database.models import User, LeadGenerationJob
from app.workers.leadgen_worker import run_lead_generation_task
from app.services.billing import UsageService
import uuid as _uuid

router = APIRouter(prefix="/leadgen", tags=["Lead Generation"])

class LeadGenRequest(BaseModel):
    campaign_id: str
    industry: str
    location: str
    # Provider routing: "maps" | "linkedin" | "website" | "google_search"
    query_type: str = "maps"
    # Override the search query (defaults to industry + location)
    query: Optional[str] = None
    company_size: str = "Any"
    require_domain: bool = True
    max_leads: int = 50
    max_pages: int = 1
    include_linkedin: bool = False
    include_google_maps: bool = True
    ai_score: bool = False

@router.post("/start")
async def start_lead_generation(
    req: LeadGenRequest, 
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """
    Kicks off the async Lead Generation Celery task.
    Routes to Apify (maps/linkedin/website) or SERP (google_search)
    based on query_type.
    """
    from app.services.leadgen_service import APIFY_TYPES, SERP_TYPES

    current_user, active_org_id, role = deps

    valid_types = APIFY_TYPES | SERP_TYPES
    if req.query_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid query_type. Valid: {sorted(valid_types)}"
        )

    # Build the search query if not explicitly provided
    auto_query = req.query or f"{req.industry} companies in {req.location}"

    # Pre-flight Cost Guardrail
    estimated_cost = req.max_leads
    remaining_credits = UsageService.get_remaining_credits(db, active_org_id)
    
    if estimated_cost > remaining_credits:
        raise HTTPException(
            status_code=402, 
            detail=f"Insufficient credits. Extraction requires {estimated_cost} credits, but org only has {remaining_credits} remaining."
        )

    try:
        camp_uuid = uuid.UUID(req.campaign_id)
        job = LeadGenerationJob(
            organization_id=active_org_id,
            campaign_id=camp_uuid,
            total_requested=req.max_leads,
            status="PENDING",
            meta={
                "query_type": req.query_type,
                "query": auto_query,
                "max_pages": req.max_pages,
                "location": req.location,
                "industry": req.industry
            }
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Trigger Celery Worker — Passing org_id for BYODB routing
        run_lead_generation_task.delay(str(job.id), str(active_org_id))

        return {"job_id": str(job.id), "status": "QUEUED", "query_type": req.query_type, "query": auto_query}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Campaign ID")


@router.get("/jobs")
async def get_jobs_for_campaign(
    campaign_id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """
    Fetch all lead generation jobs for a campaign.
    """
    current_user, active_org_id, role = deps
    try:
        camp_uuid = uuid.UUID(campaign_id)
        jobs = db.query(LeadGenerationJob).filter(
            LeadGenerationJob.organization_id == active_org_id,
            LeadGenerationJob.campaign_id == camp_uuid
        ).order_by(LeadGenerationJob.created_at.desc()).all()
        return jobs
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Campaign ID")


@router.get("/job/{job_id}")
async def get_leadgen_status(
    job_id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """
    Deprecated polling endpoint. Tasks are now checked via /tasks/{task_id}
    """
    raise HTTPException(status_code=301, detail="Use /tasks/{task_id} for pipeline updates")
