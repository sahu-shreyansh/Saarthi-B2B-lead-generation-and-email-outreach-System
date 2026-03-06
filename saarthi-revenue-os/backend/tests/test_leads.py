import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
import time

from app.main import app
from app.database.database import SessionLocal
from app.database.models import User, Organization, Lead, Campaign

client = TestClient(app)

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_test_user_and_org(db: Session, suffix: str):
    email = f"user_{suffix}@test.com"
    password = "password123"
    org_name = f"Org {suffix}"
    
    # Register
    reg_response = client.post("/auth/register", json={
        "email": email,
        "password": password,
        "organization_name": org_name
    })
    reg_data = reg_response.json()
    token = reg_data["access_token"]
    
    # Fetch Me to get org_id
    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    me_data = me_response.json()
    org_id = me_data["organization_id"]
    
    return email, token, org_id

def test_lead_org_isolation_api(db: Session):
    """
    Ensures Org A's token cannot see Org B's leads via /leads API.
    """
    suffix_a = str(int(time.time() * 1000))[-6:]
    suffix_b = str(int(time.time() * 1000) + 1)[-6:]

    _, token_a, org_a_id = create_test_user_and_org(db, suffix_a)
    _, token_b, org_b_id = create_test_user_and_org(db, suffix_b)

    # 1. Create a campaign for Org A to attach lead to
    camp_a = Campaign(id=uuid4(), organization_id=org_a_id, name="Campaign A", status="DRAFT")
    db.add(camp_a)
    db.commit()

    # 2. Create a lead for Org A via API
    create_response = client.post("/leads", 
        json={
            "contact_name": "Lead A",
            "contact_email": "leada@test.com",
            "company_name": "Company A",
            "campaign_id": str(camp_a.id)
        },
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert create_response.status_code == 200
    lead_a_id = create_response.json()["id"]

    # 3. Try to fetch this lead using Org B's token
    get_response = client.get(f"/leads/{lead_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    # This should either be 404 (not found in Org B context) or 403
    assert get_response.status_code in [404, 403]

    # 4. List leads using Org B's token
    list_response = client.get("/leads", headers={"Authorization": f"Bearer {token_b}"})
    assert list_response.status_code == 200
    leads_b = list_response.json()
    # Should NOT contain lead_a
    assert all(l["id"] != lead_a_id for l in leads_b)

    # Cleanup
    db.query(Lead).filter(Lead.id == lead_a_id).delete()
    db.query(Campaign).filter(Campaign.organization_id.in_([org_a_id, org_b_id])).delete()
    db.query(User).filter(User.organization_id.in_([org_a_id, org_b_id])).delete()
    db.query(Organization).filter(Organization.id.in_([org_a_id, org_b_id])).delete()
    db.commit()
