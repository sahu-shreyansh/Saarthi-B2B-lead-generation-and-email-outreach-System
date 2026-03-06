import json
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.providers.llm.openrouter_provider import OpenRouterProvider
from app.database.models import LeadScore

class LeadScoringService:
    @staticmethod
    def score_lead(
        db: Session,
        organization_id: str,
        lead_id: str,
        lead_data: Dict[str, Any]
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calls OpenRouter to analyze the lead's data and score it from 0 to 100.
        Returns (score, factors_dict)
        """
        ai_provider = OpenRouterProvider(db=db)
        
        prompt = f"""
        Analyze this B2B sales lead and assign a quality score from 0 to 100.
        
        Lead Data:
        {json.dumps(lead_data, indent=2)}
        
        Return ONLY valid JSON with this exact structure:
        {{
            "score": <int 0-100>,
            "factors": {{
                "company_size": <string analysis>,
                "industry_fit": <string analysis>,
                "decision_maker": <string analysis>
            }},
            "reasoning": <string summary explanation>
        }}
        """
        
        try:
            raw_result = ai_provider.generate(
                prompt_type="score_lead",
                system_prompt="You are a professional B2B lead scoring AI.",
                user_prompt=prompt,
                org_id=organization_id,
                use_fast_model=True # GPT-4o-Mini is sufficient for scoring
            )
            
            # Clean possible markdown block
            json_str = raw_result
            if json_str.startswith("```json"):
                json_str = json_str.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(json_str)
            score = int(result.get("score", 0))
            factors = result.get("factors", {})
            factors["reasoning"] = result.get("reasoning", "")
            
            # Store lead score history
            score_entry = LeadScore(
                lead_id=lead_id,
                score=score,
                factors=factors,
                model_version=ai_provider.FAST_MODEL
            )
            db.add(score_entry)
            db.commit()
            
            return score, factors
            
        except Exception as e:
            # Fallback score if AI fails
            return 0, {"error": str(e), "reasoning": "Failed to score lead due to AI error."}
