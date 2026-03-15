"""
BaseAgent — Abstract interface that all Saarthi AI Agents implement.
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.ai.routers.llm_router import call_llm
from app.ai.guards.usage_guard import check_quota

logger = logging.getLogger(__name__)

PROMPT_VERSION_MAP: Dict[str, str] = {
    "signal": "signal_v1",
    "classifier": "classifier_v1",
    "email_normal": "normal_agent_v1",
    "email_classifier": "classifier_agent_v1",
    "reply": "reply_classifier_v1",
}


class BaseAgent(ABC):
    """
    Every Saarthi AI agent must extend this class.
    Provides: quota checking, LLM routing, JSON parsing, fallback handling.
    """

    agent_type: str = "base"
    prompt_version: str = "base_v1"

    def __init__(self, organization_id: str, db: Session):
        self.organization_id = organization_id
        self.db = db

    @abstractmethod
    def _build_prompt(self, context: Dict[str, Any]) -> tuple[str, str]:
        """Return (system_prompt, user_prompt) for this agent."""
        pass

    @abstractmethod
    def _parse_response(self, raw: str) -> Dict[str, Any]:
        """Parse raw LLM output string into structured dict."""
        pass

    @abstractmethod
    def _fallback_response(self) -> Dict[str, Any]:
        """Return a safe, minimal response on LLM failure."""
        pass

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point. Checks quota → calls LLM → parses → persists → returns.
        Never raises. Always returns a valid dict.
        """
        # 1. Quota check
        try:
            check_quota(self.organization_id, self.db)
        except Exception as quota_err:
            logger.warning(f"[{self.agent_type}] Quota blocked: {quota_err}")
            raise

        # 2. Build prompts
        try:
            system_prompt, user_prompt = self._build_prompt(context)
        except Exception as e:
            logger.error(f"[{self.agent_type}] Prompt build failed: {e}")
            return self._fallback_response()

        # 3. Call LLM
        result = call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            organization_id=self.organization_id,
            db=self.db,
            operation=f"agent_{self.agent_type}",
        )

        content = result.get("content", "")
        if not content:
            logger.warning(f"[{self.agent_type}] Empty LLM response — using fallback.")
            output = self._fallback_response()
            status = "fallback"
        else:
            try:
                output = self._parse_response(content)
                status = "success"
            except Exception as parse_err:
                logger.error(f"[{self.agent_type}] Parse failed: {parse_err}. Raw: {content[:200]}")
                output = self._fallback_response()
                status = "failed"

        # 4. Attach metadata
        output["_meta"] = {
            "agent_type": self.agent_type,
            "prompt_version": self.prompt_version,
            "model_used": result.get("model", ""),
            "tokens_used": result.get("tokens", 0),
            "cost_estimate": result.get("cost", 0.0),
            "status": status,
        }

        return output

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        """Robust JSON parser handles markdown code blocks and trailing commas."""
        text = raw.strip()
        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(text)
