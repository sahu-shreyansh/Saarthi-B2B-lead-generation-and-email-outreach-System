import time
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from redis import Redis

from app.core.settings import settings

# Initialize Redis client for rate limiting
# Initialize Redis client for rate limiting lazily or handle errors
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

# Define rate limits (Requests per minute)
RATE_LIMITS = {
    "/auth/login": 5,          # Brute-force protection
    "/discovery/run": 10,      # Prevent expensive scraping floods
    "/intelligence/score": 20  # Prevent expensive AI scoring floods
}

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Check if route is protected
        limit = None
        for protected_route, route_limit in RATE_LIMITS.items():
            if path.startswith(protected_route):
                limit = route_limit
                break
                
        if not limit:
            return await call_next(request)

        # Identify requester by IP or Authorization header
        identifier = request.headers.get("Authorization", request.client.host)
        redis_key = f"rate_limit:{path}:{identifier}"
        
        current_time = int(time.time())
        window_start = current_time - 60
        
        try:
            # Token bucket: Clean old requests, add new, check limit
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zcard(redis_key)
            pipe.zadd(redis_key, {str(current_time): current_time})
            pipe.expire(redis_key, 60)
            
            results = pipe.execute()
            request_count = results[1] # Output of zcard
            
            if request_count >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"error": True, "code": "RATE_LIMIT_EXCEEDED", "message": f"Rate limit exceeded. Try again in 60 seconds."}
                )
        except Exception:
            # Fallback open if Redis is unreachable
            pass

        response = await call_next(request)
        return response
