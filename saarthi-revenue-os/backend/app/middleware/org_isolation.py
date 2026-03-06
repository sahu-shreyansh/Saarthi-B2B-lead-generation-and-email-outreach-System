import uuid
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.security import decode_access_token

class OrgIsolationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        
        # Paths that don't need org isolation (Public, auth endpoints, stripe webhooks)
        exempt_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/auth/google",
            "/auth/microsoft",
            "/auth/join",
            "/webhooks/stripe",
            "/inbox/webhook",
            "/webhooks/email/event"
        ]

        # Ignore exemptions and OPTIONS calls
        if request.url.path in exempt_paths or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # We let the route's get_current_user dependency raise the 401. 
            # But the middleware won't have the org_id context.
            return await call_next(request)
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)

        if not payload or not payload.get("active_org_id"):
            # Token is invalid or missing org_id, let route handle or block here
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token or missing organization context."}
            )

        # Inject org_id into request state for repositories to access securely
        try:
            request.state.org_id = uuid.UUID(payload.get("active_org_id"))
        except ValueError:
             return JSONResponse(
                status_code=401,
                content={"detail": "Invalid organization ID format."}
            )
        
        return await call_next(request)
