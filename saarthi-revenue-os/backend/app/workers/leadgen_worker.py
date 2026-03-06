"""
leadgen_worker.py — Production-grade Lead Generation Celery Task.

Execution Flow:
  1. Fetch job metadata from DB
  2. Route query to correct provider (Apify or SERP)
  3. Validate provider response
  4. For each lead:
     a. Deduplicate against campaign
     b. Reserve 1 credit (SELECT FOR UPDATE)
     c. Insert lead
     d. Commit — or rollback credit on failure
  5. Mark job complete

Invariants:
  - Credits deducted ONLY per successfully inserted lead
  - SELECT FOR UPDATE prevents concurrent credit overdraft
  - Credit is refunded if DB insert fails
  - Job is always marked FAILED on unrecoverable error
"""
import logging
import datetime
from typing import Optional

from app.workers.celery_app import celery_app
from app.database.database import SessionLocal
from app.database.models import LeadGenerationJob, Lead, Campaign
from app.services.billing import UsageService
from app.services.leadgen_service import fetch_leads
from app.providers.scraping.base_provider import (
    ProviderError, NetworkError, RateLimitError,
    QuotaExhaustedError, InvalidResponseError
)

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, soft_time_limit=600, time_limit=660)
def run_lead_generation_task(self, job_id: str):
    """
    Executes an async Lead Generation job.

    Reads job parameters from LeadGenerationJob table.
    Routes to Apify (maps/linkedin/website) or SERP (google_search) via leadgen_service.
    """
    db = SessionLocal()
    job: Optional[LeadGenerationJob] = None

    try:
        job = db.query(LeadGenerationJob).filter_by(id=job_id).with_for_update().first()

        if not job:
            logger.warning(f"[leadgen] Job {job_id} not found.")
            return

        if job.status != "PENDING":
            logger.info(f"[leadgen] Job {job_id} already in status '{job.status}', skipping.")
            return

        job.status = "RUNNING"
        db.commit()

        campaign = db.query(Campaign).filter_by(id=job.campaign_id).first()
        if not campaign:
            raise Exception(f"Campaign {job.campaign_id} not found")

        # ── 1. Determine provider routing from job metadata ────────
        # query_type is stored in the job's metadata JSONB (or defaults to "maps")
        meta = job.meta if hasattr(job, 'meta') and job.meta else {}
        query_type = meta.get("query_type", "maps")
        query = meta.get("query", campaign.name)
        max_results = job.total_requested or 50
        max_pages = meta.get("max_pages", 1)

        logger.info(
            f"[leadgen] Job {job_id}: query_type={query_type!r} "
            f"query={query!r} max_results={max_results}"
        )

        # ── 2. Call the provider ───────────────────────────────────
        try:
            provider_response = fetch_leads(
                query_type=query_type,
                query=query,
                max_results=max_results,
                max_pages=max_pages
            )
        except (QuotaExhaustedError, InvalidResponseError) as exc:
            # These are non-retriable — mark job failed immediately
            logger.error(f"[leadgen] Non-retriable provider error for job {job_id}: {exc}")
            _fail_job(db, job, str(exc))
            return
        except (NetworkError, RateLimitError) as exc:
            # Retriable errors — raise to trigger Celery retry with explicit exponential backoff
            logger.warning(f"[leadgen] Retriable provider error for job {job_id}: {exc}. Attempting retry (current={self.request.retries})")
            _fail_job(db, job, str(exc))
            
            backoff_schedule = [30, 120, 300] # 30s -> 2m -> 5m
            current_retry = self.request.retries
            
            if current_retry < len(backoff_schedule):
                delay = backoff_schedule[current_retry]
                raise self.retry(exc=exc, countdown=delay)
            else:
                logger.error(f"[leadgen] Exhausted all {self.max_retries} retries for job {job_id}.")
                _fail_campaign(db, job.campaign_id)
                return

        job.total_found = provider_response.total_found
        db.commit()

        logger.info(
            f"[leadgen] Provider returned {provider_response.total_found} raw results "
            f"for job {job_id} (source={provider_response.source})"
        )

        # ── 3. Process leads with credit gate ──────────────────────
        inserted = 0
        skipped_dup = 0
        skipped_nocredit = 0

        for lead_data in provider_response.results:
            email = (lead_data.email or "").lower().strip()

            # Skip leads with no email — not billable, not insertable
            if not email or "@" not in email:
                continue

            # Deduplication check (campaign-scoped)
            # Standardizing on contact_email to match models.py
            existing = db.query(Lead).filter(
                Lead.campaign_id == job.campaign_id,
                Lead.contact_email == email
            ).first()

            if existing:
                skipped_dup += 1
                continue

            # Credit gate — 1 Lead = 1 Credit, locked at row level
            has_credits = UsageService.check_and_reserve_credits(
                db, job.organization_id, required_credits=1
            )
            if not has_credits:
                skipped_nocredit += 1
                logger.warning(
                    f"[leadgen] Org {job.organization_id} exhausted credits during job {job_id}. "
                    f"Halting insertion."
                )
                break

            # Insert lead — refund credit on failure
            try:
                new_lead = Lead(
                    organization_id=job.organization_id,
                    company_name=lead_data.company,
                    contact_name=lead_data.name,
                    contact_email=email,
                    website=lead_data.website,
                    location=lead_data.location,
                    status="new",
                    source="discovery",
                    score=int(lead_data.confidence_score * 100),
                    metadata_={"domain": lead_data.domain or (email.split("@")[1] if "@" in email else None)}
                )
                db.add(new_lead)
                db.commit()
                inserted += 1

            except Exception as db_exc:
                db.rollback()
                # Refund this one credit since the lead was not inserted
                UsageService.refund_credits(db, job.organization_id, refund_amount=1)
                logger.error(
                    f"[leadgen] DB insert failed for lead {email} in job {job_id}: {db_exc}"
                )

        # ── 4. Finalize Job ────────────────────────────────────────
        job = db.query(LeadGenerationJob).filter_by(id=job_id).first()
        if job:
            job.total_inserted = inserted
            job.status = "COMPLETED"
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()

        logger.info(
            f"[leadgen] Job {job_id} COMPLETED. "
            f"inserted={inserted} skipped_dup={skipped_dup} "
            f"skipped_nocredit={skipped_nocredit}"
        )

    except Exception as exc:
        db.rollback()
        logger.exception(f"[leadgen] Unhandled exception in job {job_id}: {exc}")

        # Re-fetch job to update status (original reference may be stale after rollback)
        try:
            job = db.query(LeadGenerationJob).filter_by(id=job_id).first()
            if job and job.status not in ("COMPLETED", "FAILED"):
                _fail_job(db, job, str(exc))
        except Exception:
            logger.error(f"[leadgen] Could not update failed status for job {job_id}")

    finally:
        db.close()


def _fail_job(db, job: LeadGenerationJob, reason: str):
    """Safely marks a job as FAILED with an error message."""
    try:
        job.status = "FAILED"
        job.error_message = reason[:1000]  # Truncate to DB field limit
        job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        logger.error(f"[leadgen] Job {job.id} marked FAILED: {reason[:200]}")
    except Exception as e:
        logger.error(f"[leadgen] Could not persist FAILED status: {e}")

def _fail_campaign(db, campaign_id):
    """Marks the parent campaign as FAILED if scraping completely collapses."""
    try:
        camp = db.query(Campaign).filter_by(id=campaign_id).first()
        if camp and camp.status != "FAILED":
            camp.status = "FAILED"
            db.commit()
            logger.error(f"[leadgen] Campaign {campaign_id} permanently marked FAILED due to unrecoverable scraping errors.")
    except Exception as e:
        logger.error(f"[leadgen] Failed to mark Campaign {campaign_id} as FAILED: {e}")
