import httpx
import re
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from app.core.config import settings

def extract_emails(text: str) -> List[str]:
    if not text: return []
    raw = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return list(set([e.lower() for e in raw]))

def extract_phones(text: str) -> List[str]:
    if not text: return []
    # Simplified phone extraction matching n8n logic
    raw = re.findall(r'\+?\d[\d()\-\s]{6,}', text)
    phones = []
    for r in raw:
        cleaned = re.sub(r'[^\d+]', '', r)
        if re.match(r'^\+?\d{7,15}$', cleaned) or re.match(r'^\d{10,15}$', cleaned):
            if not cleaned.startswith('+') and len(cleaned) >= 10:
                cleaned = '+' + cleaned
            phones.append(cleaned)
    return list(set(phones))

async def search_prospects(job_title: str, industry: str, location: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Step 1: Find LinkedIn profiles matching the criteria."""
    if not settings.SERPAPI_KEY:
        print("WARNING: SERPAPI_KEY not set. Returning mock data.")
        return []
    
    query = f"site:linkedin.com/in {industry} {job_title}"
    params = {
        "engine": "google",
        "q": query,
        "location": location,
        "hl": "en",
        "num": max_results,
        "safe": "active",
        "api_key": settings.SERPAPI_KEY
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get("https://serpapi.com/search.json", params=params, timeout=15.0)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"SerpAPI search failed: {e}")
            return []

    organic_results = data.get("organic_results", [])
    prospects = []
    
    for r in organic_results:
        title = r.get("title", "")
        link = r.get("link", "")
        snippet = r.get("snippet", "")
        
        # Parse title "Name - Headline | Company"
        parts = title.split(" - ")
        name = parts[0].strip() if parts else ""
        headline = parts[1].strip() if len(parts) > 1 else ""
        
        # Simple company extraction guess from headline or snippet
        company = industry # Fallback
        if " at " in headline.lower():
            company = headline.split(" at ")[-1].strip()
        
        if name and "linkedin.com/in" in link:
            prospects.append({
                "name": name,
                "title": headline,
                "company": company,
                "linkedin": link,
                "location": location,
                "snippet": snippet
            })
            
    return prospects

async def find_contact_info(prospect: Dict[str, Any]) -> Dict[str, Any]:
    """Step 2: Find Contact Info using Google Search snippet or Google AI Mode."""
    if not settings.SERPAPI_KEY:
        return prospect

    query = f"Contact Details {prospect['name']} ,{prospect['company']}"
    params = {
        "engine": "google", # Fast fallback (n8n used google_ai_mode but google is faster/more reliable for snippets)
        "q": query,
        "api_key": settings.SERPAPI_KEY
    }
    
    # Check if we already have emails in the previous snippet
    emails = extract_emails(prospect.get('snippet', ''))
    phones = extract_phones(prospect.get('snippet', ''))
    
    if not emails:
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get("https://serpapi.com/search.json", params=params, timeout=15.0)
                res.raise_for_status()
                data = res.json()
                
                # Search through all snippets
                text_to_search = ""
                for r in data.get("organic_results", []):
                    text_to_search += r.get("snippet", "") + " "
                
                emails.extend(extract_emails(text_to_search))
                phones.extend(extract_phones(text_to_search))
                
            except Exception as e:
                print(f"SerpAPI contact search failed: {e}")

    # Remove duplicates
    emails = list(set(emails))
    phones = list(set(phones))
    
    prospect['email'] = emails[0] if emails else ""
    prospect['all_emails'] = emails
    prospect['phone'] = phones[0] if phones else ""
    
    return prospect

async def verify_email(email: str) -> str:
    """Step 3: Verify email using EmailVerify.io"""
    if not email or not settings.EMAILVERIFY_KEY:
        return "unknown"
        
    params = {
        "key": settings.EMAILVERIFY_KEY,
        "email": email
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get("https://app.emailverify.io/api/v1/validate", params=params, timeout=10.0)
            if res.status_code == 200:
                data = res.json()
                status = data.get("status", "unknown") # valid, catch_all, invalid, unknown, role_based
                return status
        except Exception as e:
            print(f"EmailVerify failed: {e}")
            
    return "unknown"

async def generate_leads_pipeline(job_title: str, industry: str, location: str, num_leads: int = 10) -> List[Dict[str, Any]]:
    """Full Lead Generation Pipeline"""
    # 1. Search LinkedIn
    prospects = await search_prospects(job_title, industry, location, max_results=num_leads)
    
    # 2. Find Contact Info concurrently
    tasks = [find_contact_info(p) for p in prospects]
    enriched_prospects = await asyncio.gather(*tasks)
    
    # 3. Verify Emails concurrently
    final_prospects = []
    verify_tasks = []
    
    for p in enriched_prospects:
        if p.get('email'):
            verify_tasks.append(verify_email(p['email']))
        else:
            # Create a dummy task returning "invalid" if no email
            async def dummy(): return "invalid"
            verify_tasks.append(dummy())
            
    verification_results = await asyncio.gather(*verify_tasks)
    
    for i, p in enumerate(enriched_prospects):
        p['email_status'] = verification_results[i]
        final_prospects.append(p)
        
    return final_prospects
