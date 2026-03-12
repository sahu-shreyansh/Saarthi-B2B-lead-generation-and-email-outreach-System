import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.models import Lead, CampaignEmail, Meeting, EmailEvent, EmailReply

from app.providers.llm.openrouter_provider import OpenRouterProvider
from app.providers.llm.prompt_templates import SYSTEM_PROMPT, DEAL_PIPELINE_INSIGHTS_PROMPT

logger = logging.getLogger(__name__)

class RevenueAnalyticsService:
    """
    SQL Aggregation engine powering the Enterprise Dashboards.
    Computes strict Conversion funnels and maps SQL outputs to Anthropic LLM Insights.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ai = OpenRouterProvider(db=db)

    def calculate_campaign_metrics(self, org_id: str, campaign_id: str) -> dict:
        """Native aggregate computation mapping Lead & activity states."""
        
        # 1. Pipeline Value (Sum of deal_val for leads in this campaign)
        pipeline_value = self.db.query(func.sum(Lead.score)).filter(
            Lead.organization_id == org_id,
            Lead.campaign_id == campaign_id
        ).scalar() or 0
        
        # 2. Email Stats
        total_sent = self.db.query(CampaignEmail).filter(
            CampaignEmail.campaign_id == campaign_id,
            CampaignEmail.status == "sent"
        ).count()
        
        # Open Rate (based on EmailEvent)
        opens = self.db.query(EmailEvent).join(CampaignEmail).filter(
            CampaignEmail.campaign_id == campaign_id,
            EmailEvent.event_type == "opened"
        ).count()
        
        # Replies
        replies = self.db.query(EmailReply).join(CampaignEmail).filter(
            CampaignEmail.campaign_id == campaign_id
        ).count()
        
        # Meetings
        meetings = self.db.query(Meeting).filter(
            Meeting.organization_id == org_id,
            Meeting.lead_id.in_(self.db.query(Lead.id).filter(Lead.campaign_id == campaign_id))
        ).count()

        open_rate = round((opens / total_sent * 100) if total_sent > 0 else 0.0, 1)
        reply_rate = round((replies / total_sent * 100) if total_sent > 0 else 0.0, 1)
        meeting_rate = round((meetings / total_sent * 100) if total_sent > 0 else 0.0, 1)
        
        return {
            "total_sent": total_sent,
            "pipeline_value": float(pipeline_value),
            "open_rate_pct": open_rate,
            "reply_rate_pct": reply_rate,
            "meeting_rate_pct": meeting_rate,
            "meetings_booked": meetings
        }

    def get_org_revenue_stats(self, org_id: str) -> dict:
        """Calculates global ROI and AI efficiency for the organization."""
        
        # Total Pipeline: Weighted sum of scores as proxy for lead value if deal_value is not explicitly used
        # If deal_value exists in metadata or another column use that. 
        # For now, let's assume deal_value is a column we use or we stick to Lead.score * multiplier
        total_pipeline = self.db.query(func.sum(Lead.score)).filter(Lead.organization_id == org_id).scalar() or 0
        total_pipeline_val = float(total_pipeline) * 100 # Each score point = $100 potential
        
        # AI Savings calculation
        # $10 for every AI-processed reply + $2 for every enriched lead
        enriched_leads = self.db.query(Lead).filter(
            Lead.organization_id == org_id,
            Lead.email_verified == True
        ).count()
        
        ai_replies = self.db.query(EmailReply).join(Lead).filter(
            Lead.organization_id == org_id,
            EmailReply.intent != "unknown"
        ).count()
        
        ai_savings = (enriched_leads * 2.0) + (ai_replies * 10.0)
        
        # Meetings 
        total_meetings = self.db.query(Meeting).filter(Meeting.organization_id == org_id).count()
        
        return {
            "total_pipeline_value": total_pipeline_val,
            "ai_savings": ai_savings,
            "total_meetings": total_meetings,
            "projected_revenue": total_pipeline_val * 0.15, # 15% win rate assumption
            "roi_multiplier": round(ai_savings / 49.0, 1) # Relative to a $49/mo sub
        }

    def generate_dashboard_insights(self, org_id: str, campaign_id: str) -> str:
        """Invokes native OpenRouter Prompt 7 to contextualize dashboard SQL."""
        
        logger.info(f"[Analytics] Requesting AI Pipeline Insights computation for {campaign_id}")
        
        metrics = self.calculate_campaign_metrics(org_id, campaign_id)
        
        prompt = DEAL_PIPELINE_INSIGHTS_PROMPT.format(
            open_rate=metrics["open_rate"],
            reply_rate=metrics["reply_rate"],
            meeting_rate=metrics["meeting_rate"],
            closed_deals=metrics["closed_deals"]
        )
        
        insights = self.ai.generate(
            prompt_type="DEAL_PIPELINE_INSIGHTS",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            org_id=org_id,
            campaign_id=campaign_id,
            use_fast_model=False, 
            default_fallback="Top insight: Campaign running.\\nBiggest bottleneck: Low Volume.\\nImprovement suggestion: Scale sender accounts."
        )
        
        return insights
