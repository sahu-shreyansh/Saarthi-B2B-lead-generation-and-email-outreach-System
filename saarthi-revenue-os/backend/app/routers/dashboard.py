from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.database.database import get_db
from app.database.models import Lead, Campaign, CampaignEmail, Meeting, AiUsageLog
from app.core.deps import get_current_user_and_org

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
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    campaigns = db.query(Campaign).filter(Campaign.organization_id == active_org_id).all()
    
    total_sent = 0
    total_opened = 0
    total_clicked = 0
    total_replied = 0
    
    for c in campaigns:
        stats = c.stats or {}
        total_sent += stats.get("sent", 0)
        total_opened += stats.get("opened", 0)
        total_clicked += stats.get("clicked", 0)
        total_replied += stats.get("replied", 0)
        
    return {
        "sent": total_sent,
        "opened": total_opened,
        "clicked": total_clicked,
        "replied": total_replied,
        "open_rate_pct": (total_opened / total_sent * 100) if total_sent > 0 else 0,
        "reply_rate_pct": (total_replied / total_sent * 100) if total_sent > 0 else 0
    }

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
