from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.database.database import get_db
from app.database.models import Lead, Campaign, CampaignEmail, Meeting, AiUsageLog, EmailEvent, EmailReply
from app.core.deps import get_current_user_and_org
from app.services.revenue_analytics_service import RevenueAnalyticsService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metrics")
def get_metrics(
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    
    total_leads = db.query(func.count(Lead.id)).filter(Lead.organization_id == active_org_id).scalar() or 0
    qualified_leads = db.query(func.count(Lead.id)).filter(
        Lead.organization_id == active_org_id,
        Lead.score >= 50
    ).scalar() or 0
    active_campaigns = db.query(func.count(Campaign.id)).filter(Campaign.organization_id == active_org_id, Campaign.status == "active").scalar() or 0
    
    # We join CampaignEmail with Campaign to filter by org_id
    emails_sent = db.query(func.count(CampaignEmail.id)).join(Campaign).filter(
        Campaign.organization_id == active_org_id,
        CampaignEmail.status == "sent"
    ).scalar() or 0
    
    replies_received = db.query(func.count(CampaignEmail.id)).join(Campaign).filter(
        Campaign.organization_id == active_org_id,
        CampaignEmail.status == "replied"
    ).scalar() or 0
    
    meetings_booked = db.query(func.count(Meeting.id)).filter(
        Meeting.organization_id == active_org_id,
        Meeting.status == "scheduled"
    ).scalar() or 0
    
    conversion_rate = round((meetings_booked / total_leads * 100), 2) if total_leads > 0 else 0.0
    
    return {
        "total_leads": total_leads,
        "qualified_leads": qualified_leads,
        "active_campaigns": active_campaigns,
        "emails_sent": emails_sent,
        "replies_received": replies_received,
        "meetings_booked": meetings_booked,
        "conversion_rate": conversion_rate
    }

@router.get("/lead-growth")
def get_lead_growth(
    days: int = 30,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(
        func.date(Lead.created_at).label("date"),
        func.count(Lead.id).label("count")
    ).filter(
        Lead.organization_id == active_org_id,
        Lead.created_at >= cutoff
    ).group_by(func.date(Lead.created_at)).order_by(func.date(Lead.created_at)).all()
    
    return [{"date": str(r.date), "count": r.count} for r in results]

@router.get("/email-performance")
def get_email_performance(
    days: int = 30,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """Returns daily time-series performance data for outreach."""
    current_user, active_org_id, role = deps
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Daily Sent
    sent_results = db.query(
        func.date(CampaignEmail.sent_at).label("date"),
        func.count(CampaignEmail.id).label("count")
    ).join(Campaign).filter(
        Campaign.organization_id == active_org_id,
        CampaignEmail.status == "sent",
        CampaignEmail.sent_at >= cutoff
    ).group_by(func.date(CampaignEmail.sent_at)).all()
    
    # Daily Opens
    open_results = db.query(
        func.date(EmailEvent.timestamp).label("date"),
        func.count(EmailEvent.id).label("count")
    ).join(CampaignEmail).join(Campaign).filter(
        Campaign.organization_id == active_org_id,
        EmailEvent.event_type == "opened",
        EmailEvent.timestamp >= cutoff
    ).group_by(func.date(EmailEvent.timestamp)).all()
    
    # Daily Replies
    reply_results = db.query(
        func.date(EmailReply.received_at).label("date"),
        func.count(EmailReply.id).label("count")
    ).join(CampaignEmail).join(Campaign).filter(
        Campaign.organization_id == active_org_id,
        EmailReply.received_at >= cutoff
    ).group_by(func.date(EmailReply.received_at)).all()
    
    # Merge into time series
    dates = {}
    for r in sent_results:
        d = str(r.date)
        if d not in dates: dates[d] = {"date": d, "sent": 0, "opened": 0, "replied": 0}
        dates[d]["sent"] = r.count
        
    for r in open_results:
        d = str(r.date)
        if d not in dates: dates[d] = {"date": d, "sent": 0, "opened": 0, "replied": 0}
        dates[d]["opened"] = r.count
        
    for r in reply_results:
        d = str(r.date)
        if d not in dates: dates[d] = {"date": d, "sent": 0, "opened": 0, "replied": 0}
        dates[d]["replied"] = r.count
        
    return sorted(dates.values(), key=lambda x: x["date"])

@router.get("/revenue")
def get_revenue_metrics(
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """Returns ROI, AI Efficiency, and Pipeline Value."""
    current_user, active_org_id, role = deps
    service = RevenueAnalyticsService(db)
    return service.get_org_revenue_stats(active_org_id)

@router.get("/recent-activity")
def get_recent_activity(
    limit: int = 10,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    # Mocking a timeline of recent leads and meetings. A real app might use an event table.
    recent_leads = db.query(Lead).filter(Lead.organization_id == active_org_id).order_by(desc(Lead.created_at)).limit(limit).all()
    
    activity = []
    for l in recent_leads:
        activity.append({
            "id": str(l.id),
            "type": "lead_created",
            "title": f"New lead created: {l.company_name or l.contact_email}",
            "timestamp": l.created_at.isoformat()
        })
        
    return sorted(activity, key=lambda x: x["timestamp"], reverse=True)[:limit]

@router.get("/ai-usage")
def get_ai_usage(
    days: int = 30,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(
        func.date(AiUsageLog.created_at).label("date"),
        func.sum(AiUsageLog.cost_estimate).label("daily_cost"),
        func.sum(AiUsageLog.total_tokens).label("daily_tokens")
    ).filter(
        AiUsageLog.organization_id == active_org_id,
        AiUsageLog.created_at >= cutoff
    ).group_by(func.date(AiUsageLog.created_at)).order_by(func.date(AiUsageLog.created_at)).all()
    
    return [
        {
            "date": str(r.date),
            "cost": float(r.daily_cost or 0),
            "tokens": int(r.daily_tokens or 0)
        } for r in results
    ]
