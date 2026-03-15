"""
AI Pipeline — Orchestration layer that runs agents in sequence.
This is the single entry point for all email generation and reply classification.
"""
import logging
import json
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.ai.services.context_builder import build_email_context, build_lead_context, build_company_context
from app.ai.agents.signal_agent import SignalAgent
from app.ai.agents.classifier_agent import ClassifierAgent
from app.ai.agents.email_agent import EmailAgent
from app.ai.agents.reply_classifier import ReplyClassifier

logger = logging.getLogger(__name__)


def _save_output(
    db: Session,
    organization_id: str,
    lead_id: Optional[str],
    agent_type: str,
    prompt_version: str,
    mode: str,
    output: Dict[str, Any],
) -> None:
    """Persists agent output to ai_outputs table."""
    from app.database.models import AiOutput
    try:
        meta = output.pop("_meta", {})
        record = AiOutput(
            organization_id=uuid.UUID(organization_id),
            lead_id=uuid.UUID(lead_id) if lead_id else None,
            agent_type=agent_type,
            prompt_version=prompt_version,
            mode=mode,
            model_used=meta.get("model_used"),
            tokens_used=meta.get("tokens_used", 0),
            cost_estimate=meta.get("cost_estimate", 0.0),
            response_json=output,
            status=meta.get("status", "success"),
        )
        db.add(record)
        db.commit()
        logger.info(f"[Pipeline] Saved {agent_type} output for lead {lead_id}")
    except Exception as e:
        logger.error(f"[Pipeline] Failed to save output: {e}")
        db.rollback()


def run_email_pipeline(
    lead_id: str,
    organization_id: str,
    db: Session,
    mode: str = "normal",
    services: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Runs the full email generation pipeline for a lead.

    Modes:
    - "normal": Uses EmailAgent (paragraph services, single call)
    - "classifier": Uses ClassifierAgent (scored JSON services, single call)

    Flow: Context Builder → Agent → AiOutput storage → return result
    """
    from app.database.models import Lead, Organization

    # 1. Fetch lead and org
    try:
        lead = db.query(Lead).filter(Lead.id == uuid.UUID(lead_id)).first()
        org = db.query(Organization).filter(Organization.id == uuid.UUID(organization_id)).first()
        if not lead or not org:
            logger.error(f"[Pipeline] Lead {lead_id} or Org {organization_id} not found.")
            return {"error": "lead_or_org_not_found"}
    except Exception as e:
        logger.error(f"[Pipeline] DB fetch failed: {e}")
        return {"error": str(e)}

    # 2. Build context
    services_list = services or []
    context = build_email_context(lead, org, services_list)

    # 3. Run agent
    if mode == "classifier":
        agent = ClassifierAgent(organization_id=organization_id, db=db)
        result = agent.run(context)
        prompt_version = "classifier_v1"
    else:
        agent = EmailAgent(organization_id=organization_id, db=db)
        result = agent.run(context)
        prompt_version = "normal_agent_v1"

    # 4. Persist
    _save_output(
        db=db,
        organization_id=organization_id,
        lead_id=lead_id,
        agent_type="email_pipeline",
        prompt_version=prompt_version,
        mode=mode,
        output=dict(result),  # copy so _meta pop doesn't mutate the return
    )

    return result


def run_signal_extraction(
    lead_id: str,
    organization_id: str,
    db: Session,
) -> Dict[str, Any]:
    """Runs signal extraction only (no email writing)."""
    from app.database.models import Lead, Organization

    try:
        lead = db.query(Lead).filter(Lead.id == uuid.UUID(lead_id)).first()
        org = db.query(Organization).filter(Organization.id == uuid.UUID(organization_id)).first()
        if not lead or not org:
            return {"error": "lead_or_org_not_found"}
    except Exception as e:
        return {"error": str(e)}

    context = build_lead_context(lead, org)
    agent = SignalAgent(organization_id=organization_id, db=db)
    result = agent.run(context)

    _save_output(
        db=db,
        organization_id=organization_id,
        lead_id=lead_id,
        agent_type="signal",
        prompt_version="signal_v1",
        mode="signal_only",
        output=dict(result),
    )

    return result


def run_reply_classification(
    reply_id: str,
    organization_id: str,
    db: Session,
) -> Dict[str, Any]:
    """Runs reply classification and updates EmailReply.intent."""
    from app.database.models import EmailReply

    try:
        reply = db.query(EmailReply).filter(
            EmailReply.id == uuid.UUID(reply_id)
        ).first()
        if not reply:
            return {"error": "reply_not_found"}

        reply_body = reply.content or ""
    except Exception as e:
        logger.error(f"[Pipeline] Failed to fetch reply {reply_id}: {e}")
        return {"error": str(e)}

    context = {"reply_body": reply_body}
    agent = ReplyClassifier(organization_id=organization_id, db=db)
    result = agent.run_and_update_db(reply_id=reply_id, context=context)

    _save_output(
        db=db,
        organization_id=organization_id,
        lead_id=str(reply.lead_id) if reply.lead_id else None,
        agent_type="reply_classifier",
        prompt_version="reply_classifier_v1",
        mode="reply",
        output=dict(result),
    )

    return result
