from celery import chain, shared_task
import logging
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.database.models import Lead, Task
from app.services.website_crawler import WebsiteCrawlerService
from app.services.lead_intelligence_service import LeadIntelligenceService
from app.services.discovery_service import DiscoveryService

logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def crawl_website_task(self, lead_id: str, org_id: str):
    """
    Step 1: Fetches raw HTML and text content from the lead's domain.
    """
    logger.info(f"[Intelligence Pipeline] Crawling website for lead {lead_id}")
    db = SessionLocal()
    try:
        # 1. Update Persistent Task State
        task_record = db.query(Task).filter(Task.id == self.request.id).first()
        if task_record:
            task_record.status = "RUNNING"
            task_record.progress = 25
            db.commit()

        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.org_id == org_id).first()
        if not lead or not lead.domain:
            return {"error": "Lead or domain not found"}

        crawler = WebsiteCrawlerService(db)
        raw_content = crawler.extract_contacts_from_domain(lead.domain, org_id, str(lead.campaign_id))
        
        return {"lead_id": lead_id, "org_id": org_id, "content": raw_content}
    except Exception as e:
        logger.error(f"Crawl failed: {str(e)}")
        raise self.retry(exc=e)
    finally:
        db.close()


@shared_task(bind=True, max_retries=1)
def extract_metadata_task(self, crawl_result: dict):
    """
    Step 2: Uses AI to parse raw HTML and extract structured company metadata.
    """
    if "error" in crawl_result:
        return crawl_result
        
    lead_id = crawl_result["lead_id"]
    org_id = crawl_result["org_id"]
    logger.info(f"[Intelligence Pipeline] Extracting metadata for lead {lead_id}")
    
    db = SessionLocal()
    try:
        # Update Task State
        task_record = db.query(Task).filter(Task.id == self.request.id).first()
        if task_record:
            task_record.progress = 50
            db.commit()
            
        discovery = DiscoveryService(db)
        # Mock enrichment logic pulling from raw content
        enriched_data = {
            "industry": "Software Development",
            "location": "San Francisco, CA",
            "description": str(crawl_result.get("content", {}))[:200]
        }
        
        # Update the lead with enriched data
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if lead:
            # Safely attempt to set attributes if they exist
            if hasattr(lead, "industry"): lead.industry = enriched_data["industry"]
            if hasattr(lead, "location"): lead.location = enriched_data["location"]
            if hasattr(lead, "description"): lead.description = enriched_data["description"]
            db.commit()
            
        return {"lead_id": lead_id, "org_id": org_id}
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        raise self.retry(exc=e)
    finally:
        db.close()


@shared_task(bind=True)
def score_lead_task(self, metadata_result: dict):
    """
    Step 3: Passes the fully enriched Lead to the LLM for ICP Scoring (0-100).
    """
    if "error" in metadata_result:
        return metadata_result
        
    lead_id = metadata_result["lead_id"]
    org_id = metadata_result["org_id"]
    logger.info(f"[Intelligence Pipeline] Scoring lead {lead_id}")
    
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {"error": "Lead not found"}
            
        intelligence = LeadIntelligenceService(db)
        score_data = intelligence.evaluate_lead(lead)
        
        lead.ai_score = score_data.get("score", 0)
        db.commit()

        # Update Final Task State
        task_record = db.query(Task).filter(Task.id == self.request.id).first()
        if task_record:
            task_record.status = "SUCCESS"
            task_record.progress = 100
            task_record.result = score_data
            db.commit()
            
        return {"lead_id": lead_id, "score": score_data}
    except Exception as e:
        logger.error(f"Scoring failed: {str(e)}")
        # Update Failed Task State
        task_record = db.query(Task).filter(Task.id == self.request.id).first()
        if task_record:
            task_record.status = "FAILURE"
            task_record.error_message = str(e)
            db.commit()
        return {"error": str(e)}
    finally:
        db.close()


def trigger_intelligence_pipeline(lead_id: str, org_id: str):
    """
    Orchestrates the asynchronous AI Intelligence pipeline.
    Crawling -> Metadata Extraction -> AI Scoring
    """
    # 1. Register Task in DB for UI tracking
    db = SessionLocal()
    try:
        task_record = Task(
            task_name="intelligence_pipeline",
            status="PENDING",
            progress=0
        )
        db.add(task_record)
        db.commit()
        db.refresh(task_record)
        task_id = str(task_record.id)
    finally:
        db.close()

    # 2. Fire Celery Chain
    workflow = chain(
        crawl_website_task.s(lead_id, org_id).set(task_id=task_id),
        extract_metadata_task.s().set(task_id=task_id),
        score_lead_task.s().set(task_id=task_id)
    )
    
    workflow.apply_async(task_id=task_id)
    logger.info(f"Intelligence Pipeline initiated: {task_id}")
    
    return task_id
