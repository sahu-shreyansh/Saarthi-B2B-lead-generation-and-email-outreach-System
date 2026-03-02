from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import csv
import io

from app.db.session import get_db
from app.db.models import User, Campaign, Lead, OutreachLog
from app.core.deps import get_current_user
from app.services.lead_generation import generate_leads_pipeline

router = APIRouter()

class LeadGenerateRequest(BaseModel):
    industry: str
    job_title: str
    location: str
    num_leads: int = 10



class LeadCreate(BaseModel):
    campaign_id: str
    name: str
    company: Optional[str] = ""
    email: EmailStr
    title: Optional[str] = ""
    location: Optional[str] = ""
    phone: Optional[str] = ""
    linkedin: Optional[str] = ""
    email_status: Optional[str] = "unknown"


class LeadBulkCreate(BaseModel):
    campaign_id: str
    leads: List[LeadCreate]


def _lead_to_dict(lead, camp_name="", latest_log=None):
    return {
        "id": str(lead.id),
        "name": lead.name,
        "company": lead.company,
        "email": lead.email,
        "title": lead.title or "",
        "location": lead.location or "",
        "phone": lead.phone or "",
        "linkedin": lead.linkedin or "",
        "status": lead.status,
        "email_status": getattr(lead, "email_status", "unknown"),
        "campaign": camp_name,
        "campaign_id": str(lead.campaign_id),
        "last_contact": latest_log.sent_at.isoformat() if latest_log and latest_log.sent_at else "",
        "reply_type": latest_log.reply_type if latest_log else "",
        "reply_status": latest_log.reply_status if latest_log else "",
        "created_at": lead.created_at.isoformat() if lead.created_at else "",
    }


@router.get("")
async def list_leads(
    campaign_id: Optional[str] = None,
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get user's campaign IDs for ownership check
    cq = await db.execute(select(Campaign.id).where(Campaign.user_id == user.id))
    campaign_ids = [r[0] for r in cq.all()]

    if not campaign_ids:
        return []

    query = select(Lead).where(Lead.campaign_id.in_(campaign_ids))

    if campaign_id:
        query = query.where(Lead.campaign_id == campaign_id)
    if status:
        query = query.where(Lead.status == status)

    query = query.order_by(Lead.created_at.desc()).limit(500)
    result = await db.execute(query)
    leads = result.scalars().all()

    out = []
    for lead in leads:
        # Get latest outreach log for this lead
        log_q = await db.execute(
            select(OutreachLog)
            .where(OutreachLog.lead_id == lead.id)
            .order_by(OutreachLog.sent_at.desc())
            .limit(1)
        )
        latest_log = log_q.scalar_one_or_none()

        # Get campaign name
        camp_q = await db.execute(select(Campaign.name).where(Campaign.id == lead.campaign_id))
        camp_name = camp_q.scalar() or ""

        out.append(_lead_to_dict(lead, camp_name, latest_log))

    return out


@router.post("", status_code=201)
async def create_lead(
    body: LeadCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify campaign ownership
    cq = await db.execute(
        select(Campaign).where(Campaign.id == body.campaign_id, Campaign.user_id == user.id)
    )
    if not cq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Campaign not found")

    lead = Lead(
        campaign_id=body.campaign_id,
        name=body.name,
        company=body.company or "",
        email=body.email,
        title=body.title or "",
        location=body.location or "",
        phone=body.phone or "",
        linkedin=body.linkedin or "",
        email_status=body.email_status or "unknown",
    )
    db.add(lead)
    await db.flush()
    return {"id": str(lead.id), "name": lead.name, "email": lead.email}


@router.post("/generate", status_code=200)
async def generate_leads(
    body: LeadGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        leads = await generate_leads_pipeline(
            job_title=body.job_title,
            industry=body.industry,
            location=body.location,
            num_leads=body.num_leads
        )
        return {"leads": leads}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/bulk", status_code=201)
async def bulk_create_leads(
    body: LeadBulkCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify campaign ownership
    cq = await db.execute(
        select(Campaign).where(Campaign.id == body.campaign_id, Campaign.user_id == user.id)
    )
    if not cq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Campaign not found")

    created = []
    for item in body.leads:
        lead = Lead(
            campaign_id=body.campaign_id,
            name=item.name,
            company=item.company or "",
            email=item.email,
            title=item.title or "",
            location=item.location or "",
            phone=item.phone or "",
            linkedin=item.linkedin or "",
            email_status=item.email_status or "unknown",
        )
        db.add(lead)
        await db.flush()
        created.append({"id": str(lead.id), "name": lead.name, "email": lead.email})

    return {"created": len(created), "leads": created}


@router.post("/import-csv", status_code=201)
async def import_csv(
    file: UploadFile = File(...),
    campaign_id: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Import leads from a CSV file. The CSV must have a header row.
    Required columns: name, email
    Optional columns: company, title, location, phone, linkedin
    Column matching is case-insensitive and strips whitespace.
    """
    # Verify campaign ownership
    cq = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    if not cq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Read and parse CSV
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    # Normalize header names
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no headers")

    # Build a mapping from normalized header -> original header
    header_map = {}
    for h in reader.fieldnames:
        norm = h.strip().lower().replace(" ", "_")
        header_map[norm] = h

    # Check required columns
    if "email" not in header_map and "email_address" not in header_map:
        raise HTTPException(status_code=400, detail="CSV must have an 'email' or 'email_address' column")
    if "name" not in header_map and "full_name" not in header_map and "first_name" not in header_map:
        raise HTTPException(status_code=400, detail="CSV must have a 'name', 'full_name', or 'first_name' column")

    created = 0
    skipped = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        # Extract email
        email = (
            row.get(header_map.get("email", ""), "")
            or row.get(header_map.get("email_address", ""), "")
        ).strip()

        if not email or "@" not in email:
            skipped += 1
            continue

        # Extract name
        name = ""
        if "full_name" in header_map:
            name = row.get(header_map["full_name"], "").strip()
        elif "name" in header_map:
            name = row.get(header_map["name"], "").strip()
        elif "first_name" in header_map:
            first = row.get(header_map["first_name"], "").strip()
            last = row.get(header_map.get("last_name", ""), "").strip()
            name = f"{first} {last}".strip()

        if not name:
            name = email.split("@")[0]

        # Extract optional fields
        company = row.get(header_map.get("company", header_map.get("company_name", "")), "").strip()
        title = row.get(header_map.get("title", header_map.get("job_title", "")), "").strip()
        location = row.get(header_map.get("location", header_map.get("city", "")), "").strip()
        phone = row.get(header_map.get("phone", header_map.get("phone_number", "")), "").strip()
        linkedin = row.get(header_map.get("linkedin", header_map.get("linkedin_url", "")), "").strip()

        # Check for duplicate email in this campaign
        dup_q = await db.execute(
            select(Lead.id).where(Lead.campaign_id == campaign_id, Lead.email == email).limit(1)
        )
        if dup_q.scalar_one_or_none():
            skipped += 1
            continue

        lead = Lead(
            campaign_id=campaign_id,
            name=name,
            company=company,
            email=email,
            title=title,
            location=location,
            phone=phone,
            linkedin=linkedin,
        )
        db.add(lead)
        created += 1

    await db.flush()

    return {
        "created": created,
        "skipped": skipped,
        "total_rows": created + skipped,
    }


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get lead with ownership check
    lead_q = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_q.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Verify ownership
    cq = await db.execute(
        select(Campaign).where(Campaign.id == lead.campaign_id, Campaign.user_id == user.id)
    )
    if not cq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Lead not found")

    # Get all outreach logs
    logs_q = await db.execute(
        select(OutreachLog).where(OutreachLog.lead_id == lead.id).order_by(OutreachLog.sent_at.asc())
    )
    logs = logs_q.scalars().all()

    camp_q = await db.execute(select(Campaign.name).where(Campaign.id == lead.campaign_id))
    camp_name = camp_q.scalar() or ""

    return {
        "id": str(lead.id),
        "name": lead.name,
        "company": lead.company,
        "email": lead.email,
        "title": lead.title or "",
        "location": lead.location or "",
        "phone": lead.phone or "",
        "linkedin": lead.linkedin or "",
        "status": lead.status,
        "email_status": getattr(lead, "email_status", "unknown"),
        "campaign": camp_name,
        "campaign_id": str(lead.campaign_id),
        "created_at": lead.created_at.isoformat() if lead.created_at else "",
        "activity": [
            {
                "id": str(log.id),
                "sequence_step": log.sequence_step,
                "subject": log.subject,
                "body": log.body,
                "sent_at": log.sent_at.isoformat() if log.sent_at else "",
                "reply_status": log.reply_status,
                "reply_type": log.reply_type,
                "followup_status": log.followup_status,
            }
            for log in logs
        ],
    }


@router.delete("/{lead_id}", status_code=200)
async def delete_lead(
    lead_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead_q = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_q.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    cq = await db.execute(
        select(Campaign).where(Campaign.id == lead.campaign_id, Campaign.user_id == user.id)
    )
    if not cq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Lead not found")

    await db.delete(lead)
    return {"deleted": True, "id": lead_id}
