"""
serp_provider.py — Production-grade SERP API integration.

Uses SerpApi (serpapi.com) for Google search result extraction.

Features:
  - Pagination (multi-page extraction)
  - Rate limit detection (HTTP 429)
  - Exponential backoff (max 3 retries)
  - Circuit breaker (Redis-backed, 5 min open window)
  - Organic, Maps, and Related result parsing
  - Normalized NormalizedLead output
  
SERP is ONLY for Google search queries.
Do NOT use this for LinkedIn scraping.
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

SERP_ENDPOINT = "https://serpapi.com/search"
CIRCUIT_BREAKER_KEY = "circuit_breaker:serp"
CB_FAILURE_KEY = "cb_failures:serp"
CB_OPEN_TTL = 300   # 5 minutes
CB_MAX_FAILURES = 5

_redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


class SERPProvider(BaseProvider):
    """
    Calls SerpApi to extract structured Google search results.
    Supports organic results, Maps results, and pagination.
    """

    name = "serp"

    def __init__(self):
        if not settings.SERPAPI_KEY:
            raise RuntimeError(
                "SERPAPI_KEY is not configured. Cannot initialize SERPProvider."
            )
        self._key = settings.SERPAPI_KEY

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
                f"[serp] Circuit breaker OPENED after {CB_MAX_FAILURES} consecutive failures."
            )

    def _record_success(self):
        _redis.delete(CB_FAILURE_KEY)
        _redis.delete(CIRCUIT_BREAKER_KEY)

    # ── Error Handler ────────────────────────────────────────────────
    def handle_error(self, exc: Exception, attempt: int) -> None:
        if isinstance(exc, httpx.TimeoutException):
            logger.warning(f"[serp] Timeout on attempt {attempt}")
            raise NetworkError(f"SERP request timed out: {exc}") from exc

        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            if status_code == 429:
                raise RateLimitError("SERP rate limit hit (HTTP 429)") from exc
            if status_code == 402:
                raise QuotaExhaustedError("SERP quota exhausted (HTTP 402)") from exc
            if status_code >= 500:
                raise NetworkError(f"SERP server error {status_code}") from exc

        raise NetworkError(f"SERP unknown network error: {exc}") from exc

    # ── Response Validator ───────────────────────────────────────────
    def validate_response(self, raw: dict) -> bool:
        if not isinstance(raw, dict):
            raise InvalidResponseError("SERP response is not a JSON object")
        if raw.get("error"):
            err_msg = raw["error"]
            if "credits" in err_msg.lower() or "usage" in err_msg.lower():
                raise QuotaExhaustedError(f"SERP quota error: {err_msg}")
            raise InvalidResponseError(f"SERP API error: {err_msg}")
        return True

    # ── Search Entry Point (with Pagination) ─────────────────────────
    def search(
        self,
        query: str,
        max_pages: int = 1,
        result_type: str = "organic",  # "organic" | "maps"
        **kwargs
    ) -> ProviderResponse:
        """
        Execute a Google search via SerpApi.

        Args:
            query: The search query string.
            max_pages: Number of pages to paginate through (10 results/page).
            result_type: "organic" or "maps"
        """
        db = kwargs.get("db")
        org_id = kwargs.get("org_id")
        
        api_key = self._key
        if db and org_id:
            from app.database.models import Organization
            from app.core.security import decrypt_string
            org = db.query(Organization).filter(Organization.id == org_id).first()
            if org and org.serpapi_api_key:
                decrypted_key = decrypt_string(org.serpapi_api_key)
                if decrypted_key:
                    api_key = decrypted_key

        if self._is_circuit_open():
            logger.error("[serp] Circuit breaker is OPEN. Skipping provider call.")
            raise NetworkError("SERP circuit breaker is OPEN — provider temporarily disabled.")

        all_results: list[NormalizedLead] = []
        next_token = None

        for page_num in range(max_pages):
            params = {
                "q": query,
                "api_key": api_key,
                "engine": "google",
                "num": 10,
                "start": page_num * 10,
            }
            if result_type == "maps":
                params["tbm"] = "lcl"  # Local results

            if next_token:
                params["next_page_token"] = next_token

            result_page = self._fetch_page(params, page_num + 1)
            if not result_page:
                break

            if result_type == "organic":
                page_leads = self._parse_organic(result_page)
            else:
                page_leads = self._parse_maps(result_page)

            all_results.extend(page_leads)

            # Pagination token
            next_token = result_page.get("serpapi_pagination", {}).get("next_page_token")
            if not next_token:
                break

        return ProviderResponse(
            source="serp",
            results=all_results,
            total_found=len(all_results),
            has_more=bool(next_token),
            next_page_token=next_token
        )

    def _fetch_page(self, params: dict, page_num: int) -> dict | None:
        """Fetch a single results page with retry/backoff."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                t0 = time.monotonic()
                with httpx.Client(timeout=30.0) as client:
                    resp = client.get(SERP_ENDPOINT, params=params)
                    resp.raise_for_status()
                    raw = resp.json()

                duration = time.monotonic() - t0
                logger.info(
                    f"[serp] page={page_num} status=200 duration={duration:.2f}s "
                    f"results={len(raw.get('organic_results', []))}"
                )
                self.validate_response(raw)
                self._record_success()
                return raw

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
                        logger.warning(f"[serp] Retrying page {page_num} in {backoff}s (attempt {attempt}/{self.MAX_RETRIES})")
                        time.sleep(backoff)
                    else:
                        raise

        return None

    def scrape(self, target: str, **kwargs) -> ProviderResponse:
        """
        SERP is NOT the correct provider for scraping specific URLs.
        Route those to ApifyProvider instead.
        """
        raise NotImplementedError(
            "SERPProvider.scrape() is not supported. "
            "Use ApifyProvider for LinkedIn/Maps/Website scraping."
        )

    # ── Parsers ──────────────────────────────────────────────────────
    def _parse_organic(self, raw: dict) -> list[NormalizedLead]:
        leads = []
        for item in raw.get("organic_results", []):
            domain = None
            link = item.get("link", "")
            if link:
                domain = link.replace("https://", "").replace("http://", "").split("/")[0]

            lead = NormalizedLead(
                name=item.get("title"),
                website=link,
                domain=domain,
                confidence_score=0.5
            )
            leads.append(lead)
        return leads

    def _parse_maps(self, raw: dict) -> list[NormalizedLead]:
        leads = []
        for item in raw.get("local_results", []):
            website = item.get("website")
            domain = None
            if website:
                domain = website.replace("https://", "").replace("http://", "").split("/")[0]

            lead = NormalizedLead(
                name=item.get("title"),
                company=item.get("title"),
                website=website,
                domain=domain,
                location=item.get("address"),
                confidence_score=0.65 if website else 0.3
            )
            leads.append(lead)
        return leads
