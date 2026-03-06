"""
leadgen_service.py — Provider routing and lead processing service.

Responsible for:
  - Routing query_type to the correct provider (Apify or SERP)
  - Deduplicating raw results against the campaign
  - Emitting normalized NormalizedLead objects
"""
import logging
from typing import List

from app.providers.scraping.base_provider import ProviderResponse, NormalizedLead, ProviderError
from app.providers.scraping.apify_provider import ApifyProvider
from app.providers.scraping.serp_provider import SERPProvider

logger = logging.getLogger(__name__)

# Valid query types and their provider routing
APIFY_TYPES = {"linkedin", "maps", "website"}
SERP_TYPES = {"google_search"}


def route_provider(query_type: str):
    """
    Returns the correct provider instance for a given query_type.

    Routing rules:
      linkedin | maps | website → ApifyProvider
      google_search             → SERPProvider

    Raises:
      ValueError for unknown query types.
    """
    qt = query_type.lower()

    if qt in APIFY_TYPES:
        logger.info(f"[leadgen_service] Routing '{query_type}' → ApifyProvider")
        return ApifyProvider()
    
    if qt in SERP_TYPES:
        logger.info(f"[leadgen_service] Routing '{query_type}' → SERPProvider")
        return SERPProvider()

    raise ValueError(
        f"Unknown query_type '{query_type}'. "
        f"Valid types: {sorted(APIFY_TYPES | SERP_TYPES)}"
    )


def fetch_leads(
    query_type: str,
    query: str,
    max_results: int = 50,
    max_pages: int = 1,
    **kwargs
) -> ProviderResponse:
    """
    Fetches leads from the appropriate provider.

    Args:
        query_type: One of "linkedin", "maps", "website", "google_search"
        query:      The search query or scrape target
        max_results: Max number of leads to retrieve (per page for SERP)
        max_pages:  Number of pages for SERP pagination
    
    Returns:
        ProviderResponse with normalized NormalizedLead list.
    
    Raises:
        ProviderError subclasses on external API failures.
    """
    provider = route_provider(query_type)

    if query_type in APIFY_TYPES:
        return provider.scrape(target=query, actor_type=query_type, max_results=max_results, **kwargs)
    else:
        return provider.search(query=query, max_pages=max_pages, **kwargs)
