"""
Reply Classifier Agent — Classifies incoming email reply intent.
Updates EmailReply.intent in the database after classification.
"""
import logging
import os
from typing import Any, Dict, Tuple

from app.ai.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = None

VALID_INTENTS = {
    "interested", "not_interested", "meeting_request",
    "out_of_office", "bounce", "unclear"
}


def _get_prompt_template() -> str:
    global _PROMPT_TEMPLATE
    if _PROMPT_TEMPLATE is None:
        prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/reply_classifier.md")
        with open(prompt_path, "r") as f:
            _PROMPT_TEMPLATE = f.read()
    return _PROMPT_TEMPLATE


REPLY_SYSTEM = "You are SAARTHI Reply Classifier. Classify email reply intent. Return ONLY valid JSON."


class ReplyClassifier(BaseAgent):
    agent_type = "reply_classifier"
    prompt_version = "reply_classifier_v1"

    def _build_prompt(self, context: Dict[str, Any]) -> Tuple[str, str]:
        template = _get_prompt_template()
        reply_body = context.get("reply_body", "")
        user_prompt = template.replace("{{reply_body}}", reply_body)
        return REPLY_SYSTEM, user_prompt

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        data = self._parse_json(raw)
        if "intent" not in data:
            raise ValueError("Missing 'intent' in ReplyClassifier response")

        # Normalize intent
        intent = data.get("intent", "unclear").lower()
        if intent not in VALID_INTENTS:
            logger.warning(f"[ReplyClassifier] Unknown intent '{intent}' — defaulting to 'unclear'")
            data["intent"] = "unclear"

        return data

    def _fallback_response(self) -> Dict[str, Any]:
        return {
            "intent": "unclear",
            "confidence": "low",
            "summary": "Could not classify reply.",
            "recommended_action": "wait",
            "tone": "neutral",
            "key_signal": "fallback due to LLM failure",
        }

    def run_and_update_db(self, reply_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs classification and updates the EmailReply.intent in the database.
        This is the high-level entry point to use from the pipeline.
        """
        from app.database.models import EmailReply

        result = self.run(context)
        intent = result.get("intent", "unclear")

        try:
            import uuid
            reply = self.db.query(EmailReply).filter(
                EmailReply.id == uuid.UUID(reply_id)
            ).first()
            if reply:
                reply.intent = intent
                self.db.commit()
                logger.info(f"[ReplyClassifier] Updated reply {reply_id} intent → {intent}")
        except Exception as e:
            logger.error(f"[ReplyClassifier] Failed to update DB for reply {reply_id}: {e}")
            self.db.rollback()

        return result
