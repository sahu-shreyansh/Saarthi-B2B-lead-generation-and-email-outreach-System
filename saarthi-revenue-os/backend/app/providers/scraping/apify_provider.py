"""
apify_provider.py — Production-grade Apify integration.

Supports:
  - LinkedIn scraping
  - Google Maps scraping
  - Website crawling

Features:
  - Async actor run + dataset polling
  - Timeout protection (httpx)
  - Exponential backoff (max 3 retries)
  - Circuit breaker (Redis-backed, 5 min open window)
  - Structured error classification
  - Quota exhaustion detection
"""
import logging
import time
import httpx
import redis

from app.core.settings import settings
from app.providers.scraping.base_provider import (
    BaseProvider, ProviderResponse, NormalizedLead,
    NetworkError, RateLimitError, QuotaExhaustedError, InvalidResponseError
)

logger = logging.getLogger(__name__)

# ── Apify Actor IDs ─────────────────────────────────────────────────
ACTOR_IDS = {
    "linkedin": "2SyF0bVxmgGr8IVCZ",       # LinkedIn Profile/Company Scraper
    "maps": "nwua9Gu5YrADL7ZDj",             # Google Maps Scraper
    "website": "apify~website-content-crawler"  # General Website Crawler
}

APIFY_BASE = "https://api.apify.com/v2"
CIRCUIT_BREAKER_KEY = "circuit_breaker:apify"
CB_FAILURE_KEY = "cb_failures:apify"
CB_OPEN_TTL = 300   # 5 minutes open window
CB_MAX_FAILURES = 5 # Failure threshold

_redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


class ApifyProvider(BaseProvider):
    """
    Calls Apify actors to scrape LinkedIn, Google Maps, and websites.
    Uses synchronous run-sync endpoint for small jobs, falls back to polling for large ones.
    """

    name = "apify"

    def __init__(self):
        if not settings.APIFY_TOKEN:
            raise RuntimeError(
                "APIFY_TOKEN is not configured. Cannot initialize ApifyProvider."
            )
        self._token = settings.APIFY_TOKEN
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

    # ── Circuit Breaker ──────────────────────────────────────────────
    def _is_circuit_open(self) -> bool:
        return _redis.exists(CIRCUIT_BREAKER_KEY) > 0

    def _record_failure(self):
        pipe = _redis.pipeline()
        pipe.incr(CB_FAILURE_KEY)
        pipe.expire(CB_FAILURE_KEY, CB_OPEN_TTL)
        failures, _ = pipe.execute()
        if int(failures) >= CB_MAX_FAILURES:
            _redis.setex(CIRCUIT_BREAKER_KEY, CB_OPEN_TTL, "open")
            logger.error(
                f"[apify] Circuit breaker OPENED after {CB_MAX_FAILURES} consecutive failures."
            )

    def _record_success(self):
        _redis.delete(CB_FAILURE_KEY)
        _redis.delete(CIRCUIT_BREAKER_KEY)

    # ── Error Handler ────────────────────────────────────────────────
    def handle_error(self, exc: Exception, attempt: int) -> None:
        if isinstance(exc, httpx.TimeoutException):
            logger.warning(f"[apify] Timeout on attempt {attempt}")
            raise NetworkError(f"Apify request timed out: {exc}") from exc

        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            if status_code == 429:
                raise RateLimitError("Apify rate limit hit (HTTP 429)") from exc
            if status_code == 402:
                raise QuotaExhaustedError("Apify quota exhausted (HTTP 402)") from exc
            if status_code >= 500:
                raise NetworkError(f"Apify server error {status_code}") from exc

        raise NetworkError(f"Apify unknown error: {exc}") from exc

    # ── Response Validator ───────────────────────────────────────────
    def validate_response(self, raw: dict) -> bool:
        if not isinstance(raw, (list, dict)):
            raise InvalidResponseError("Apify response is not a list or dict")
        return True

    # ── Scrape Entry Point ───────────────────────────────────────────
    def scrape(self, target: str, actor_type: str = "maps", max_results: int = 50, **kwargs) -> ProviderResponse:
        """
        Invokes an Apify actor and retrieves all dataset results.
        
        Args:
            target: The search query or URL to scrape.
            actor_type: One of "linkedin", "maps", "website"
            max_results: Max number of results to fetch.
        """
        db = kwargs.get("db")
        org_id = kwargs.get("org_id")
        
        headers = self._headers
        if db and org_id:
            from app.database.models import Organization
            from app.core.security import decrypt_string
            org = db.query(Organization).filter(Organization.id == org_id).first()
            if org and org.apify_api_key:
                decrypted_key = decrypt_string(org.apify_api_key)
                if decrypted_key:
                    headers = {
                        "Authorization": f"Bearer {decrypted_key}",
                        "Content-Type": "application/json"
                    }

        if self._is_circuit_open():
            logger.error("[apify] Circuit breaker is OPEN. Skipping provider call.")
            raise NetworkError("Apify circuit breaker is OPEN — provider temporarily disabled.")

        actor_id = ACTOR_IDS.get(actor_type)
        if not actor_id:
            raise InvalidResponseError(f"Unknown actor_type: {actor_type}. Valid: {list(ACTOR_IDS.keys())}")

        input_payload = self._build_payload(actor_type, target, max_results, **kwargs)

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"[apify] Attempt {attempt} — actor={actor_id} target={target!r}")
                t0 = time.monotonic()

                with httpx.Client(timeout=300.0) as client:
                    # Start actor run synchronously (Apify will block until complete, up to 60s)
                    run_resp = client.post(
                        f"{APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items",
                        headers=headers,
                        json=input_payload,
                        params={"clean": "true", "format": "json", "limit": max_results}
                    )
                    run_resp.raise_for_status()
                    raw_items = run_resp.json()

                duration = time.monotonic() - t0
                logger.info(
                    f"[apify] actor={actor_id} status=200 duration={duration:.2f}s "
                    f"results={len(raw_items) if isinstance(raw_items, list) else 0}"
                )

                self.validate_response(raw_items)
                self._record_success()

                normalized = self._normalize(raw_items, actor_type)
                return ProviderResponse(
                    source="apify",
                    results=normalized,
                    total_found=len(normalized)
                )

            except (RateLimitError, QuotaExhaustedError, InvalidResponseError):
                self._record_failure()
                raise

            except Exception as exc:
                self._record_failure()
                try:
                    self.handle_error(exc, attempt)
                except NetworkError:
                    if attempt < self.MAX_RETRIES:
                        backoff = self.BACKOFF_BASE * (2 ** (attempt - 1))
                        logger.warning(f"[apify] Retrying in {backoff}s (attempt {attempt}/{self.MAX_RETRIES})")
                        time.sleep(backoff)
                    else:
                        raise

        raise NetworkError("Apify: all retries exhausted.")

    def search(self, query: str, **kwargs) -> ProviderResponse:
        """
        Apify is NOT the correct provider for raw Google Search queries.
        Route those to SERPProvider instead.
        """
        raise NotImplementedError(
            "ApifyProvider.search() is not supported. "
            "Use SERPProvider for Google search results."
        )

    # ── Input Payload Builder ────────────────────────────────────────
    def _build_payload(self, actor_type: str, target: str, max_results: int, **kwargs) -> dict:
        if actor_type == "maps":
            return {
                "searchStringsArray": [target],
                "maxCrawledPlaces": max_results,
                "language": kwargs.get("language", "en"),
                "countryCode": kwargs.get("country_code", "us"),
                "includeReviews": False,
                "includeImages": False,
                "includeHistogram": False
            }
        elif actor_type == "linkedin":
            return {
                "searchUrl": target,
                "count": max_results
            }
        elif actor_type == "website":
            return {
                "startUrls": [{"url": target}],
                "maxCrawlPages": min(max_results, 10),
                "sameDomain": True
            }
        return {"query": target}

    # ── Normalizer ───────────────────────────────────────────────────
    def _normalize(self, raw_items: list, actor_type: str) -> list[NormalizedLead]:
        leads = []
        for item in (raw_items if isinstance(raw_items, list) else []):
            if actor_type == "maps":
                lead = NormalizedLead(
                    name=item.get("title"),
                    company=item.get("title"),
                    email=self._extract_email(item),
                    domain=item.get("website", "").replace("https://", "").replace("http://", "").split("/")[0] if item.get("website") else None,
                    website=item.get("website"),
                    location=item.get("address"),
                    confidence_score=0.7 if item.get("website") else 0.3
                )
            elif actor_type == "linkedin":
                lead = NormalizedLead(
                    name=item.get("fullName") or item.get("name"),
                    company=item.get("companyName") or (item.get("positions") or [{}])[0].get("companyName"),
                    email=item.get("email"),
                    linkedin_url=item.get("url") or item.get("profileUrl"),
                    location=item.get("geoLocationName"),
                    confidence_score=0.85 if item.get("email") else 0.5
                )
            elif actor_type == "website":
                lead = NormalizedLead(
                    name=item.get("metadata", {}).get("title"),
                    website=item.get("url"),
                    email=self._extract_email(item),
                    confidence_score=0.4
                )
            else:
                continue

            # Set domain from email if not already set
            if lead.email and "@" in lead.email and not lead.domain:
                lead.domain = lead.email.split("@")[1].lower()

            leads.append(lead)
        return leads

    def _extract_email(self, item: dict) -> str | None:
        """Scan common fields for email addresses."""
        for field in ["email", "businessEmail", "contact_email"]:
            if item.get(field):
                return item[field].lower()
        # Scan arrays like additionalInfo
        for val in str(item).split():
            if "@" in val and "." in val:
                clean = val.strip('",;:\'{}[]')
                if "@" in clean:
                    return clean.lower()
        return None
