import logging
import json
from sqlalchemy.orm import Session
from app.providers.llm.openrouter_provider import OpenRouterProvider
from app.providers.llm.prompt_templates import SYSTEM_PROMPT, LEAD_SCORING_PROMPT
from app.database.models import Lead

logger = logging.getLogger(__name__)


class LeadIntelligenceService:
    """
    Gatekeeper engine. Scores, validates, and filters gathered leads.
    Employs Claude-3.5-Sonnet + internal heuristics to enforce ICP.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ai = OpenRouterProvider(db=db)

    def evaluate_lead(self, lead: Lead) -> bool:
        """
        Executes integer-based scoring & AI ICP evaluation.
        Returns True if score >= 50, otherwise False.
        Updates lead.ai_score inline.
        """
        logger.info(f"[Intelligence] Evaluating Lead: {lead.email}")
        
        payload = {
            "company_name": lead.company or "",
            "industry": lead.meta.get("industry", "") if lead.meta else "",
            "website": lead.domain or "",
            "linkedin_profile": lead.meta.get("linkedin_url", "") if lead.meta else "",
            "job_title": lead.job_title or "",
            "company_size": lead.meta.get("company_size", "") if lead.meta else ""
        }

        prompt = LEAD_SCORING_PROMPT.format(lead_data=json.dumps(payload, indent=2))
        
        raw_json_str = self.ai.generate(
            prompt_type="LEAD_SCORING",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            org_id=str(lead.org_id),
            campaign_id=str(lead.campaign_id),
            use_fast_model=False, # Use Claude 3.5 Sonnet for Intelligence
            default_fallback='{"score": 0, "reason": "AI failure"}'
        )

        try:
            if raw_json_str.startswith("```json"):
                raw_json_str = raw_json_str.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(raw_json_str)
            score = int(result.get("score", 0))
            reason = result.get("reason", "")
            
            logger.info(f"[Intelligence] Scored {score}/100 - {reason}")
            
            lead.ai_score = score
            self.db.add(lead)
            
            return score >= 50
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"[Intelligence] Failed to parse scoring result: {e}")
            lead.ai_score = 0
            self.db.add(lead)
            return False
