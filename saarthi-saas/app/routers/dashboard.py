from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, date

from app.db.session import get_db
from app.db.models import User, OutreachLog, Campaign, Lead, Subscription, UsageTracking
from app.core.deps import get_current_user

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)

    # Get user's campaign IDs
    cq = await db.execute(select(Campaign.id).where(Campaign.user_id == user.id))
    campaign_ids = [r[0] for r in cq.all()]

    if not campaign_ids:
        return {
            "emails_sent_today": 0,
            "replies_today": 0,
            "positive_replies": 0,
            "followups_due": 0,
            "total_leads": 0,
            "total_sent": 0,
            "usage_sent": 0,
            "usage_limit": 100,
        }

    # Emails sent today
    sent_today = await db.execute(
        select(func.count(OutreachLog.id))
        .where(OutreachLog.campaign_id.in_(campaign_ids))
        .where(OutreachLog.sent_at >= today_start)
    )

    # Replies today
    replies_today = await db.execute(
        select(func.count(OutreachLog.id))
        .where(OutreachLog.campaign_id.in_(campaign_ids))
        .where(OutreachLog.reply_status == "REPLIED")
        .where(OutreachLog.sent_at >= today_start)
    )

    # Positive replies (all time)
    positive = await db.execute(
        select(func.count(OutreachLog.id))
        .where(OutreachLog.campaign_id.in_(campaign_ids))
        .where(OutreachLog.reply_type == "POSITIVE")
    )

    # Followups due
    followups = await db.execute(
        select(func.count(OutreachLog.id))
        .where(OutreachLog.campaign_id.in_(campaign_ids))
        .where(OutreachLog.followup_status == "PENDING")
        .where(OutreachLog.reply_status == "NO_REPLY")
        .where(OutreachLog.next_followup_due <= today)
    )

    # Total leads
    total_leads = await db.execute(
        select(func.count(Lead.id)).where(Lead.campaign_id.in_(campaign_ids))
    )

    # Total sent
    total_sent = await db.execute(
        select(func.count(OutreachLog.id)).where(OutreachLog.campaign_id.in_(campaign_ids))
    )

    # Usage
    month_str = today.strftime("%Y-%m")
    usage_q = await db.execute(
        select(UsageTracking).where(
            UsageTracking.user_id == user.id,
            UsageTracking.month == month_str,
        )
    )
    usage = usage_q.scalar_one_or_none()

    sub_q = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = sub_q.scalar_one_or_none()

    return {
        "emails_sent_today": sent_today.scalar() or 0,
        "replies_today": replies_today.scalar() or 0,
        "positive_replies": positive.scalar() or 0,
        "followups_due": followups.scalar() or 0,
        "total_leads": total_leads.scalar() or 0,
        "total_sent": total_sent.scalar() or 0,
        "usage_sent": usage.emails_sent if usage else 0,
        "usage_limit": sub.monthly_limit if sub else 100,
    }
