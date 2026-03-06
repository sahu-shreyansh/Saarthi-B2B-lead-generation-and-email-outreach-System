import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
import time

from app.main import app
from app.database.database import SessionLocal
from app.database.models import User, Organization

client = TestClient(app)

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_registration_and_login(db: Session):
    """
    Tests the full auth cycle: Register -> Login -> Get Me
    """
    unique_suffix = str(int(time.time() * 1000))[-8:]
    email = f"test_{unique_suffix}@example.com"
    password = "password123"
    org_name = f"Test Org {unique_suffix}"

    # 1. Register
    reg_response = client.post("/auth/register", json={
        "email": email,
        "password": password,
        "organization_name": org_name
    })
    assert reg_response.status_code == 200
    reg_data = reg_response.json()
    assert "access_token" in reg_data
    token = reg_data["access_token"]

    # 2. Get Me (to verify registration worked and get org_id)
    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == email
    assert me_data.get("organization_id") is not None

    # 3. Get Me
    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == email
    assert me_data["organization_id"] is not None

    # Cleanup (Optional, but good for test database health if not using a fresh one)
    user = db.query(User).filter(User.email == email).first()
    if user:
        org_id = user.organization_id
        db.delete(user)
        if org_id:
            org = db.query(Organization).filter(Organization.id == org_id).first()
            if org:
                db.delete(org)
        db.commit()

def test_login_invalid_password(db: Session):
    unique_suffix = str(int(time.time() * 1000))[-8:]
    email = f"fail_{unique_suffix}@example.com"
    
    # Create user via registration
    client.post("/auth/register", json={
        "email": email,
        "password": "correct_password",
        "organization_name": "Fail Org"
    })

    # Try login with wrong password
    response = client.post("/auth/login", json={
        "email": email,
        "password": "wrong_password"
    })
    # Should be 400 (Incorrect email or password) per auth.py
    assert response.status_code == 400
