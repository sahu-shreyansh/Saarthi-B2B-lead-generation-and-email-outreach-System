import json
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.providers.llm.openrouter_provider import OpenRouterProvider

class AutoReplyService:
    @staticmethod
    def generate_reply(
        db: Session,
        organization_id: str,
        message_id: str,
        thread_history: str,
        intent: str,
        booking_link: str = ""
    ) -> str:
        """
        Generates a contextual reply to an inbound email using OpenRouter based on its intent
        and the previous thread history.
        """
        ai_provider = OpenRouterProvider(db=db)
        
        prompt = f"""
        You are an SDR assistant. Draft a reply to the prospect's last email.
        The system has classified their intent as: {intent}
        
        Thread History:
        {thread_history}
        
        Guidelines based on intent:
        - If 'positive': Propose a time to chat, answer any questions briefly, and include our booking link if provided: {booking_link}
        - If 'not_interested': Politely thank them for their time and close the loop.
        - If 'ooo': Keep it brief, say you will reach back out when they return.
        - Default: Respond politely and ask clarifying questions if needed.
        
        Do not include subject lines or "Subject:" prefixes, just the raw email body string.
        Return ONLY valid JSON with this exact structure:
        {{
            "reply": "<the reply body text>"
        }}
        """
        
        try:
            raw_result = ai_provider.generate(
                prompt_type="auto_reply",
                system_prompt="You are a polite, concise B2B SDR.",
                user_prompt=prompt,
                org_id=organization_id,
                use_fast_model=False # Use Primary Model (Claude 3.5 Sonnet) for high quality replies
            )
            
            # Clean possible markdown block
            json_str = raw_result
            if json_str.startswith("```json"):
                json_str = json_str.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(json_str)
            return result.get("reply", "Thank you, noted.")
            
        except Exception as e:
            return f"Thank you for your response.\n\n(AI Reply Generation Failed: {str(e)})"
