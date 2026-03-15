"""
Email Agent — Generates personalized cold emails using the Normal Agent prompt (Prompt 1).
For service-based classification, use ClassifierAgent instead.
"""
import logging
import os
from typing import Any, Dict, Tuple

from app.ai.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = None


def _get_prompt_template() -> str:
    global _PROMPT_TEMPLATE
    if _PROMPT_TEMPLATE is None:
        prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/normal_agent.md")
        with open(prompt_path, "r") as f:
            _PROMPT_TEMPLATE = f.read()
    return _PROMPT_TEMPLATE


EMAIL_SYSTEM = "You are SAARTHI — an autonomous B2B outreach intelligence agent. Always return valid JSON. No markdown wrappers. No trailing commas."


class EmailAgent(BaseAgent):
    agent_type = "email"
    prompt_version = "normal_agent_v1"

    def _build_prompt(self, context: Dict[str, Any]) -> Tuple[str, str]:
        template = _get_prompt_template()

        user_prompt = template\
            .replace("{{company_name}}", context.get("company_name", "UNKNOWN"))\
            .replace("{{company_business}}", context.get("company_business", "UNKNOWN"))\
            .replace("{{icp}}", context.get("icp", "UNKNOWN"))\
            .replace("{{services_paragraph}}", context.get("services_paragraph", "UNKNOWN"))\
            .replace("{{lead_name}}", context.get("lead_name", "UNKNOWN"))\
            .replace("{{job_title}}", context.get("job_title", "UNKNOWN"))\
            .replace("{{lead_company}}", context.get("lead_company", "UNKNOWN"))\
            .replace("{{company_size}}", context.get("company_size", "UNKNOWN"))\
            .replace("{{headline}}", context.get("headline", "UNKNOWN"))\
            .replace("{{about}}", context.get("about", "UNKNOWN"))

        return EMAIL_SYSTEM, user_prompt

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        data = self._parse_json(raw)
        if "email" not in data:
            raise ValueError("Missing 'email' key in EmailAgent response")
        email = data["email"]
        if "subject" not in email or "body" not in email:
            raise ValueError("Missing 'subject' or 'body' in email output")
        return data

    def _fallback_response(self) -> Dict[str, Any]:
        return {
            "agent_type": "normal",
            "signal_report": {
                "inferred_priority": "unknown",
                "hidden_frustration": "unknown",
                "person_type": "unknown",
                "conversation_opener": "unknown",
                "avoid": "unknown",
            },
            "angle_selected": {
                "angle_name": "generic",
                "pulled_from": "fallback",
                "why_this_angle": "LLM failure — using fallback email",
                "rejected_angles": "all",
            },
            "email": {
                "subject": "Quick question",
                "body": (
                    "Hi,\n\n"
                    "Wanted to reach out — we work with companies like yours to improve "
                    "outreach and pipeline results. Would it make sense to connect briefly?\n\n"
                    "Best,"
                ),
            },
            "why_this_works": {
                "word_count": "32",
                "personalization_depth": "Surface",
                "why_wont_feel_generic": "fallback — not personalized",
            },
        }
