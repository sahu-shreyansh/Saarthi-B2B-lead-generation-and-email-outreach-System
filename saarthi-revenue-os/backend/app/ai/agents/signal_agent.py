"""
Signal Agent — Extracts behavioral and psychological signals from lead profiles.
Uses Prompt 1 internal steps (STEP 1 only logic applied to the full normal agent prompt).
"""
import json
import logging
import os
from typing import Any, Dict, Tuple
from sqlalchemy.orm import Session

from app.ai.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../prompts/normal_agent.md")

# Signal-extraction system prompt (condensed — no email writing)
SIGNAL_SYSTEM = """You are SAARTHI Signal Extractor.

Read the lead profile below and extract ONLY the signal report.
Do NOT write an email.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATA RELIABILITY RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- NEVER invent or assume facts.
- If headline/about is UNKNOWN, infer signals from job title + company + company size only.
- If signals cannot be confidently inferred, set values to "unknown".

Return ONLY this JSON:
{
  "signal_report": {
    "inferred_priority": "what this person cares about most",
    "hidden_frustration": "what is quietly frustrating them",
    "person_type": "Builder / Operator / Visionary / Hustler",
    "conversation_opener": "the non-obvious thing pulled from their profile",
    "avoid": "what would make them delete an email instantly"
  },
  "personalization_depth": "Surface / Medium / Deep"
}

Return ONLY the JSON. No explanations outside JSON.
"""


class SignalAgent(BaseAgent):
    agent_type = "signal"
    prompt_version = "signal_v1"

    def _build_prompt(self, context: Dict[str, Any]) -> Tuple[str, str]:
        user_prompt = f"""
Name: {context.get('lead_name', 'UNKNOWN')}
Job Title: {context.get('job_title', 'UNKNOWN')}
Company: {context.get('lead_company', 'UNKNOWN')}
Company Size: {context.get('company_size', 'UNKNOWN')}
Headline: {context.get('headline', 'UNKNOWN')}
About: {context.get('about', 'UNKNOWN')}
Industry: {context.get('industry', 'UNKNOWN')}
""".strip()
        return SIGNAL_SYSTEM, user_prompt

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        data = self._parse_json(raw)
        # Validate required keys
        if "signal_report" not in data:
            raise ValueError("Missing 'signal_report' in SignalAgent response")
        return data

    def _fallback_response(self) -> Dict[str, Any]:
        return {
            "signal_report": {
                "inferred_priority": "unknown",
                "hidden_frustration": "unknown",
                "person_type": "unknown",
                "conversation_opener": "unknown",
                "avoid": "generic pitches and buzzwords",
            },
            "personalization_depth": "Surface",
        }
