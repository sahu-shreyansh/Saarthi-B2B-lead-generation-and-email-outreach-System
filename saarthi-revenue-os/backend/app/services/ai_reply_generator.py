import logging
from sqlalchemy.orm import Session
from app.providers.llm.openrouter_provider import OpenRouterProvider
from app.providers.llm.prompt_templates import SYSTEM_PROMPT, AI_REPLY_GENERATOR_PROMPT

logger = logging.getLogger(__name__)

class AiReplyGeneratorService:
    """
    Handles autonomous responses for POSITIVE incoming replies.
    Drafts contextual booking emails dynamically substituting calendar endpoints.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ai = OpenRouterProvider(db=db)

    def generate_booking_reply(self, org_id: str, campaign_id: str, calendar_link: str) -> str:
        """
        Takes an intended meeting link and uses AI to wrap it into a conversational
        book-a-time transition email under 80 words.
        """
        logger.info(f"[AiReplyGenerator] Drafting autonomous meeting reply using link: {calendar_link}")
        
        prompt = AI_REPLY_GENERATOR_PROMPT.format(
            calendar_link=calendar_link
        )
        
        draft = self.ai.generate(
            prompt_type="AI_REPLY_GENERATOR",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            org_id=org_id,
            campaign_id=campaign_id,
            use_fast_model=False, # Use primary Claude model for prose
            default_fallback=f"Glad to hear it! Please feel free to pick a time that works best for you here: {calendar_link}\\n\\nLooking forward to it.\\n"
        )
        
        return draft
