import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
import time

from app.tasks.lead_pipeline import run_discovery_task
from app.database.database import SessionLocal
from app.database.models import Lead, Task, Organization

class MockSERPResult:
    def __init__(self, website, company=None):
        self.website = website
        self.company = company
        self.name = company or "Mock Co"

class MockSERPResponse:
    def __init__(self, results):
        self.results = results

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_run_discovery_task_success(db: SessionLocal):
    """
    Tests run_discovery_task with mocked external providers.
    """
    org_id = uuid4()
    # Ensure org exists
    org = Organization(id=org_id, name="Test Pipeline Org")
    db.add(org)
    db.commit()

    # Create a task record to be updated
    task_id = str(uuid4())
    db_task = Task(id=task_id, task_name="run_discovery_task", status="QUEUED", progress=0)
    db.add(db_task)
    db.commit()

    # Mock SERPProvider
    mock_serp = MagicMock()
    mock_serp.search.return_value = MockSERPResponse([
        MockSERPResult("https://tesla.com", "Tesla"),
        MockSERPResult("https://spacex.com", "SpaceX")
    ])

    # Mock WebsiteCrawlerService
    mock_crawler = MagicMock()
    mock_crawler.extract_contacts_from_domain.return_value = [
        {"name": "Elon Musk", "email": "elon@tesla.com", "title": "CEO"},
        {"name": "Gwynne Shotwell", "email": "gwynne@spacex.com", "title": "COO"}
    ]

    # Patch the classes inside the task function
    with patch("app.providers.scraping.serp_provider.SERPProvider", return_value=mock_serp), \
         patch("app.services.website_crawler.WebsiteCrawlerService", return_value=mock_crawler):
        
        # We need to mock the 'self' bind for celery task
        mock_self = MagicMock()
        mock_self.request.id = task_id
        
        run_discovery_task(mock_self, "EV", "Austin", 10, str(org_id))

    # Verify results in DB
    db.expire_all()
    leads = db.query(Lead).filter(Lead.organization_id == org_id).all()
    assert len(leads) == 2
    emails = [l.contact_email for l in leads]
    assert "elon@tesla.com" in emails
    assert "gwynne@spacex.com" in emails

    # Verify task status
    final_task = db.query(Task).filter(Task.id == task_id).first()
    assert final_task.status == "COMPLETED"
    assert "Found 2 leads" in final_task.result

    # Cleanup
    db.query(Lead).filter(Lead.organization_id == org_id).delete()
    db.query(Task).filter(Task.id == task_id).delete()
    db.query(Organization).filter(Organization.id == org_id).delete()
    db.commit()
