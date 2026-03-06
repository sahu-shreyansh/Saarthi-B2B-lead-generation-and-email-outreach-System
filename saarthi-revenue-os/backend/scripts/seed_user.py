import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.database.models import Organization, User, UserOrganization
from app.core.security import get_password_hash

def run():
    db = SessionLocal()
    try:
        email = "admin@saarthi.ai"
        password = "password123"
        org_name = "Saarthi Testing"

        # Check if user already exists
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"User {email} already exists. Updating password.")
            user.password_hash = get_password_hash(password)
            db.commit()
            return

        # 1. Create Organization
        org = Organization(name=org_name)
        db.add(org)
        db.flush()

        # 2. Create User
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            is_active=True
        )
        db.add(user)
        db.flush()

        # 3. Create UserOrganization Relationship (OWNER)
        user_org = UserOrganization(
            user_id=user.id,
            org_id=org.id,
            role="OWNER" 
        )
        db.add(user_org)
        db.commit()

        print(f"Successfully seeded Test Admin:\\nEmail: {email}\\nPassword: {password}")
    except Exception as e:
        print(f"Failed to seed user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run()
