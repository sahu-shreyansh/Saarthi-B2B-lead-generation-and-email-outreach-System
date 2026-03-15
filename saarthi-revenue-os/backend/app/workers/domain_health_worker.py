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

from app.core.database_router import get_engine_for_org
from sqlalchemy.orm import sessionmaker
from app.database.models import OrganizationDatabaseConfig

def process_domain_health_for_session(db: SessionLocal):
    """Internal helper to process domain health for a given database session."""
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
                        func.cast(OutreachLog.status == 'BOUNCED', func.Integer)
                    ).label('total_bounced')
                ).filter(
                    OutreachLog.sending_account_id == account.id,
                    OutreachLog.sent_at >= seven_days_ago
                ).first()

                total_sent = stats.total_sent or 0
                total_bounced = stats.total_bounced or 0

                if total_sent < MIN_EMAILS_FOR_STATS:
                    continue  

                bounce_rate = total_bounced / total_sent
                domain = account.email.split('@')[1] if '@' in account.email else account.email

                # 2. Update DomainHealth Record
                health = db.query(DomainHealth).filter_by(
                    org_id=account.organization_id, 
                    domain=domain
                ).first()

                if not health:
                    health = DomainHealth(org_id=account.organization_id, domain=domain)
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
                    db.commit()

            except Exception as e:
                logger.error(f"Failed processing health for account {account.id}: {e}")
                db.rollback()
    finally:
        db.close()

@celery_app.task(bind=True)
def monitor_domain_health_task(self):
    """
    Weekly/Daily Cron Job.
    Calculates bounce rates per SendingAccount/Domain across ALL databases.
    """
    platform_db = SessionLocal()
    try:
        # 1. Process Platform DB
        process_domain_health_for_session(platform_db)

        # 2. Process External DBs
        platform_db = SessionLocal() # Re-open
        external_configs = platform_db.query(OrganizationDatabaseConfig).filter(
            OrganizationDatabaseConfig.mode == "external"
        ).all()

        for config in external_configs:
            try:
                engine = get_engine_for_org(config.organization_id)
                Session = sessionmaker(bind=engine)
                process_domain_health_for_session(Session())
            except Exception as e:
                logger.error(f"Failed to process health for external org {config.organization_id}: {e}")

    finally:
        platform_db.close()
