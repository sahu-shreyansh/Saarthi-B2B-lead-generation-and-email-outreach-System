"""
Usage Guard — Callable quota enforcement for AI agent calls.
Use this BEFORE every LLM request inside an agent.
"""
import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def check_quota(organization_id: str, db: Session) -> None:
    """
    Raises HTTP 402 if the organization has exceeded its platform AI quota.
    Quota is bypassed if the org has connected their own OpenRouter API key.

    Usage:
        check_quota(org_id, db)  # raises if over limit
    """
    from app.database.models import Organization

    try:
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            logger.warning(f"[UsageGuard] Org {organization_id} not found — allowing request.")
            return

        # BYO Key: org pays their own bill, no platform limit
        if org.openrouter_api_key:
            return

        # Platform free tier check
        if (org.ai_usage_tokens or 0) >= (org.ai_usage_limit or 50000):
            raise HTTPException(
                status_code=402,
                detail={
                    "detail": "Free AI quota exceeded. Connect your OpenRouter API key in Settings → Integrations to continue.",
                    "code": "AI_QUOTA_EXCEEDED",
                    "tokens_used": org.ai_usage_tokens,
                    "tokens_limit": org.ai_usage_limit,
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        # Don't block on guard failure — log and proceed
        logger.error(f"[UsageGuard] Error checking quota for {organization_id}: {e}")
