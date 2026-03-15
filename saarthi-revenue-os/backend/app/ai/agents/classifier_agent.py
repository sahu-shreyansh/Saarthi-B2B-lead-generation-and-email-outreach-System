"""
Classifier Agent — Evaluates each service against a lead and selects the winning one.
Uses Prompt 2 from agent.md (4-step classifier approach).
"""
import json
import logging
import os
from typing import Any, Dict, Tuple
from sqlalchemy.orm import Session

from app.ai.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = None


def _get_prompt_template() -> str:
    global _PROMPT_TEMPLATE
    if _PROMPT_TEMPLATE is None:
        prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/classifier_agent.md")
        with open(prompt_path, "r") as f:
            _PROMPT_TEMPLATE = f.read()
    return _PROMPT_TEMPLATE


CLASSIFIER_SYSTEM = "You are SAARTHI Classifier — a B2B outreach intelligence agent. Always return valid JSON. No markdown. No trailing commas."


class ClassifierAgent(BaseAgent):
    agent_type = "classifier"
    prompt_version = "classifier_v1"

    def _build_prompt(self, context: Dict[str, Any]) -> Tuple[str, str]:
        import json as _json
        template = _get_prompt_template()

        services_json_str = _json.dumps(context.get("services_json", []), indent=2)

        user_prompt = template\
            .replace("{{company_name}}", context.get("company_name", "UNKNOWN"))\
            .replace("{{company_business}}", context.get("company_business", "UNKNOWN"))\
            .replace("{{icp}}", context.get("icp", "UNKNOWN"))\
            .replace("{{services_json}}", services_json_str)\
            .replace("{{lead_name}}", context.get("lead_name", "UNKNOWN"))\
            .replace("{{job_title}}", context.get("job_title", "UNKNOWN"))\
            .replace("{{lead_company}}", context.get("lead_company", "UNKNOWN"))\
            .replace("{{company_size}}", context.get("company_size", "UNKNOWN"))\
            .replace("{{headline}}", context.get("headline", "UNKNOWN"))\
            .replace("{{about}}", context.get("about", "UNKNOWN"))

        return CLASSIFIER_SYSTEM, user_prompt

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        data = self._parse_json(raw)
        if "classification" not in data:
            raise ValueError("Missing 'classification' in ClassifierAgent response")
        if "email" not in data:
            raise ValueError("Missing 'email' in ClassifierAgent response")
        return data

    def _fallback_response(self) -> Dict[str, Any]:
        return {
            "agent_type": "classifier",
            "signal_report": {
                "inferred_priority": "unknown",
                "hidden_frustration": "unknown",
                "person_type": "unknown",
                "conversation_opener": "unknown",
                "avoid": "generic pitches",
            },
            "classification": {
                "services_evaluated": [],
                "selected_service": {
                    "name": "unknown",
                    "description": "",
                    "match_reason": "Classifier failed — using fallback.",
                    "positioning": "",
                    "service_type": "unknown",
                },
                "classifier_logic": "fallback due to LLM failure",
            },
            "email": {
                "subject": "Quick question",
                "body": "Hi,\n\nWanted to reach out — we help companies like yours improve outreach results. Worth a quick chat?\n\nBest,",
            },
            "why_this_works": {
                "word_count": "20",
                "personalization_depth": "Surface",
                "why_wont_feel_generic": "fallback email — not personalized",
            },
        }
