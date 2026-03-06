import json
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.providers.llm.openrouter_provider import OpenRouterProvider

VALID_INTENTS = ["positive", "negative", "ooo", "not_interested", "unknown"]

class InboxClassificationService:
    @staticmethod
    def classify_message(
        db: Session,
        organization_id: str,
        message_id: str,
        subject: str,
        body: str
    ) -> str:
        """
        Classifies an inbound email body into an intent category using OpenRouter.
        Returns one of: positive, negative, ooo, not_interested, unknown
        """
        ai_provider = OpenRouterProvider(db=db)
        
        prompt = f"""
        Analyze this inbound email from a prospect and classify their intent.
        
        Subject: {subject}
        Body:
        {body}
        
        Select EXACTLY ONE of the following intent categories:
        1. "positive" (interested, asking for more info, wants to book a call)
        2. "negative" (unsubscribe, angry, spam)
        3. "not_interested" (polite no, timing isn't right, already have a solution)
        4. "ooo" (Out of office auto-responder)
        5. "unknown" (None of the above or ambiguous)
        
        Return ONLY valid JSON with this exact structure:
        {{
            "intent": "<the category string>"
        }}
        """
        
        try:
            raw_result = ai_provider.generate(
                prompt_type="classify_message",
                system_prompt="You are an email intent classification system.",
                user_prompt=prompt,
                org_id=organization_id,
                is_classification=True,
                default_fallback="unknown"
            )
            
            # Clean possible markdown block
            json_str = raw_result
            if json_str.startswith("```json"):
                json_str = json_str.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(json_str)
            intent = result.get("intent", "unknown").lower()
            
            if intent not in VALID_INTENTS:
                return "unknown"
                
            return intent
            
        except Exception as e:
            return "unknown"
