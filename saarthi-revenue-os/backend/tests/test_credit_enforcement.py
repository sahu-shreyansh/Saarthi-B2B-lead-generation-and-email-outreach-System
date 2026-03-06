import pytest
import threading
from sqlalchemy.orm import Session
from uuid import uuid4

from app.database.database import SessionLocal
from app.database.models import Organization, Subscription
from sqlalchemy import select

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_credit_enforcement_race_condition(db: Session):
    """
    CRITICAL ENTERPRISE REQUIREMENT
    Simulates 10 concurrent worker threads attempting to deduct credits simultaneously.
    Verifies that the row-level locking (SELECT FOR UPDATE) prevents credits
    from being drawn past zero via race conditions.
    """
    org_id = uuid4()
    org = Organization(id=org_id, name="Concurrency Test Org")
    
    # Subscription holds the credits
    sub_id = uuid4()
    sub = Subscription(id=sub_id, org_id=org_id, monthly_credit_limit=5, credits_used=0)
    
    db.add_all([org, sub])
    db.commit()

    successful_deductions = []
    failed_deductions = []
    
    def worker_attempt_deduction():
        # Each worker must spawn its own session
        local_db = SessionLocal()
        try:
            # Attempt to deduct 1 credit for an AI inference via pessimistic row lock
            sub_record = local_db.execute(
                select(Subscription)
                .where(Subscription.org_id == org_id)
                .with_for_update()
            ).scalar_one()

            if (sub_record.monthly_credit_limit - sub_record.credits_used) >= 1:
                sub_record.credits_used += 1
                local_db.commit()
                successful_deductions.append(True)
            else:
                failed_deductions.append(True)
        except Exception:
            failed_deductions.append(True)
        finally:
            local_db.close()

    # Spawn 10 concurrent workers
    threads = []
    for _ in range(10):
        t = threading.Thread(target=worker_attempt_deduction)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # Validate absolute consistency
    final_sub = db.query(Subscription).filter(Subscription.org_id == org_id).first()
    
    # 1. Exactly 5 deductions must have succeeded
    assert len(successful_deductions) == 5
    # 2. Exactly 5 deductions must have failed
    assert len(failed_deductions) == 5
    # 3. Credits must be exactly 0, meaning 5 used out of 5
    assert final_sub.credits_used == 5
    assert (final_sub.monthly_credit_limit - final_sub.credits_used) == 0

    # Cleanup
    db.query(Subscription).filter(Subscription.org_id == org_id).delete(synchronize_session=False)
    db.query(Organization).filter(Organization.id == org_id).delete(synchronize_session=False)
    db.commit()
