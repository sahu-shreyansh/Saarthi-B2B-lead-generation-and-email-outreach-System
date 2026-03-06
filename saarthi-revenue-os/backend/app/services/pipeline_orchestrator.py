import uuid
from sqlalchemy.orm import Session
from app.database.models import Task
from app.tasks.lead_pipeline import run_discovery_task
from app.tasks.campaign_pipeline import run_campaign
from app.tasks.inbox_pipeline import fetch_new_messages_task, classify_message_task, generate_reply_task

class PipelineOrchestrator:
    @staticmethod
    def start_discovery(db: Session, industry: str, location: str, limit: int, organization_id: str):
        """Kicks off the lead discovery pipeline."""
        task = run_discovery_task.delay(industry, location, limit, organization_id)
        
        # Store task stub in database
        db_task = Task(
            id=task.id,
            task_name="run_discovery_task",
            status="QUEUED",
            progress=0
        )
        db.add(db_task)
        db.commit()
        return task.id

    @staticmethod
    def start_campaign(db: Session, campaign_id: str):
        """Kicks off a specific campaign outreach."""
        task = run_campaign.delay(campaign_id)
        return task.id

    @staticmethod
    def process_inbox(db: Session, organization_id: str):
        """Kicks off inbox message fetching for an organization."""
        task = fetch_new_messages_task.delay(organization_id)
        return task.id

    @staticmethod
    def trigger_reply(db: Session, message_id: str):
        """Triggers AI reply generation for a specific message."""
        task = generate_reply_task.delay(message_id)
        return task.id

    @staticmethod
    def trigger_classification(db: Session, message_id: str):
        """Triggers AI intent classification for a specific message."""
        task = classify_message_task.delay(message_id)
        return task.id
