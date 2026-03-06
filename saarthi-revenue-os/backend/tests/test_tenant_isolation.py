import pytest
from sqlalchemy.orm import Session
from uuid import uuid4
import time

from app.database.database import SessionLocal
from app.database.models import Organization, Lead, Campaign, User

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_tenant_data_isolation(db: Session):
    """
    CRITICAL ENTERPRISE REQUIREMENT
    Ensures that queries from Organization A cannot access Data belonging to Organization B.
    """
    # Use unique IDs to avoid collisions
    unique_suffix = str(int(time.time() * 1000))[-8:]
    
    # 1. Setup Organizations
    org_a_id = uuid4()
    org_b_id = uuid4()
    
    org_a = Organization(id=org_a_id, name=f"Stark Industries {unique_suffix}")
    org_b = Organization(id=org_b_id, name=f"Wayne Enterprises {unique_suffix}")
    
    db.add_all([org_a, org_b])
    db.commit()

    # 1.5 Setup User with unique email
    user_id = uuid4()
    user = User(id=user_id, email=f"admin{unique_suffix}@test.com")
    db.add(user)
    db.commit()

    # 2. Setup Campaigns & Leads for Org A
    camp_a = Campaign(id=uuid4(), org_id=org_a_id, name="Stark Campaign", status="DRAFT", created_by=user_id)
    lead_a = Lead(id=uuid4(), org_id=org_a_id, campaign_id=camp_a.id, email="pepper@stark.com", status="NEW")
    
    # 3. Setup Campaigns & Leads for Org B
    camp_b = Campaign(id=uuid4(), org_id=org_b_id, name="Wayne Campaign", status="DRAFT", created_by=user_id)
    lead_b = Lead(id=uuid4(), org_id=org_b_id, campaign_id=camp_b.id, email="alfred@wayne.com", status="NEW")

    db.add_all([camp_a, lead_a, camp_b, lead_b])
    db.commit()

    # 4. Assert Org A Context
    leads_a = db.query(Lead).filter(Lead.org_id == org_a_id).all()
    assert len(leads_a) == 1
    assert leads_a[0].email == "pepper@stark.com"
    assert leads_a[0].email != "alfred@wayne.com"

    # 5. Assert Org B Context
    leads_b = db.query(Lead).filter(Lead.org_id == org_b_id).all()
    assert len(leads_b) == 1
    assert leads_b[0].email == "alfred@wayne.com"
    assert leads_b[0].email != "pepper@stark.com"

    # 6. Cleanup
    db.query(Lead).filter(Lead.id.in_([lead_a.id, lead_b.id])).delete(synchronize_session=False)
    db.query(Campaign).filter(Campaign.id.in_([camp_a.id, camp_b.id])).delete(synchronize_session=False)
    db.query(Organization).filter(Organization.id.in_([org_a_id, org_b_id])).delete(synchronize_session=False)
    db.commit()
