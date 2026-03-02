from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.db.models import User, Campaign, Lead, OutreachLog
from app.core.deps import get_current_user

router = APIRouter()


class CampaignCreate(BaseModel):
    name: str


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None  # active | paused
    sequence_config: Optional[list] = None
    schedule_config: Optional[dict] = None


@router.get("")
async def list_campaigns(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.user_id == user.id).order_by(Campaign.created_at.desc())
    )
    campaigns = result.scalars().all()

    out = []
    for c in campaigns:
        # Count leads
        lead_count = await db.execute(
            select(func.count(Lead.id)).where(Lead.campaign_id == c.id)
        )
        # Count replies
        reply_count = await db.execute(
            select(func.count(OutreachLog.id))
            .where(OutreachLog.campaign_id == c.id)
            .where(OutreachLog.reply_status == "REPLIED")
        )
        total_sent = await db.execute(
            select(func.count(OutreachLog.id)).where(OutreachLog.campaign_id == c.id)
        )
        leads = lead_count.scalar() or 0
        replies = reply_count.scalar() or 0
        sent = total_sent.scalar() or 0

        out.append({
            "id": str(c.id),
            "name": c.name,
            "status": c.status,
            "leads_count": leads,
            "reply_rate": round((replies / sent * 100), 1) if sent > 0 else 0,
            "total_sent": sent,
            "created_at": c.created_at.isoformat() if c.created_at else "",
            "sequence_config": c.sequence_config,
            "schedule_config": c.schedule_config,
        })
    return out


@router.post("", status_code=201)
async def create_campaign(
    body: CampaignCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = Campaign(user_id=user.id, name=body.name)
    db.add(campaign)
    await db.flush()
    return {"id": str(campaign.id), "name": campaign.name, "status": campaign.status}


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get leads
    leads_q = await db.execute(
        select(Lead).where(Lead.campaign_id == campaign.id).order_by(Lead.created_at.desc())
    )
    leads = leads_q.scalars().all()

    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "status": campaign.status,
        "sequence_config": campaign.sequence_config,
        "schedule_config": campaign.schedule_config,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else "",
        "leads": [
            {
                "id": str(l.id),
                "name": l.name,
                "company": l.company,
                "email": l.email,
                "status": l.status,
                "created_at": l.created_at.isoformat() if l.created_at else "",
            }
            for l in leads
        ],
    }


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if body.name is not None:
        campaign.name = body.name
    if body.status is not None:
        campaign.status = body.status
    if body.sequence_config is not None:
        campaign.sequence_config = body.sequence_config
    if body.schedule_config is not None:
        campaign.schedule_config = body.schedule_config

    await db.flush()

    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "status": campaign.status,
        "sequence_config": campaign.sequence_config,
        "schedule_config": campaign.schedule_config,
    }
