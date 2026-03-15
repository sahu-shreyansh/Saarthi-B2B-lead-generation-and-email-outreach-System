import uuid
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.database.database import SessionLocal
from app.database.models import Organization

class AIUsageGuardMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce AI token limits for organizations using the platform's default LLM keys.
    If an organization has connected their own OpenRouter key, the limit is bypassed.
    """
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        
        # Paths that trigger substantial AI usage
        ai_paths = ["/intelligence", "/leadgen", "/campaigns/personalize"]
        
        is_ai_path = any(request.url.path.startswith(p) for p in ai_paths)
        
        if not is_ai_path:
            return await call_next(request)

        # Skip check for OPTIONS
        if request.method == "OPTIONS":
            return await call_next(request)

        # org_id is injected by OrgIsolationMiddleware
        org_id = getattr(request.state, "org_id", None)
        if not org_id:
            # If no org_id in state, it might not be an isolated route or auth failed.
            # We let the route/auth dependency handle it.
            return await call_next(request)

        # Database session
        db = SessionLocal()
        try:
            org = db.query(Organization).filter(Organization.id == org_id).first()
            if not org:
                return await call_next(request)

            # BYO Key Check: If they have their own OpenRouter key, we don't block them.
            # (Tokens are billed to their own account)
            if org.openrouter_api_key:
                return await call_next(request)

            # Platform Free Tier Check
            if org.ai_usage_tokens >= org.ai_usage_limit:
                return JSONResponse(
                    status_code=402,
                    content={
                        "detail": "Free AI quota exceeded. Connect your OpenRouter API key in Settings to continue.",
                        "code": "AI_QUOTA_EXCEEDED"
                    }
                )
        finally:
            db.close()

        return await call_next(request)
