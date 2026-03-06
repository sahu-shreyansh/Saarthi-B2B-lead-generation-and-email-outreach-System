import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.providers.scraping.serp_provider import SERPProvider
from app.providers.scraping.base_provider import NormalizedLead

logger = logging.getLogger(__name__)

class DiscoveryService:
    """
    Discovery engine orchestrating SERP API to uncover target organizations
    based on high intent search directives.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.provider = SERPProvider()
        
    def discover_companies(self, query: str, num_pages: int = 1) -> List[NormalizedLead]:
        """
        Executes Google search pagination and aggregates raw results into rough NormalizedLeads
        ready for deep intelligence crawling or direct insertion.
        """
        logger.info(f"[DiscoveryService] Starting discovery for query: {query}")
        leads = []
        try:
            response = self.provider.search(query=query, max_pages=num_pages)
            leads = response.results
            logger.info(f"[DiscoveryService] Extracted {len(leads)} raw target companies.")
        except Exception as e:
            logger.error(f"[DiscoveryService] Failure during SERP discovery: {str(e)}")
            
        return leads
