from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

from app.core.settings import settings

# ──────────────────────────────────────────────────────────────────────
# Named Exchanges
# ──────────────────────────────────────────────────────────────────────
default_exchange = Exchange("default", type="direct")
ai_exchange = Exchange("ai", type="direct")
email_exchange = Exchange("email", type="direct")
inbox_exchange = Exchange("inbox", type="direct")
scraping_exchange = Exchange("scraping", type="direct")
lead_gen_exchange = Exchange("lead_generation", type="direct")

celery_app = Celery(
    "saarthi_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    set_as_current=True,
    include=[
        "app.tasks.lead_pipeline",
        "app.tasks.campaign_pipeline",
        "app.tasks.inbox_pipeline",
        "app.tasks.intelligence_pipeline",
        "app.tasks.followup_pipeline"
    ]
)

celery_app.set_default()
print(f"CELERY_APP_INIT: Broker is {celery_app.conf.broker_url}")

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_ignore_result=False,

    # ── Declare named queues ──
    task_queues=(
        Queue("default",         default_exchange,  routing_key="default"),
        Queue("lead_generation", lead_gen_exchange, routing_key="lead_generation"),
        Queue("scraping",        scraping_exchange, routing_key="scraping"),
        Queue("ai",              ai_exchange,       routing_key="ai"),
        Queue("email",           email_exchange,    routing_key="email"),
        Queue("inbox",           inbox_exchange,    routing_key="inbox"),
    ),
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",

    # ── Route tasks to their dedicated queues ──
    task_routes={
        # Lead discovery pipeline
        "run_discovery_task":      {"queue": "lead_generation"},
        "score_lead_task":         {"queue": "ai"},
        "extract_metadata_task":   {"queue": "ai"},

        # Scraping
        "app.tasks.intelligence_pipeline.crawl_website_task":    {"queue": "scraping"},
        "app.tasks.intelligence_pipeline.extract_metadata_task": {"queue": "ai"},
        "app.tasks.intelligence_pipeline.score_lead_task":       {"queue": "ai"},

        # Campaign / email
        "run_campaign":     {"queue": "lead_generation"},
        "send_email_task":  {"queue": "email"},

        # Inbox / reply
        "fetch_new_messages_task": {"queue": "inbox"},
        "classify_message_task":   {"queue": "inbox"},
        "generate_reply_task":     {"queue": "ai"},
        "run_followup_campaign":   {"queue": "lead_generation"},

        # Meetings
        "schedule_meeting_task":   {"queue": "ai"},
    },
)

# ── Automated schedules ────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    "process-outbound-sequence": {
        "task": "process_outbound_sequence_task",
        "schedule": crontab(minute="*"), # Every minute
    },
    "fetch-inbox-messages": {
        "task": "fetch_new_messages_task",
        "schedule": crontab(minute="*/5"),
        "args": ("00000000-0000-0000-0000-000000000000",)
    },
    "run-followup-daily": {
        "task": "run_followup_campaign",
        "schedule": crontab(hour=0, minute=0),  # Midnight UTC
    }
}
