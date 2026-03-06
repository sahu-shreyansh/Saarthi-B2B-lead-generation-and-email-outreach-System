"""
base_provider.py — Abstract Base for all external LeadGen providers.

Defines the contract every provider must fulfill:
  - search()
  - scrape()
  - validate_response()
  - handle_error()
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


# ── Normalized Lead Schema ──────────────────────────────────────────
class NormalizedLead(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    confidence_score: float = 0.0


class ProviderResponse(BaseModel):
    source: str          # "apify" | "serp"
    results: List[NormalizedLead]
    total_found: int = 0
    has_more: bool = False
    next_page_token: Optional[str] = None


# ── Error Classification ────────────────────────────────────────────
class ProviderError(Exception):
    """Base error for all provider failures."""

class NetworkError(ProviderError):
    """Transient network failure — eligible for retry."""

class RateLimitError(ProviderError):
    """HTTP 429 — provider rate limit hit."""

class QuotaExhaustedError(ProviderError):
    """API plan quota exhausted — do not retry."""

class InvalidResponseError(ProviderError):
    """Response schema cannot be parsed — do not retry."""


# ── Circuit Breaker ─────────────────────────────────────────────────
class CircuitState(Enum):
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Provider disabled
    HALF_OPEN = "HALF_OPEN" # Testing recovery


# ── Abstract Base Provider ──────────────────────────────────────────
class BaseProvider(ABC):
    """
    All LeadGen providers must extend this class.
    Enforces a consistent interface across Apify, SERP, and any future provider.
    """

    name: str = "base"
    MAX_RETRIES: int = 3
    BACKOFF_BASE: int = 30  # seconds: 30, 60, 120

    @abstractmethod
    def search(self, query: str, **kwargs) -> ProviderResponse:
        """
        Execute a structured search (e.g., Google query via SERP).
        Returns a normalized list of results.
        """
        ...

    @abstractmethod
    def scrape(self, target: str, **kwargs) -> ProviderResponse:
        """
        Execute a structured scrape (e.g., LinkedIn profile via Apify actor).
        Returns a normalized list of results.
        """
        ...

    @abstractmethod
    def validate_response(self, raw: dict) -> bool:
        """
        Verify that the raw API response conforms to expected schema.
        Raises InvalidResponseError if schema is unexpected.
        """
        ...

    @abstractmethod
    def handle_error(self, exc: Exception, attempt: int) -> None:
        """
        Classify error and decide whether to retry, raise, or circuit-break.
        Raises the appropriate ProviderError subclass.
        """
        ...
