"""
Unit tests for the Saarthi AI Agent system.
Tests: context_builder, usage_guard, llm_router, signal_agent, classifier_agent, email_agent output schemas.
"""
import json
import pytest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_org():
    org = MagicMock()
    org.id = "11111111-1111-1111-1111-111111111111"
    org.name = "Acme Corp"
    org.openrouter_api_key = None  # platform key by default
    org.default_llm_model = "mistralai/mistral-7b-instruct"
    org.ai_usage_tokens = 100
    org.ai_usage_limit = 50000
    org.settings = {
        "company_profile": {
            "company_name": "Acme Corp",
            "business_description": "B2B SaaS for sales teams",
            "ideal_customer_profile": "Head of Sales at 50-500 person companies",
            "services_paragraph": "Lead enrichment, email personalization, CRM sync",
        }
    }
    return org


@pytest.fixture
def mock_lead():
    lead = MagicMock()
    lead.id = "22222222-2222-2222-2222-222222222222"
    lead.first_name = "Alice"
    lead.last_name = "Smith"
    lead.contact_name = None
    lead.title = "Head of Sales"
    lead.company = "TechCo"
    lead.company_name = "TechCo"
    lead.industry = "SaaS"
    lead.location = "San Francisco"
    lead.linkedin_url = ""
    lead.description = ""
    lead.metadata_ = {
        "headline": "Growing sales from $1M to $10M ARR",
        "about": "Spent 5 years in SDR roles before moving to leadership.",
        "company_size": "50",
    }
    return lead


@pytest.fixture
def sample_services():
    return [
        {"service_name": "Lead Enrichment", "service_description": "Fills missing contact data automatically"},
        {"service_name": "Email Personalization", "service_description": "AI-generated personalized cold emails"},
        {"service_name": "CRM Sync", "service_description": "Two-way sync with Salesforce and HubSpot"},
    ]


# ─────────────────────────────────────────────
# Context Builder Tests
# ─────────────────────────────────────────────

class TestContextBuilder:
    def test_build_lead_context_full_data(self, mock_lead):
        from app.ai.services.context_builder import build_lead_context
        ctx = build_lead_context(mock_lead)

        assert ctx["lead_name"] == "Alice Smith"
        assert ctx["first_name"] == "Alice"
        assert ctx["job_title"] == "Head of Sales"
        assert ctx["lead_company"] == "TechCo"
        assert ctx["headline"] == "Growing sales from $1M to $10M ARR"
        assert ctx["about"] == "Spent 5 years in SDR roles before moving to leadership."
        assert ctx["company_size"] == "50"

    def test_build_lead_context_missing_fields(self):
        from app.ai.services.context_builder import build_lead_context
        lead = MagicMock()
        lead.first_name = None
        lead.last_name = None
        lead.contact_name = None
        lead.title = None
        lead.company = None
        lead.company_name = None
        lead.industry = None
        lead.location = None
        lead.linkedin_url = None
        lead.description = None
        lead.metadata_ = {}

        ctx = build_lead_context(lead)
        assert ctx["lead_name"] == "UNKNOWN"
        assert ctx["job_title"] == "UNKNOWN"
        assert ctx["headline"] == "UNKNOWN"

    def test_build_company_context(self, mock_org):
        from app.ai.services.context_builder import build_company_context
        ctx = build_company_context(mock_org)

        assert ctx["company_name"] == "Acme Corp"
        assert "SaaS" in ctx["company_business"]

    def test_build_services_context_json(self, sample_services):
        from app.ai.services.context_builder import build_services_context
        ctx = build_services_context(sample_services)

        assert len(ctx["services_json"]) == 3
        assert "Lead Enrichment" in ctx["services_paragraph"]
        assert ctx["services_json"][0]["service_name"] == "Lead Enrichment"

    def test_build_services_context_empty(self):
        from app.ai.services.context_builder import build_services_context
        ctx = build_services_context([])
        assert ctx["services_paragraph"] == "UNKNOWN"
        assert ctx["services_json"] == []

    def test_personalization_depth_deep(self, mock_lead):
        from app.ai.services.context_builder import build_lead_context, get_personalization_depth
        ctx = build_lead_context(mock_lead)
        assert get_personalization_depth(ctx) == "Deep"

    def test_personalization_depth_medium(self):
        from app.ai.services.context_builder import get_personalization_depth
        ctx = {"headline": "UNKNOWN", "about": "UNKNOWN", "job_title": "Head of Sales"}
        assert get_personalization_depth(ctx) == "Medium"

    def test_personalization_depth_surface(self):
        from app.ai.services.context_builder import get_personalization_depth
        ctx = {"headline": "UNKNOWN", "about": "UNKNOWN", "job_title": "UNKNOWN"}
        assert get_personalization_depth(ctx) == "Surface"


# ─────────────────────────────────────────────
# Usage Guard Tests
# ─────────────────────────────────────────────

class TestUsageGuard:
    def test_quota_ok(self, mock_db, mock_org):
        from app.ai.guards.usage_guard import check_quota
        mock_db.query.return_value.filter.return_value.first.return_value = mock_org
        # Should not raise
        check_quota(str(mock_org.id), mock_db)

    def test_quota_exceeded_raises_402(self, mock_db, mock_org):
        from app.ai.guards.usage_guard import check_quota
        from fastapi import HTTPException
        mock_org.ai_usage_tokens = 60000
        mock_org.ai_usage_limit = 50000
        mock_org.openrouter_api_key = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_org

        with pytest.raises(HTTPException) as exc_info:
            check_quota(str(mock_org.id), mock_db)
        assert exc_info.value.status_code == 402

    def test_quota_bypassed_for_byo_key(self, mock_db, mock_org):
        from app.ai.guards.usage_guard import check_quota
        mock_org.ai_usage_tokens = 999999
        mock_org.openrouter_api_key = "sk-abc123"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_org
        # Should not raise — BYO key bypasses limit
        check_quota(str(mock_org.id), mock_db)

    def test_quota_unknown_org_passes(self, mock_db):
        from app.ai.guards.usage_guard import check_quota
        mock_db.query.return_value.filter.return_value.first.return_value = None
        # Should not raise for missing org
        check_quota("00000000-0000-0000-0000-000000000000", mock_db)


# ─────────────────────────────────────────────
# LLM Router Tests
# ─────────────────────────────────────────────

class TestLLMRouter:
    def test_get_llm_platform_key(self, mock_db, mock_org):
        from app.ai.routers.llm_router import get_llm_for_org
        mock_db.query.return_value.filter.return_value.first.return_value = mock_org

        config = get_llm_for_org(str(mock_org.id), mock_db)
        assert config["is_platform_key"] is True
        assert config["model"] == "mistralai/mistral-7b-instruct"

    def test_get_llm_byo_key(self, mock_db, mock_org):
        from app.ai.routers.llm_router import get_llm_for_org
        mock_org.openrouter_api_key = "encrypted_key"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_org

        with patch("app.core.security.decrypt_string", return_value="sk-custom-key"):
            config = get_llm_for_org(str(mock_org.id), mock_db)

        assert config["is_platform_key"] is False
        assert config["api_key"] == "sk-custom-key"


# ─────────────────────────────────────────────
# Agent Output Schema Tests
# ─────────────────────────────────────────────

class TestBaseAgentJsonParsing:
    def test_parse_clean_json(self):
        from app.ai.agents.base_agent import BaseAgent
        raw = '{"key": "value"}'
        result = BaseAgent._parse_json(raw)
        assert result == {"key": "value"}

    def test_parse_json_with_markdown_fence(self):
        from app.ai.agents.base_agent import BaseAgent
        raw = '```json\n{"key": "value"}\n```'
        result = BaseAgent._parse_json(raw)
        assert result == {"key": "value"}


class TestSignalAgentFallback:
    def test_fallback_response_schema(self, mock_db):
        from app.ai.agents.signal_agent import SignalAgent
        agent = SignalAgent(organization_id="00000000-0000-0000-0000-000000000000", db=mock_db)
        fallback = agent._fallback_response()

        assert "signal_report" in fallback
        sr = fallback["signal_report"]
        assert "inferred_priority" in sr
        assert "hidden_frustration" in sr
        assert "person_type" in sr
        assert "conversation_opener" in sr
        assert "avoid" in sr


class TestEmailAgentFallback:
    def test_fallback_has_email(self, mock_db):
        from app.ai.agents.email_agent import EmailAgent
        agent = EmailAgent(organization_id="00000000-0000-0000-0000-000000000000", db=mock_db)
        fallback = agent._fallback_response()

        assert "email" in fallback
        assert "subject" in fallback["email"]
        assert "body" in fallback["email"]
        assert len(fallback["email"]["body"]) > 10


class TestClassifierAgentFallback:
    def test_fallback_has_classification(self, mock_db):
        from app.ai.agents.classifier_agent import ClassifierAgent
        agent = ClassifierAgent(organization_id="00000000-0000-0000-0000-000000000000", db=mock_db)
        fallback = agent._fallback_response()

        assert "classification" in fallback
        assert "selected_service" in fallback["classification"]
        assert "email" in fallback


class TestReplyClassifierFallback:
    def test_fallback_is_unclear(self, mock_db):
        from app.ai.agents.reply_classifier import ReplyClassifier
        agent = ReplyClassifier(organization_id="00000000-0000-0000-0000-000000000000", db=mock_db)
        fallback = agent._fallback_response()

        assert fallback["intent"] == "unclear"
        assert "confidence" in fallback
        assert "recommended_action" in fallback
