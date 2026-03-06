import logging
import json
import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.providers.scraping.apify_provider import ApifyProvider
from app.providers.llm.openrouter_provider import OpenRouterProvider
from app.providers.llm.prompt_templates import SYSTEM_PROMPT, WEBSITE_LEAD_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

class WebsiteCrawlerService:
    """
    Crawls enterprise domains to extract latent team/contact records
    translating unstructured web-text into Lead objects using OpenRouter AI.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.scraper = ApifyProvider()
        self.ai = OpenRouterProvider(db=db)

    def extract_contacts_from_domain(self, url: str, org_id: str, campaign_id: str) -> List[Dict[str, Any]]:
        logger.info(f"[WebsiteCrawler] Commencing deep crawl on: {url}")
        
        # 1. Scrape domain (Using apify website crawler wrapper)
        try:
            # Increase max_results to 10 for better coverage
            raw_response = self.scraper.scrape(target=url, actor_type="website", max_results=10)
            
            # Combine text payloads from the crawled pages
            aggregated_web_text = "\n\n".join([
                lead.meta.get("text_content", "") 
                for lead in raw_response.results 
                if lead.meta
            ])
            
            if not aggregated_web_text:
                logger.warning(f"[WebsiteCrawler] No extractable text found for {url}")
                return []
                
        except Exception as e:
            logger.error(f"[WebsiteCrawler] Failed to scrape {url}: {e}")
            return []

        # 2. Extract via AI
        prompt = WEBSITE_LEAD_EXTRACTION_PROMPT.format(website_content=aggregated_web_text[:20000]) # Cap higher
        raw_json_str = self.ai.generate(
            prompt_type="WEBSITE_LEAD_EXTRACTION",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            org_id=org_id,
            campaign_id=campaign_id,
            use_fast_model=True # Extraction can use GPT-4o-mini
        )

        # 3. Parse and Return
        extracted_leads = []
        try:
            # Clean possible markdown block
            if raw_json_str.startswith("```json"):
                raw_json_str = raw_json_str.replace("```json", "").replace("```", "").strip()
            
            extracted_leads = json.loads(raw_json_str)
            if not isinstance(extracted_leads, list):
                extracted_leads = []
        except json.JSONDecodeError:
            logger.error(f"[WebsiteCrawler] AI yielded malformed JSON during extraction for {url}")

        # 4. Regex Fallback (Important for high recall)
        # If AI failed or returned nothing, search for emails directly
        if not extracted_leads:
            emails = list(set(re.findall(EMAIL_REGEX, aggregated_web_text)))
            if emails:
                logger.info(f"[WebsiteCrawler] Regex found {len(emails)} emails as fallback for {url}")
                for email in emails:
                    extracted_leads.append({
                        "contact_name": "Discovery Lead",
                        "contact_email": email,
                        "company_name": url.split("//")[-1].split("/")[0], # Rough domain extract
                        "reasoning": "Extracted via regex fallback"
                    })

        return extracted_leads
