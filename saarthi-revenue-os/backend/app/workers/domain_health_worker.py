import logging
import datetime
from sqlalchemy import func
from app.workers.celery_app import celery_app
from app.database.database import SessionLocal
from app.database.models import SendingAccount, OutreachLog, DomainHealth

logger = logging.getLogger(__name__)

# Configurable Enterprise Thresholds
CRITICAL_BOUNCE_RATE = 0.05  # 5%
MIN_EMAILS_FOR_STATS = 50

@celery_app.task(bind=True)
def monitor_domain_health_task(self):
    """
    Weekly/Daily Cron Job.
    Calculates bounce rates per SendingAccount/Domain.
    Auto-pauses accounts that cross the critical threshold to protect deliverability organically.
    """
    db = SessionLocal()
    try:
        # Get all active sending accounts
        accounts = db.query(SendingAccount).filter(SendingAccount.is_active == True).all()

        for account in accounts:
            try:
                # 1. Calculate Sent vs Bounced over the last 7 days
                seven_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
                
                stats = db.query(
                    func.count(OutreachLog.id).label('total_sent'),
                    func.sum(
                        func.cast(OutreachLog.status == 'BOUNCED', func.Integer) # Use standard PG int cast
                    ).label('total_bounced')
                ).filter(
                    OutreachLog.sending_account_id == account.id,
                    OutreachLog.sent_at >= seven_days_ago
                ).first()

                total_sent = stats.total_sent or 0
                total_bounced = stats.total_bounced or 0

                if total_sent < MIN_EMAILS_FOR_STATS:
                    continue  # Not enough data for statistical significance

                bounce_rate = total_bounced / total_sent

                # Extract domain
                domain = account.email.split('@')[1] if '@' in account.email else account.email

                # 2. Update DomainHealth Record
                health = db.query(DomainHealth).filter_by(
                    org_id=account.org_id, 
                    domain=domain
                ).first()

                if not health:
                    health = DomainHealth(org_id=account.org_id, domain=domain)
                    db.add(health)
                
                health.bounce_rate = bounce_rate
                health.last_calculated_at = datetime.datetime.now(datetime.timezone.utc)
                db.commit()

                # 3. Enforcement: Auto-Pause if Critical
                if bounce_rate >= CRITICAL_BOUNCE_RATE:
                    logger.warning(
                        f"CRITICAL BOUNCE RATE: Account {account.email} hit {bounce_rate*100}%. "
                        f"Auto-pausing account to prevent domain blacklisting."
                    )
                    account.is_active = False
                    # Note: Need to optionally alert organization admins here via email or UI notification.
                    db.commit()

            except Exception as e:
                logger.error(f"Failed processing health for account {account.id}: {e}")
                db.rollback()

    except Exception as e:
        logger.error(f"Domain Health Monitor Failed globally: {e}")
    finally:
        db.close()
