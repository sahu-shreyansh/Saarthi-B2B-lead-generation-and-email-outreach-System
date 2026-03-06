import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Tuple

from app.database.models import Subscription, UsageTracking, StripeEvent, ProviderRateLimit
import datetime


class UsageService:
    """
    Enterprise-grade Usage & Billing Gateway.
    Implements Row-Level Locking to prevent Celery race conditions.
    """

    @staticmethod
    def initialize_org_subscription(db: Session, organization_id: uuid.UUID) -> Subscription:
        """Create a default free tier subscription for a new org."""
        sub = db.query(Subscription).filter(Subscription.organization_id == organization_id).first()
        if not sub:
            sub = Subscription(
                organization_id=organization_id,
                plan="FREE",
                monthly_credit_limit=100,  # 100 free credits
                credits_used=0,
                status="ACTIVE"
            )
            db.add(sub)
            db.commit()
            db.refresh(sub)
        return sub

    @staticmethod
    def check_and_reserve_credits(db: Session, organization_id: uuid.UUID, required_credits: int) -> bool:
        """
        Locks the subscription row, checks if sufficient credits exist, 
        and reserves them immediately if available.
        """
        sub = db.query(Subscription).filter(
            Subscription.organization_id == organization_id
        ).with_for_update().first()

        if not sub or sub.status != "ACTIVE":
            return False

        remaining = sub.monthly_credit_limit - sub.credits_used
        
        if remaining >= required_credits:
            sub.credits_used += required_credits
            return True
            
        return False

    @staticmethod
    def get_remaining_credits(db: Session, organization_id: uuid.UUID) -> int:
        """
        Returns the remaining credits for an org without locking or reserving.
        """
        sub = db.query(Subscription).filter(
            Subscription.organization_id == organization_id
        ).first()

        if not sub or sub.status != "ACTIVE":
            return 0
            
        return max(0, sub.monthly_credit_limit - sub.credits_used)

    @staticmethod
    def refund_credits(db: Session, organization_id: uuid.UUID, refund_amount: int):
        """
        Refund credits if an external API action fails after reservation.
        """
        sub = db.query(Subscription).filter(
            Subscription.organization_id == organization_id
        ).with_for_update().first()

        if sub:
            sub.credits_used = max(0, sub.credits_used - refund_amount)
            db.commit()

    @staticmethod
    def check_limits_before_send(db: Session, organization_id: uuid.UUID, sending_account_id: uuid.UUID) -> bool:
        """
        Enforces monthly subscription limits and daily provider rate limits.
        """
        today = datetime.datetime.now(datetime.timezone.utc).date()
        month_str = today.strftime("%Y-%m")
        
        sub = db.query(Subscription).filter_by(organization_id=organization_id).with_for_update().first()
        if not sub or sub.status != "ACTIVE":
            return False
            
        usage = db.query(UsageTracking).filter_by(organization_id=organization_id, month=month_str).with_for_update().first()
        if usage and usage.emails_sent >= sub.monthly_credit_limit:
             return False 
            
        date_str = today.strftime("%Y-%m-%d")
        rate_limit = db.query(ProviderRateLimit).filter_by(
            organization_id=organization_id, sending_account_id=sending_account_id, date=date_str
        ).with_for_update().first()

        daily_limit = 50 
        
        if rate_limit and rate_limit.emails_sent_today >= daily_limit:
            return False 

        return True

    @staticmethod
    def log_send(db: Session, organization_id: uuid.UUID, sending_account_id: uuid.UUID):
        """
        Increment usage trackers atomically after a successful send.
        """
        today = datetime.datetime.now(datetime.timezone.utc).date()
        month_str = today.strftime("%Y-%m")
        date_str = today.strftime("%Y-%m-%d")

        usage = db.query(UsageTracking).filter_by(organization_id=organization_id, month=month_str).with_for_update().first()
        if not usage:
            usage = UsageTracking(organization_id=organization_id, month=month_str, emails_sent=1)
            db.add(usage)
        else:
            usage.emails_sent += 1

        rate_limit = db.query(ProviderRateLimit).filter_by(
            organization_id=organization_id, sending_account_id=sending_account_id, date=date_str
        ).with_for_update().first()
        
        if not rate_limit:
            rate_limit = ProviderRateLimit(
                organization_id=organization_id, sending_account_id=sending_account_id, date=date_str, emails_sent_today=1
            )
            db.add(rate_limit)
        else:
            rate_limit.emails_sent_today += 1

        db.commit()

    @staticmethod
    def process_stripe_webhook_event(db: Session, event_id: str, event_type: str, payload: dict) -> Tuple[bool, str]:
        try:
            stripe_event = StripeEvent(
                event_id=event_id,
                type=event_type,
                payload=payload
            )
            db.add(stripe_event)
            db.commit()
        except IntegrityError:
            db.rollback()
            return False, f"Duplicate event_id {event_id} ignored"

        return True, "Event queued for processing"
