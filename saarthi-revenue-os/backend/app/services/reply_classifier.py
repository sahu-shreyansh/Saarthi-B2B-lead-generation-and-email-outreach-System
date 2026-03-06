import logging
from sqlalchemy.orm import Session
from app.providers.llm.openrouter_provider import OpenRouterProvider
from app.providers.llm.prompt_templates import SYSTEM_PROMPT, REPLY_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)

class ReplyClassifierService:
    """
    Categorizes incoming SMTP replies natively through AI analysis
    into strict label bindings: POSITIVE, NEGATIVE, OOO, MEETING_REQUEST...
    """
    
    VALID_LABELS = {"POSITIVE", "NEGATIVE", "MEETING_REQUEST", "OUT_OF_OFFICE", "UNSUBSCRIBE", "NEUTRAL"}
    
    def __init__(self, db: Session):
        self.db = db
        self.ai = OpenRouterProvider(db=db)

    def classify_reply(self, email_body: str, org_id: str, campaign_id: str = None) -> str:
        """
        Fast LLM Classification of the given thread body.
        Guarantees one of the VALID_LABELS enum will return.
        """
        logger.info("[ReplyClassifier] Classifying inbound message intent...")
        
        prompt = REPLY_CLASSIFICATION_PROMPT.format(
            email_text=email_body[:5000] # Cap long trailing threads
        )
        
        # Classification mandates the FAST_MODEL (GPT-4o-mini)
        classification = self.ai.generate(
            prompt_type="REPLY_CLASSIFICATION",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            org_id=org_id,
            campaign_id=campaign_id,
            is_classification=True, 
            default_fallback="NEUTRAL"
        )
        
        clean_label = classification.strip().upper()
        
        # Enforce enum bounds via regex or hard check
        for label in self.VALID_LABELS:
            if label in clean_label:
                return label
                
        logger.warning(f"[ReplyClassifier] AI yielded unrecognized intent: {clean_label}. Defaulting to NEUTRAL.")
        return "NEUTRAL"
