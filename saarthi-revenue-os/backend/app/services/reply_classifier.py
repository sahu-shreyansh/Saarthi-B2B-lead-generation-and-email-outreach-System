import json
from sqlalchemy.orm import Session
from app.providers.llm.openrouter_provider import OpenRouterProvider

VALID_INTENTS = ["interested", "not_interested", "meeting_request", "out_of_office", "unknown"]

class ReplyClassifier:
    """
    Uses LLM (OpenRouter) to classify incoming email replies for the outbound engine.
    Categories: interested, not_interested, meeting_request, out_of_office, unknown
    """
    
    @staticmethod
    def classify_reply(db: Session, organization_id: str, content: str) -> str:
        if not content:
            return "unknown"
            
        ai_provider = OpenRouterProvider(db=db)
        
        prompt = f"""
        You are an expert sales development representative. 
        Analyze the following email reply from a prospect and classify it into EXACTLY ONE category.

        Email Reply Content:
        \"\"\"{content}\"\"\"

        Categories:
        - "interested": The person wants to learn more, asks for a demo, or is generally positive.
        - "meeting_request": The person specifically asks for a meeting or provides their availability/calendar.
        - "not_interested": The person says no, tells you to stop emailing, or is negative.
        - "out_of_office": Auto-reply or the person is away for some time.
        - "unknown": Anything else that doesn't fit the above.

        Return ONLY a JSON object with this exact structure:
        {{
            "intent": "<category_name>"
        }}
        """
        
        try:
            raw_result = ai_provider.generate(
                prompt_type="classify_outbound_reply",
                system_prompt="You are a reply classification AI for an outbound sales engine.",
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
            
            if intent in VALID_INTENTS:
                return intent
            
            # Fuzzy match if needed
            for valid in VALID_INTENTS:
                if valid in intent:
                    return valid
                    
            return "unknown"
        except Exception as e:
            print(f"REPLY_CLASSIFIER_ERROR: {str(e)}")
            return "unknown"
