import time
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger
import openai

from app.database.models import AiUsageLog

# Estimated costs per 1K tokens (as of avg standard models)
PRICING = {
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
}

class AIObservability:
    @staticmethod
    def log_usage(
        db: Session,
        organization_id: str,
        operation: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AiUsageLog:
        """
        Calculates cost and logs AI usage to the database for billing/tracking.
        """
        # Calculate cost
        pricing = PRICING.get(model, PRICING["gpt-4o-mini"]) # default to mini pricing if unknown
        cost_estimate = (prompt_tokens / 1000.0) * pricing["prompt"] + (completion_tokens / 1000.0) * pricing["completion"]

        log_entry = AiUsageLog(
            organization_id=organization_id,
            operation=operation,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_estimate=cost_estimate,
            latency_ms=latency_ms,
            request_id=request_id,
            metadata_=metadata or {}
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        logger.info(f"AI Usage logged [{operation}]: {prompt_tokens + completion_tokens} tokens, ${cost_estimate:.4f}, {latency_ms}ms")
        return log_entry
