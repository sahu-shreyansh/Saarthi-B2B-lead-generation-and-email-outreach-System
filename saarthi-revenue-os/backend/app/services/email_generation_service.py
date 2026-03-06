import json
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.providers.llm.openrouter_provider import OpenRouterProvider
from app.providers.llm.prompt_templates import SYSTEM_PROMPT

class EmailGenerationService:
    @staticmethod
    def generate_cold_email(
        db: Session,
        organization_id: str,
        campaign_id: str,
        lead_data: Dict[str, Any],
        email_template: str
    ) -> Tuple[str, str]:
        """
        Creates a customized cold email subject and body for a specific lead using OpenRouter.
        """
        ai_provider = OpenRouterProvider(db=db)
        
        prompt = f"""
        You are an expert B2B sales development representative.
        Generate a highly personalized cold email based on the provided lead data and campaign template.
        
        Lead Data:
        {json.dumps(lead_data, indent=2)}
        
        Campaign Guidelines/Template Context:
        {email_template}
        
        The email must be concise, professional, and focus on the value proposition.
        Return ONLY valid JSON with this exact structure:
        {{
            "subject": <catchy, relevant subject line>,
            "body": <full email body text>
        }}
        """
        
        try:
            raw_result = ai_provider.generate(
                prompt_type="generate_email",
                system_prompt="You are a top-tier B2B SDR.",
                user_prompt=prompt,
                org_id=organization_id,
                campaign_id=campaign_id,
                use_fast_model=False # Use Primary Model (Claude 3.5 Sonnet) for high quality emails
            )
            
            # Clean possible markdown block
            json_str = raw_result
            if json_str.startswith("```json"):
                json_str = json_str.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(json_str)
            
            subject = result.get("subject", "Connecting regarding your business goals")
            body = result.get("body", "Hi,\n\nI wanted to reach out regarding potential synergies.\n\nBest,\nSDR")
            
            return subject, body
            
        except Exception as e:
            fallback_subject = "Connecting regarding your business goals"
            fallback_body = f"Hi,\n\nI wanted to reach out regarding potential synergies.\n\nBest,\nSDR\n\n(AI Generation Failed: {str(e)})"
            return fallback_subject, fallback_body
