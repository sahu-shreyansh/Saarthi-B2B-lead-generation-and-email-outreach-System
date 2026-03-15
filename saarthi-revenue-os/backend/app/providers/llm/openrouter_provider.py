import logging
import time
import httpx
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.database.models import AiUsageLog

logger = logging.getLogger(__name__)

class OpenRouterError(Exception):
    pass

class OpenRouterProvider:
    """
    Centralized API pipeline for all LLM calls.
    Enforces master models, fallback logic, and SQL logging.
    """
    
    PRIMARY_MODEL = "anthropic/claude-3.5-sonnet"
    FAST_MODEL = "openai/gpt-4o-mini"
    CLASSIFICATION_MODEL = "openai/gpt-4o-mini"
    
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, db: Session):
        self.db = db
        self.api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        if not self.api_key:
            logger.warning("[OpenRouter] OPENROUTER_API_KEY is not set globally.")

    def generate(
        self,
        prompt_type: str,
        system_prompt: str,
        user_prompt: str,
        org_id: str,
        campaign_id: Optional[str] = None,
        use_fast_model: bool = False,
        is_classification: bool = False,
        default_fallback: str = "NEUTRAL",
        max_retries: int = 2,
    ) -> str:
        """
        Executes strict AI pipeline: Service -> Prompt -> Provider -> Model -> Result
        """
        from app.database.models import Organization
        from app.core.security import decrypt_string

        # 1. Resolve Credentials and Model
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        
        api_key = self.api_key # Platform default
        using_platform_key = True
        
        custom_model = None
        if org and org.openrouter_api_key:
            decrypted_key = decrypt_string(org.openrouter_api_key)
            if decrypted_key:
                api_key = decrypted_key
                using_platform_key = False
                custom_model = org.default_llm_model

        # 2. Model Selection
        if custom_model:
            target_model = custom_model
        else:
            target_model = self.FAST_MODEL if use_fast_model else self.PRIMARY_MODEL
            if is_classification:
                target_model = self.CLASSIFICATION_MODEL

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://saarthi.ai",
            "X-Title": "Saarthi Revenue OS",
            "Content-Type": "application/json"
        }

        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }

        for attempt in range(max_retries + 1):
            start_time = time.time()
            try:
                # Execution
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(self.BASE_URL, headers=headers, json=payload)
                    resp.raise_for_status()
                    
                    data = resp.json()
                    result = data["choices"][0]["message"]["content"].strip()
                    
                    usage = data.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
                    
                    latency = int((time.time() - start_time) * 1000)
                    
                    # Cost Estimate (Simplified for demonstration)
                    cost_estimate = 0.0
                    if "claude" in target_model.lower():
                        cost_estimate = (prompt_tokens / 1_000_000) * 3.0 + (completion_tokens / 1_000_000) * 15.0
                    else:
                        cost_estimate = (prompt_tokens / 1_000_000) * 0.15 + (completion_tokens / 1_000_000) * 0.60
                    
                    self._log_usage(
                        org_id=org_id,
                        campaign_id=campaign_id,
                        prompt_type=prompt_type,
                        model=target_model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        latency=latency,
                        cost_estimate=cost_estimate,
                        request_id=data.get("id"),
                        is_platform_key=using_platform_key
                    )
                    
                    return result
            
            except Exception as e:
                logger.warning(f"[OpenRouter] Attempt {attempt+1} failed targeting {target_model}: {str(e)}")
                if attempt == max_retries:
                    # Final exhaustion
                    logger.error(f"[OpenRouter] Total failure on {prompt_type}. Falling back to default: {default_fallback}")
                    return default_fallback
                else:
                    # Switch to fast model if primary collapsed (only if not using custom model)
                    if not custom_model and target_model == self.PRIMARY_MODEL:
                        logger.warning(f"[OpenRouter] Falling back to {self.FAST_MODEL}")
                        target_model = self.FAST_MODEL
                        payload["model"] = target_model
                    
                    time.sleep(1) # Slight pause between fast retries

    def _log_usage(
        self, 
        org_id: str, 
        campaign_id: Optional[str], 
        prompt_type: str, 
        model: str, 
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int, 
        latency: int,
        cost_estimate: float = 0.0,
        request_id: Optional[str] = None,
        is_platform_key: bool = True
    ):
        """Standard AI Observability."""
        from app.database.models import Organization
        
        # 1. Update Organization Usage if using platform key
        if is_platform_key:
            try:
                org = self.db.query(Organization).filter(Organization.id == org_id).first()
                if org:
                    org.ai_usage_tokens += total_tokens
                    self.db.flush() 
            except Exception as e:
                logger.error(f"Failed to update org usage: {str(e)}")

        # 2. Log Entry
        log_entry = AiUsageLog(
            organization_id=org_id,
            operation=prompt_type,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency,
            cost_estimate=cost_estimate,
            request_id=request_id,
            metadata_={"campaign_id": campaign_id} if campaign_id else {}
        )
        try:
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log AI Usage: {str(e)}")
