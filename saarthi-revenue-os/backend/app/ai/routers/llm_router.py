"""
LLM Router — Centralized LLM dispatch for all AI agents.
Resolves the correct API key and model per organization.
All agents MUST call LLM exclusively through this module.
"""
import logging
import time
import json
import httpx
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session

from app.core.settings import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Saarthi platform defaults
DEFAULT_MODEL = "mistralai/mistral-7b-instruct"
SMART_MODEL = "anthropic/claude-3.5-sonnet"
FAST_MODEL = "openai/gpt-4o-mini"


def get_llm_for_org(organization_id: str, db: Session) -> Dict[str, Any]:
    """
    Resolves the LLM configuration (api_key, model) for an organization.
    - If org has their own OpenRouter key → use it with their selected model.
    - Otherwise → use Saarthi platform key with smart default.
    Returns: { "api_key": str, "model": str, "is_platform_key": bool }
    """
    from app.database.models import Organization
    from app.core.security import decrypt_string

    api_key = getattr(settings, "OPENROUTER_API_KEY", "")
    model = DEFAULT_MODEL
    is_platform_key = True

    try:
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if org and org.openrouter_api_key:
            decrypted = decrypt_string(org.openrouter_api_key)
            if decrypted:
                api_key = decrypted
                is_platform_key = False
                model = org.default_llm_model or DEFAULT_MODEL
    except Exception as e:
        logger.warning(f"[LLMRouter] Error resolving org LLM config: {e}. Falling back to platform.")

    return {
        "api_key": api_key,
        "model": model,
        "is_platform_key": is_platform_key,
    }


def call_llm(
    system_prompt: str,
    user_prompt: str,
    organization_id: str,
    db: Session,
    operation: str = "agent_call",
    max_retries: int = 2,
    temperature: float = 0.7,
    force_json: bool = True,
) -> Dict[str, Any]:
    """
    Core LLM call. Handles retries, usage logging, and structured response.
    Returns: { "content": str, "model": str, "tokens": int, "cost": float, "is_platform_key": bool }
    """
    config = get_llm_for_org(organization_id, db)
    api_key = config["api_key"]
    model = config["model"]

    if not api_key:
        logger.error("[LLMRouter] No API key available.")
        return {"content": "", "model": model, "tokens": 0, "cost": 0.0, "is_platform_key": True, "error": "no_api_key"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://saarthi.ai",
        "X-Title": "Saarthi AI Agents",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if force_json:
        payload["response_format"] = {"type": "json_object"}

    last_error = None
    for attempt in range(max_retries + 1):
        start = time.time()
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(BASE_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = prompt_tokens + completion_tokens
            latency_ms = int((time.time() - start) * 1000)

            # Cost estimate
            if "claude" in model.lower():
                cost = (prompt_tokens / 1_000_000) * 3.0 + (completion_tokens / 1_000_000) * 15.0
            else:
                cost = (prompt_tokens / 1_000_000) * 0.15 + (completion_tokens / 1_000_000) * 0.60

            # Log to existing system
            _log_usage(
                db=db,
                org_id=organization_id,
                operation=operation,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                cost_estimate=cost,
                is_platform_key=config["is_platform_key"],
            )

            return {
                "content": content,
                "model": model,
                "tokens": total_tokens,
                "cost": cost,
                "is_platform_key": config["is_platform_key"],
            }

        except Exception as e:
            last_error = str(e)
            logger.warning(f"[LLMRouter] Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries:
                time.sleep(1)

    logger.error(f"[LLMRouter] All {max_retries + 1} attempts failed. Last error: {last_error}")
    return {"content": "", "model": model, "tokens": 0, "cost": 0.0, "is_platform_key": config["is_platform_key"], "error": last_error}


def _log_usage(
    db: Session, org_id: str, operation: str, model: str,
    prompt_tokens: int, completion_tokens: int, total_tokens: int,
    latency_ms: int, cost_estimate: float, is_platform_key: bool
):
    """Reuses the existing AiUsageLog pattern."""
    from app.database.models import Organization, AiUsageLog
    try:
        if is_platform_key:
            org = db.query(Organization).filter(Organization.id == org_id).first()
            if org:
                org.ai_usage_tokens = (org.ai_usage_tokens or 0) + total_tokens
                db.flush()

        log = AiUsageLog(
            organization_id=org_id,
            operation=operation,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost_estimate=cost_estimate,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"[LLMRouter] Failed to log usage: {e}")
        db.rollback()
