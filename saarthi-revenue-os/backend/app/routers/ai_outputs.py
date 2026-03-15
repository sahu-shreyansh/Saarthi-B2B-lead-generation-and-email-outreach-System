"""
AI Outputs Router — Read-only API for agent results + trigger endpoints.
Existing routes are NOT touched.
"""
import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database.database import get_db
from app.database.models import AiOutput
from app.core.deps import get_current_user_and_org, get_current_org_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Agents"])


# ── Request Schemas ─────────────────────────────────────────────

class GenerateEmailRequest(BaseModel):
    lead_id: str
    mode: str = "normal"  # normal | classifier
    services: Optional[List[dict]] = []


class ClassifyReplyRequest(BaseModel):
    reply_id: str


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/generate-email")
async def trigger_email_generation(
    body: GenerateEmailRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    deps=Depends(get_current_user_and_org),
    db: Session = Depends(get_db),
):
    """
    Triggers background email generation for a lead.
    Returns immediately — result is stored in ai_outputs table.
    """
    _, org_id, _ = deps

    from app.workers.ai_worker import generate_email_for_lead_task
    task = generate_email_for_lead_task.apply_async(
        kwargs={
            "lead_id": body.lead_id,
            "organization_id": str(org_id),
            "mode": body.mode,
            "services": body.services or [],
        },
        queue="ai",
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "lead_id": body.lead_id,
        "mode": body.mode,
    }


@router.post("/generate-email/sync")
def generate_email_sync(
    body: GenerateEmailRequest,
    deps=Depends(get_current_user_and_org),
    db: Session = Depends(get_db),
):
    """
    Synchronous email generation — returns result immediately.
    Use for single leads where you need the output right now.
    """
    _, org_id, _ = deps

    from app.ai.services.ai_pipeline import run_email_pipeline
    result = run_email_pipeline(
        lead_id=body.lead_id,
        organization_id=str(org_id),
        db=db,
        mode=body.mode,
        services=body.services or [],
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/classify-reply")
def classify_reply(
    body: ClassifyReplyRequest,
    deps=Depends(get_current_user_and_org),
    db: Session = Depends(get_db),
):
    """
    Synchronously classifies an email reply and updates its intent.
    """
    _, org_id, _ = deps

    from app.ai.services.ai_pipeline import run_reply_classification
    result = run_reply_classification(
        reply_id=body.reply_id,
        organization_id=str(org_id),
        db=db,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/outputs/{lead_id}")
def get_ai_outputs_for_lead(
    lead_id: str,
    agent_type: Optional[str] = None,
    limit: int = 10,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    """Returns all stored AI agent outputs for a specific lead."""
    try:
        query = db.query(AiOutput).filter(
            AiOutput.organization_id == org_id,
            AiOutput.lead_id == uuid.UUID(lead_id),
        )
        if agent_type:
            query = query.filter(AiOutput.agent_type == agent_type)

        outputs = query.order_by(AiOutput.created_at.desc()).limit(limit).all()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return [
        {
            "id": str(o.id),
            "agent_type": o.agent_type,
            "prompt_version": o.prompt_version,
            "mode": o.mode,
            "model_used": o.model_used,
            "tokens_used": o.tokens_used,
            "status": o.status,
            "response_json": o.response_json,
            "created_at": o.created_at.isoformat(),
        }
        for o in outputs
    ]


@router.get("/outputs")
def get_ai_outputs_for_org(
    agent_type: Optional[str] = None,
    limit: int = 20,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    """Returns the latest AI agent outputs for the organization."""
    query = db.query(AiOutput).filter(AiOutput.organization_id == org_id)
    if agent_type:
        query = query.filter(AiOutput.agent_type == agent_type)

    outputs = query.order_by(AiOutput.created_at.desc()).limit(limit).all()
    return [
        {
            "id": str(o.id),
            "lead_id": str(o.lead_id) if o.lead_id else None,
            "agent_type": o.agent_type,
            "prompt_version": o.prompt_version,
            "mode": o.mode,
            "model_used": o.model_used,
            "tokens_used": o.tokens_used,
            "status": o.status,
            "created_at": o.created_at.isoformat(),
        }
        for o in outputs
    ]
