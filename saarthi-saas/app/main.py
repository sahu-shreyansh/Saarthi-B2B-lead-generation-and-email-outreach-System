from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.db.session import engine
from app.db.models import Base


scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────
    # Create all tables (dev convenience — use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Register cron jobs
    from app.workers.reply_worker import poll_replies
    from app.workers.followup_worker import run_sequences

    scheduler.add_job(poll_replies, "interval", minutes=15, id="reply_poll")
    scheduler.add_job(run_sequences, "cron", hour=9, id="daily_sequence")
    scheduler.start()

    yield

    # ── Shutdown ──────────────────────────────────
    scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ─────────────────────────────
from app.routers import auth, dashboard, campaigns, leads, outreach, inbox, settings as settings_router, billing

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
app.include_router(leads.router, prefix="/leads", tags=["Leads"])
app.include_router(outreach.router, prefix="/outreach", tags=["Outreach"])
app.include_router(inbox.router, prefix="/inbox", tags=["Inbox"])
app.include_router(settings_router.router, prefix="/settings", tags=["Settings"])
app.include_router(billing.router, prefix="/billing", tags=["Billing"])


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
