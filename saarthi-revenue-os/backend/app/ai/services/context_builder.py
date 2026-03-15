"""
Context Builder — Converts raw DB models into clean, prompt-ready dicts.
Agents must NEVER receive raw SQLAlchemy objects.
"""
import logging
from typing import Optional, Any, Dict, List

logger = logging.getLogger(__name__)


def build_lead_context(lead: Any, organization: Any = None) -> Dict[str, str]:
    """
    Extracts and normalizes all available lead fields for agent prompts.
    Handles missing data gracefully — agents use 'UNKNOWN' as signal.
    """
    def _safe(val, fallback="UNKNOWN"):
        if val is None:
            return fallback
        v = str(val).strip()
        return v if v else fallback

    # Compose full name
    first = _safe(getattr(lead, "first_name", None), "")
    last = _safe(getattr(lead, "last_name", None), "")
    contact_name = getattr(lead, "contact_name", None)

    if first and last:
        full_name = f"{first} {last}"
    elif contact_name:
        full_name = _safe(contact_name)
    elif first:
        full_name = first
    else:
        full_name = "UNKNOWN"

    # Company name — try multiple fields
    company = (
        _safe(getattr(lead, "company_name", None), "")
        or _safe(getattr(lead, "company", None), "")
        or "UNKNOWN"
    )

    return {
        "lead_name": full_name,
        "first_name": first or full_name.split()[0] if full_name != "UNKNOWN" else "there",
        "job_title": _safe(getattr(lead, "title", None)),
        "lead_company": company,
        "company_size": _safe(lead.metadata_.get("company_size") if hasattr(lead, "metadata_") and lead.metadata_ else None),
        "headline": _safe(lead.metadata_.get("headline") if hasattr(lead, "metadata_") and lead.metadata_ else None),
        "about": _safe(lead.metadata_.get("about") if hasattr(lead, "metadata_") and lead.metadata_ else None),
        "industry": _safe(getattr(lead, "industry", None)),
        "location": _safe(getattr(lead, "location", None)),
        "linkedin_url": _safe(getattr(lead, "linkedin_url", None), ""),
        "description": _safe(getattr(lead, "description", None)),
    }


def build_company_context(organization: Any) -> Dict[str, str]:
    """
    Extracts organization-level context for agent prompts.
    Reads from org.settings['company_profile'] if populated.
    """
    def _safe(val, fallback="UNKNOWN"):
        if val is None:
            return fallback
        v = str(val).strip()
        return v if v else fallback

    profile = {}
    if hasattr(organization, "settings") and organization.settings:
        profile = organization.settings.get("company_profile", {})

    return {
        "company_name": _safe(profile.get("company_name") or getattr(organization, "name", None)),
        "company_business": _safe(profile.get("business_description")),
        "icp": _safe(profile.get("ideal_customer_profile")),
        "services_paragraph": _safe(profile.get("services_paragraph")),
    }


def build_services_context(services: List[Dict]) -> Dict[str, Any]:
    """
    Formats a list of services for use in agents.
    Returns both paragraph (for Normal Agent) and JSON array (for Classifier Agent).
    """
    if not services:
        return {
            "services_paragraph": "UNKNOWN",
            "services_json": [],
        }

    # Paragraph form
    para_parts = []
    for s in services:
        name = s.get("service_name", "")
        desc = s.get("service_description", "")
        if name:
            para_parts.append(f"{name}: {desc}" if desc else name)
    services_paragraph = ". ".join(para_parts) if para_parts else "UNKNOWN"

    # JSON array form
    services_json = [
        {
            "service_name": s.get("service_name", ""),
            "service_description": s.get("service_description", ""),
        }
        for s in services
        if s.get("service_name")
    ]

    return {
        "services_paragraph": services_paragraph,
        "services_json": services_json,
    }


def build_email_context(lead: Any, organization: Any, services: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """
    Master context builder combining lead + company + services.
    Single call for agents that need the full picture.
    """
    lead_ctx = build_lead_context(lead, organization)
    company_ctx = build_company_context(organization)
    services_ctx = build_services_context(services or [])

    return {**lead_ctx, **company_ctx, **services_ctx}


def get_personalization_depth(context: Dict[str, str]) -> str:
    """
    Returns Surface / Medium / Deep based on available lead data.
    Matches the personalization_depth mapping from agent.md Data Reliability Rules.
    """
    headline = context.get("headline", "UNKNOWN")
    about = context.get("about", "UNKNOWN")
    job_title = context.get("job_title", "UNKNOWN")

    if headline != "UNKNOWN" or about != "UNKNOWN":
        return "Deep"
    if job_title != "UNKNOWN":
        return "Medium"
    return "Surface"
