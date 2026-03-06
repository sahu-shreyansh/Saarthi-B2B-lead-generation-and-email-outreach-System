from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.database.database import get_db
from app.middleware.org_isolation import OrgIsolationMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

# Import Routers
from app.routers import leadgen, auth, campaigns, dashboard, leads, inbox, sending_accounts, billing, stripe, intelligence, tasks, discovery, meetings, settings as settings_router, webhooks

app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-tenant B2B Outreach SaaS Backend",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Strict Multi-Tenant Org Isolation Middleware
app.add_middleware(OrgIsolationMiddleware)

# 3. Redis Token Bucket Rate Limiter
app.add_middleware(RateLimitMiddleware)

# 4. Include Routers
app.include_router(leadgen.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(campaigns.router)
app.include_router(leads.router)
app.include_router(inbox.router)
app.include_router(sending_accounts.router)
app.include_router(billing.router)
app.include_router(stripe.router)
app.include_router(intelligence.router)
app.include_router(tasks.router)
app.include_router(discovery.router)
app.include_router(meetings.router)
app.include_router(settings_router.router)
app.include_router(webhooks.router)

@app.get("/health")
def health_check(db = Depends(get_db)):
    health = {
        "status": "ok",
        "version": "2.0.0",
        "database": "down",
        "redis": "down"
    }
    
    # Check Database
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        health["database"] = "up"
    except Exception as e:
        health["status"] = "error"
        health["database"] = f"down: {str(e)}"
        
    # Check Redis
    try:
        from app.middleware.rate_limit import redis_client
        if redis_client.ping():
            health["redis"] = "up"
    except Exception as e:
        health["status"] = "error"
        health["redis"] = f"down: {str(e)}"
        
    return health
