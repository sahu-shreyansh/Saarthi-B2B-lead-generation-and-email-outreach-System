import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import datetime

from app.database.database import get_db
from app.database.models import Meeting
from app.core.deps import get_current_user_and_org

router = APIRouter(prefix="/meetings", tags=["Meetings"])

class MeetingCreate(BaseModel):
    lead_id: str
    title: str
    scheduled_time: datetime.datetime
    duration_minutes: int = 30
    meeting_link: Optional[str] = None

class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    scheduled_time: Optional[datetime.datetime] = None
    duration_minutes: Optional[int] = None
    meeting_link: Optional[str] = None
    status: Optional[str] = None
    calendar_event_id: Optional[str] = None

class MeetingResponse(BaseModel):
    id: str
    organization_id: str
    lead_id: str
    title: str
    scheduled_time: str
    duration_minutes: int
    meeting_link: Optional[str]
    status: str
    calendar_event_id: Optional[str]
    created_at: str
    updated_at: str

@router.post("", response_model=MeetingResponse)
def create_meeting(
    schema: MeetingCreate,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        lead_uuid = uuid.UUID(schema.lead_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Lead ID")
        
    meeting = Meeting(
        organization_id=active_org_id,
        lead_id=lead_uuid,
        title=schema.title,
        scheduled_time=schema.scheduled_time,
        duration_minutes=schema.duration_minutes,
        meeting_link=schema.meeting_link,
        status="scheduled"
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    return {
        "id": str(meeting.id),
        "organization_id": str(meeting.organization_id),
        "lead_id": str(meeting.lead_id),
        "title": meeting.title,
        "scheduled_time": meeting.scheduled_time.isoformat(),
        "duration_minutes": meeting.duration_minutes,
        "meeting_link": meeting.meeting_link,
        "status": meeting.status,
        "calendar_event_id": meeting.calendar_event_id,
        "created_at": meeting.created_at.isoformat(),
        "updated_at": meeting.updated_at.isoformat()
    }

@router.get("", response_model=List[MeetingResponse])
def list_meetings(
    skip: int = 0, limit: int = 100,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    meetings = db.query(Meeting).filter(Meeting.organization_id == active_org_id).order_by(Meeting.scheduled_time.asc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(m.id),
            "organization_id": str(m.organization_id),
            "lead_id": str(m.lead_id),
            "title": m.title,
            "scheduled_time": m.scheduled_time.isoformat(),
            "duration_minutes": m.duration_minutes,
            "meeting_link": m.meeting_link,
            "status": m.status,
            "calendar_event_id": m.calendar_event_id,
            "created_at": m.created_at.isoformat(),
            "updated_at": m.updated_at.isoformat()
        } for m in meetings
    ]

@router.patch("/{id}", response_model=MeetingResponse)
def update_meeting(
    id: str,
    schema: MeetingUpdate,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        meeting_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Meeting ID")
        
    meeting = db.query(Meeting).filter(Meeting.id == meeting_uuid, Meeting.organization_id == active_org_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    update_data = schema.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(meeting, key, value)
        
    db.commit()
    db.refresh(meeting)
    
    return {
        "id": str(meeting.id),
        "organization_id": str(meeting.organization_id),
        "lead_id": str(meeting.lead_id),
        "title": meeting.title,
        "scheduled_time": meeting.scheduled_time.isoformat(),
        "duration_minutes": meeting.duration_minutes,
        "meeting_link": meeting.meeting_link,
        "status": meeting.status,
        "calendar_event_id": meeting.calendar_event_id,
        "created_at": meeting.created_at.isoformat(),
        "updated_at": meeting.updated_at.isoformat()
    }

@router.delete("/{id}")
def delete_meeting(
    id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    try:
        meeting_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Meeting ID")
        
    meeting = db.query(Meeting).filter(Meeting.id == meeting_uuid, Meeting.organization_id == active_org_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    db.delete(meeting)
    db.commit()
    return {"message": "Meeting deleted"}

@router.post("/{id}/send-confirmation")
def send_meeting_confirmation(
    id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """Sends a meeting confirmation email via celery."""
    current_user, active_org_id, role = deps
    try:
        meeting_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Meeting ID")
        
    meeting = db.query(Meeting).filter(Meeting.id == meeting_uuid, Meeting.organization_id == active_org_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    from app.tasks.inbox_pipeline import schedule_meeting_task
    # Usually this would be send_meeting_confirmation, but spec requires schedule_meeting pipeline
    task = schedule_meeting_task.delay(str(meeting.lead_id), str(meeting.id))
    
    return {"message": "Meeting confirmation initiated", "task_id": str(task.id)}
