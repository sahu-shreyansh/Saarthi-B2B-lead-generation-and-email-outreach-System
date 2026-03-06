import time
import uuid
import uuid
from typing import Dict, Any
from loguru import logger
from celery import shared_task

from app.database.database import SessionLocal
from app.database.models import Lead, Task, WorkerLog
from app.services.lead_scoring_service import LeadScoringService

@shared_task(name="run_discovery_task", bind=True)
def run_discovery_task(self, industry: str, location: str, limit: int, organization_id: str):
    logger.info(f"Starting discovery task {self.request.id} for industry={industry}")
    db = SessionLocal()
    start_time = time.time()
    
    try:
        from app.providers.scraping.serp_provider import SERPProvider
        from app.services.website_crawler import WebsiteCrawlerService
        
        org_uuid = uuid.UUID(organization_id)
        
        # 1. Search for company websites using SERP
        serp = SERPProvider()
        query = f"top {industry} companies in {location}"
        search_response = serp.search(query=query, max_pages=1) # 10 results
        
        found_leads_count = 0
        crawler = WebsiteCrawlerService(db=db)
        
        for result in search_response.results:
            if found_leads_count >= limit:
                break
                
            if result.website:
                # 2. Extract contacts from the domain
                logger.info(f"Crawling website: {result.website}")
                contacts = crawler.extract_contacts_from_domain(
                    url=result.website,
                    org_id=organization_id,
                    campaign_id=None # Discovery is campaign-agnostic initially
                )
                
                for contact in contacts:
                    if found_leads_count >= limit:
                        break
                        
                    email = contact.get("email")
                    if email and "@" in email:
                        new_lead = Lead(
                            organization_id=org_uuid,
                            company_name=result.company or result.name or "Unknown",
                            contact_name=contact.get("name") or "Decision Maker",
                            contact_email=email,
                            industry=industry,
                            location=location,
                            source="discovery",
                            status="new",
                            metadata_={
                                "title": contact.get("title"),
                                "linkedin": contact.get("linkedin"),
                                "website": result.website,
                                "discovery_query": query
                            }
                        )
                        db.add(new_lead)
                        found_leads_count += 1
                        
        # Update Task Status
        db_task = db.query(Task).filter(Task.id == str(self.request.id)).first()
        if db_task:
            db_task.status = "COMPLETED"
            db_task.progress = 100
            db_task.result = f"Found {found_leads_count} leads."
            
        db.commit()
    except Exception as e:
        db.rollback()
        db_task = db.query(Task).filter(Task.id == str(self.request.id)).first()
        if db_task:
            db_task.status = "FAILED"
            db_task.error_message = str(e)
            db.commit()
        logger.error(f"Discovery task failed: {str(e)}")
    finally:
        # Log to WorkerLogs
        runtime = time.time() - start_time
        log = WorkerLog(task_id=str(self.request.id or uuid.uuid4()), task_name="run_discovery_task", runtime_seconds=runtime, status="SUCCESS", error_logs="")
        db.add(log)
        db.commit()
        db.close()


@shared_task(name="score_lead_task", bind=True)
def score_lead_task(self, lead_id: str):
    logger.info(f"Starting score task for lead {lead_id}")
    db = SessionLocal()
    start_time = time.time()
    try:
        lead_uuid = uuid.UUID(lead_id)
        lead = db.query(Lead).filter(Lead.id == lead_uuid).first()
        if not lead:
            return "Lead not found"
            
        data = {
            "company_name": lead.company_name,
            "industry": lead.industry,
            "description": lead.description
        }
        
        score, factors = LeadScoringService.score_lead(db, str(lead.organization_id), str(lead.id), data)
        
        lead.score = score
        db.commit()
    except Exception as e:
        logger.error(f"Score task failed: {str(e)}")
    finally:
        runtime = time.time() - start_time
        log = WorkerLog(task_id=str(self.request.id or uuid.uuid4()), task_name="score_lead_task", runtime_seconds=runtime, status="SUCCESS", error_logs="")
        db.add(log)
        db.commit()
        db.close()

@shared_task(name="extract_metadata_task", bind=True)
def extract_metadata_task(self, lead_id: str):
    logger.info(f"Starting enrich metadata task for lead {lead_id}")
    db = SessionLocal()
    try:
        lead_uuid = uuid.UUID(lead_id)
        lead = db.query(Lead).filter(Lead.id == lead_uuid).first()
        if lead:
            # Fake enrichment
            meta = lead.metadata_ or {}
            meta["enriched_at"] = time.time()
            meta["company_size"] = "100-500 employees"
            lead.metadata_ = meta
            db.commit()
    finally:
        db.close()
