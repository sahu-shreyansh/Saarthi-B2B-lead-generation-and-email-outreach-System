import os
import sys
import uuid

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.database.models import Organization, Campaign, User
from app.tasks.lead_pipeline import trigger_enterprise_pipeline

def run():
    print("Initiating Master Pipeline Verification Test...")
    db = SessionLocal()
    
    try:
        # Create mock user
        user = User(email="test@saarthi.ai", auth_provider="local")
        db.add(user)
        db.flush()

        # Create mock org and campaign
        org = Organization(name="Test Verification Org", join_policy="OPEN")
        db.add(org)
        db.flush()
        
        camp = Campaign(
            org_id=org.id,
            name="AI Automated Master Campaign",
            created_by=user.id # Assigned actual DB user
        )
        db.add(camp)
        db.commit()
        
        print(f"Created Test Org: {org.id}")
        print(f"Created Test Camp: {camp.id}")
        
        task_id = trigger_enterprise_pipeline(
            query="B2B SaaS companies in NY",
            org_id=str(org.id),
            campaign_id=str(camp.id)
        )
        print(f"\\nSUCCESS! Dispatched Master Enterprise Pipeline Chain.\\nTask ID: {task_id}")
        
    except Exception as e:
        print(f"FAIlURE: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run()
