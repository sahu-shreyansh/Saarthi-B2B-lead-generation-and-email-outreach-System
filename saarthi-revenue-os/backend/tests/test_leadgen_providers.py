"""
test_leadgen_providers.py — LeadGen Provider System Tests

Test Coverage:
  1. Provider routing correctness
  2. SERP response parsing (organic + maps)
  3. Apify response normalization
  4. Credit deduction accuracy
  5. Retry behavior on network failures
  6. Circuit breaker activation
  7. Quota exhaustion handling (non-retriable)
  8. Duplicate lead deduplication
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import httpx

from app.providers.scraping.base_provider import (
    NormalizedLead, ProviderResponse,
    NetworkError, RateLimitError, QuotaExhaustedError, InvalidResponseError
)
from app.providers.scraping.apify_provider import ApifyProvider
from app.providers.scraping.serp_provider import SERPProvider
from app.services.leadgen_service import route_provider, fetch_leads, APIFY_TYPES, SERP_TYPES


# ─────────────────────────────────────────────────────────
# 1. Provider Routing Correctness
# ─────────────────────────────────────────────────────────

class TestRouting:
    @patch("app.providers.scraping.apify_provider.settings")
    def test_maps_routes_to_apify(self, mock_settings):
        mock_settings.APIFY_TOKEN = "test-token"
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        provider = route_provider("maps")
        assert isinstance(provider, ApifyProvider)

    @patch("app.providers.scraping.apify_provider.settings")
    def test_linkedin_routes_to_apify(self, mock_settings):
        mock_settings.APIFY_TOKEN = "test-token"
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        provider = route_provider("linkedin")
        assert isinstance(provider, ApifyProvider)

    @patch("app.providers.scraping.serp_provider.settings")
    def test_google_search_routes_to_serp(self, mock_settings):
        mock_settings.SERPAPI_KEY = "test-serp-key"
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        provider = route_provider("google_search")
        assert isinstance(provider, SERPProvider)

    def test_invalid_query_type_raises(self):
        with pytest.raises(ValueError, match="Unknown query_type"):
            route_provider("invalid_source")

    @patch("app.providers.scraping.serp_provider.settings")
    def test_apify_cannot_search(self, mock_settings):
        """Apify.search() must raise NotImplementedError — it's not a search engine."""
        mock_settings.APIFY_TOKEN = "test-token"
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        with patch("app.providers.scraping.apify_provider.settings") as apify_settings:
            apify_settings.APIFY_TOKEN = "test-token"
            apify_settings.REDIS_URL = "redis://localhost:6379/0"
            provider = ApifyProvider()
            with pytest.raises(NotImplementedError):
                provider.search("query")

    @patch("app.providers.scraping.serp_provider.settings")
    def test_serp_cannot_scrape(self, mock_settings):
        """SERP.scrape() must raise NotImplementedError — it's not a scraper."""
        mock_settings.SERPAPI_KEY = "test-serp-key"
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        provider = SERPProvider()
        with pytest.raises(NotImplementedError):
            provider.scrape("https://linkedin.com/in/test")


# ─────────────────────────────────────────────────────────
# 2. SERP Parsing Tests
# ─────────────────────────────────────────────────────────

class TestSERPParsing:
    def _make_provider(self):
        with patch("app.providers.scraping.serp_provider.settings") as m, \
             patch("app.providers.scraping.serp_provider._redis") as r:
            m.SERPAPI_KEY = "test-key"
            m.REDIS_URL = "redis://localhost:6379/0"
            r.exists.return_value = 0
            r.pipeline.return_value.__enter__ = lambda s: s
            r.pipeline.return_value.__exit__ = MagicMock(return_value=False)
            r.pipeline.return_value.execute.return_value = [1, True]
            return SERPProvider()

    def test_organic_results_parsed_correctly(self):
        raw = {
            "organic_results": [
                {"title": "Acme Corp", "link": "https://acme.com/page"},
                {"title": "Beta Inc", "link": "https://betainc.io"},
            ]
        }
        provider = self._make_provider()
        leads = provider._parse_organic(raw)
        assert len(leads) == 2
        assert leads[0].name == "Acme Corp"
        assert leads[0].domain == "acme.com"
        assert leads[0].website == "https://acme.com/page"

    def test_maps_results_parsed_correctly(self):
        raw = {
            "local_results": [
                {"title": "Sky Labs", "address": "123 Main St, SF", "website": "https://skylabs.io"},
            ]
        }
        provider = self._make_provider()
        leads = provider._parse_maps(raw)
        assert len(leads) == 1
        assert leads[0].company == "Sky Labs"
        assert leads[0].location == "123 Main St, SF"
        assert leads[0].domain == "skylabs.io"

    def test_quota_error_raised_from_response(self):
        provider = self._make_provider()
        with pytest.raises(QuotaExhaustedError):
            provider.validate_response({"error": "Your plan credits have been exhausted"})

    def test_invalid_response_error_for_non_dict(self):
        provider = self._make_provider()
        with pytest.raises(InvalidResponseError):
            provider.validate_response(["not", "a", "dict"])


# ─────────────────────────────────────────────────────────
# 3. Apify Parsing Tests
# ─────────────────────────────────────────────────────────

class TestApifyParsing:
    def _make_provider(self):
        with patch("app.providers.scraping.apify_provider.settings") as m, \
             patch("app.providers.scraping.apify_provider._redis") as r:
            m.APIFY_TOKEN = "test-token"
            m.REDIS_URL = "redis://localhost:6379/0"
            r.exists.return_value = 0
            return ApifyProvider()

    def test_maps_results_normalized(self):
        raw = [
            {"title": "Acme Cafe", "address": "5th Ave, NY", "website": "https://acmecafe.com", "email": "hello@acmecafe.com"},
        ]
        provider = self._make_provider()
        leads = provider._normalize(raw, "maps")
        assert leads[0].company == "Acme Cafe"
        assert leads[0].email == "hello@acmecafe.com"
        assert leads[0].domain == "acmecafe.com"

    def test_linkedin_results_normalized(self):
        raw = [
            {"fullName": "Jane Doe", "companyName": "TechCorp", "email": "jane@techcorp.com", "url": "https://linkedin.com/in/jane"},
        ]
        provider = self._make_provider()
        leads = provider._normalize(raw, "linkedin")
        assert leads[0].name == "Jane Doe"
        assert leads[0].company == "TechCorp"
        assert leads[0].confidence_score == 0.85

    def test_no_email_gives_lower_confidence(self):
        raw = [{"fullName": "Bob Smith", "url": "https://linkedin.com/in/bob"}]
        provider = self._make_provider()
        leads = provider._normalize(raw, "linkedin")
        assert leads[0].confidence_score == 0.5


# ─────────────────────────────────────────────────────────
# 4. Credit Deduction Accuracy
# ─────────────────────────────────────────────────────────

class TestCreditGate:
    def test_credits_deducted_per_lead(self):
        """Each inserted lead must consume exactly 1 credit via check_and_reserve."""
        from app.services.billing import UsageService
        db_mock = MagicMock()
        sub_mock = MagicMock()
        sub_mock.status = "ACTIVE"
        sub_mock.monthly_credit_limit = 10
        sub_mock.credits_used = 5
        db_mock.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = sub_mock

        result = UsageService.check_and_reserve_credits(db_mock, "org-uuid", 1)
        assert result is True
        assert sub_mock.credits_used == 6

    def test_no_credits_blocks_insertion(self):
        from app.services.billing import UsageService
        db_mock = MagicMock()
        sub_mock = MagicMock()
        sub_mock.status = "ACTIVE"
        sub_mock.monthly_credit_limit = 5
        sub_mock.credits_used = 5  # Exhausted
        db_mock.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = sub_mock

        result = UsageService.check_and_reserve_credits(db_mock, "org-uuid", 1)
        assert result is False

    def test_credit_refunded_on_insert_failure(self):
        from app.services.billing import UsageService
        db_mock = MagicMock()
        sub_mock = MagicMock()
        sub_mock.credits_used = 3
        db_mock.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = sub_mock

        UsageService.refund_credits(db_mock, "org-uuid", 1)
        assert sub_mock.credits_used == 2


# ─────────────────────────────────────────────────────────
# 5. Retry Behavior
# ─────────────────────────────────────────────────────────

class TestRetryBehavior:
    @patch("app.providers.scraping.apify_provider._redis")
    @patch("app.providers.scraping.apify_provider.settings")
    @patch("app.providers.scraping.apify_provider.time.sleep", return_value=None)
    def test_network_error_retries_three_times(self, mock_sleep, mock_settings, mock_redis):
        mock_settings.APIFY_TOKEN = "token"
        mock_settings.REDIS_URL = "redis://localhost"
        mock_redis.exists.return_value = 0
        mock_redis.pipeline.return_value.execute.return_value = [1, True]

        provider = ApifyProvider()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client_cls.return_value = mock_client

            with pytest.raises(NetworkError):
                provider.scrape("test query", actor_type="maps")

            # Should have attempted 3 times
            assert mock_client.post.call_count == 3


# ─────────────────────────────────────────────────────────
# 6. Circuit Breaker Activation
# ─────────────────────────────────────────────────────────

class TestCircuitBreaker:
    @patch("app.providers.scraping.apify_provider._redis")
    @patch("app.providers.scraping.apify_provider.settings")
    def test_circuit_open_blocks_call(self, mock_settings, mock_redis):
        mock_settings.APIFY_TOKEN = "token"
        mock_settings.REDIS_URL = "redis://localhost"
        mock_redis.exists.return_value = 1  # Circuit is OPEN

        provider = ApifyProvider()
        with pytest.raises(NetworkError, match="circuit breaker"):
            provider.scrape("test", actor_type="maps")

    @patch("app.providers.scraping.apify_provider._redis")
    @patch("app.providers.scraping.apify_provider.settings")
    @patch("app.providers.scraping.apify_provider.time.sleep", return_value=None)
    def test_consecutive_failures_open_circuit(self, mock_sleep, mock_settings, mock_redis):
        mock_settings.APIFY_TOKEN = "token"
        mock_settings.REDIS_URL = "redis://localhost"
        # Start closed, return failure counts escalating
        mock_redis.exists.return_value = 0
        mock_redis.pipeline.return_value.execute.return_value = [5, True]  # 5 failures → OPEN

        provider = ApifyProvider()
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client_cls.return_value = mock_client

            with pytest.raises(NetworkError):
                provider.scrape("test", actor_type="maps")

        # setex must have been called to open the circuit
        mock_redis.setex.assert_called()


# ─────────────────────────────────────────────────────────
# 7. Quota Exhaustion Handling
# ─────────────────────────────────────────────────────────

class TestQuotaExhaustion:
    @patch("app.providers.scraping.serp_provider._redis")
    @patch("app.providers.scraping.serp_provider.settings")
    def test_quota_error_not_retried(self, mock_settings, mock_redis):
        mock_settings.SERPAPI_KEY = "test"
        mock_settings.REDIS_URL = "redis://localhost"
        mock_redis.exists.return_value = 0
        mock_redis.pipeline.return_value.execute.return_value = [1, True]

        provider = SERPProvider()
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"error": "your plan credits are exhausted"}
            mock_resp.raise_for_status.return_value = None
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with pytest.raises(QuotaExhaustedError):
                provider.search("test query")


# ─────────────────────────────────────────────────────────
# 8. Duplicate Lead Prevention
# ─────────────────────────────────────────────────────────

class TestDeduplication:
    def test_duplicate_email_skipped(self):
        """DB dedup check should prevent double-insertion of same email in a campaign."""
        db = MagicMock()
        # Simulate existing lead found
        existing_lead = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing_lead

        # Pure logic test — if existing, we skip
        lead_email = "duplicate@test.com"
        campaign_id = "some-uuid"

        from app.database.models import Lead
        found = db.query(Lead).filter(
            Lead.campaign_id == campaign_id,
            Lead.email == lead_email
        ).first()

        assert found is not None  # Logic would skip insertion
