import logging
import json
from sqlalchemy.orm import Session
from app.providers.llm.openrouter_provider import OpenRouterProvider
from app.providers.llm.prompt_templates import SYSTEM_PROMPT, EMAIL_GENERATION_PROMPT
from app.database.models import Lead, Campaign, OutreachLog

logger = logging.getLogger(__name__)

class CampaignService:
    """
    Manages automated cold email drafting utilizing Claude/GPT 
    based on campaign instructions and lead metadata.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ai = OpenRouterProvider(db=db)

    def generate_opening_email(self, lead: Lead, campaign: Campaign) -> str:
        """
        Drafts a heavily personalized opening outreach email based on the Master Spec
        AI rules (under 90 words, no emojis, purely professional).
        """
        logger.info(f"[CampaignService] Generating cold outreach for: {lead.email}")
        
        lead_payload = {
            "first_name": lead.name.split(" ")[0] if lead.name else "there",
            "company_name": lead.company or "",
            "industry": lead.meta.get("industry", "") if lead.meta else ""
        }
        
        campaign_payload = {
            "offer": "We offer a fully automated intent-driven outbound system.",
            "value_proposition": "We cut outbound manual labor by 80% while doubling meeting booked rates using contextual AI."
        }
        
        # Merge if campaign has a sequence_json meta definition for explicit offers:
        if campaign.sequence_json and len(campaign.sequence_json) > 0:
            campaign_payload["offer"] = campaign.sequence_json[0].get("offer", campaign_payload["offer"])
            campaign_payload["value_proposition"] = campaign.sequence_json[0].get("value_prop", campaign_payload["value_proposition"])

        prompt = EMAIL_GENERATION_PROMPT.format(
            lead_data=json.dumps(lead_payload, indent=2),
            campaign_data=json.dumps(campaign_payload, indent=2)
        )
        
        # Email Generation maps to primary_model (Claude) cached internally if needed
        draft = self.ai.generate(
            prompt_type="EMAIL_GENERATION",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            org_id=str(lead.org_id),
            campaign_id=str(campaign.id),
            use_fast_model=False,
            default_fallback="Hi there,\\n\\nI'd love to connect and see if our automated leadgen system could help scale your outreach.\\n\\nBest,\\n"
        )
        
        return draft
