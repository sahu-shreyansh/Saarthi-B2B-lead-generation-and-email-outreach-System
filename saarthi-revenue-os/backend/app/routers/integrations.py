import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database.database import get_db, get_platform_db
from app.database.models import Organization
from app.core.deps import get_current_org_id, require_role_admin
from app.core.security import encrypt_string, decrypt_string
from app.core.settings import settings

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

# ── Pydantic Schemas ──────────────────────────────────────────────────

class IntegrationsStatus(BaseModel):
    apify_connected: bool
    serpapi_connected: bool
    openrouter_connected: bool
    selected_model: Optional[str]
    ai_usage_tokens: int
    ai_usage_limit: int

class ApiKeyUpdate(BaseModel):
    api_key: str

class OpenRouterUpdate(BaseModel):
    api_key: str
    model: Optional[str] = "mistralai/mistral-7b-instruct"

class TestConnectionRequest(BaseModel):
    service: str # apify, serpapi, openrouter

class OpenRouterModel(BaseModel):
    id: str
    name: str

# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("", response_model=IntegrationsStatus)
def get_integrations_status(
    db: Session = Depends(get_platform_db),
    org_id: uuid.UUID = Depends(get_current_org_id)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    return {
        "apify_connected": bool(org.apify_api_key),
        "serpapi_connected": bool(org.serpapi_api_key),
        "openrouter_connected": bool(org.openrouter_api_key),
        "selected_model": org.default_llm_model,
        "ai_usage_tokens": org.ai_usage_tokens,
        "ai_usage_limit": org.ai_usage_limit
    }

@router.post("/apify")
def save_apify_key(
    data: ApiKeyUpdate,
    db: Session = Depends(get_platform_db),
    org_id: uuid.UUID = Depends(require_role_admin)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    org.apify_api_key = encrypt_string(data.api_key)
    db.commit()
    return {"status": "success", "message": "Apify API Key updated"}

@router.post("/serpapi")
def save_serpapi_key(
    data: ApiKeyUpdate,
    db: Session = Depends(get_platform_db),
    org_id: uuid.UUID = Depends(require_role_admin)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    org.serpapi_api_key = encrypt_string(data.api_key)
    db.commit()
    return {"status": "success", "message": "SerpAPI Key updated"}

@router.post("/openrouter")
def save_openrouter_key(
    data: OpenRouterUpdate,
    db: Session = Depends(get_platform_db),
    org_id: uuid.UUID = Depends(require_role_admin)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    org.openrouter_api_key = encrypt_string(data.api_key)
    if data.model:
        org.default_llm_model = data.model
    db.commit()
    return {"status": "success", "message": "OpenRouter configuration updated"}

@router.post("/test")
async def test_integration(
    req: TestConnectionRequest,
    db: Session = Depends(get_platform_db),
    org_id: uuid.UUID = Depends(get_current_org_id)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    
    if req.service == "apify":
        key = decrypt_string(org.apify_api_key)
        if not key: raise HTTPException(400, "Apify key not set")
        async with httpx.AsyncClient() as client:
            res = await client.get(f"https://api.apify.com/v2/acts?token={key}")
            if res.status_code == 200: return {"status": "ok"}
            else: return {"status": "error", "detail": res.text}

    elif req.service == "serpapi":
        key = decrypt_string(org.serpapi_api_key)
        if not key: raise HTTPException(400, "SerpAPI key not set")
        async with httpx.AsyncClient() as client:
            res = await client.get(f"https://serpapi.com/search?q=test&api_key={key}")
            if res.status_code == 200: return {"status": "ok"}
            else: return {"status": "error", "detail": res.text}

    elif req.service == "openrouter":
        key = decrypt_string(org.openrouter_api_key)
        if not key: raise HTTPException(400, "OpenRouter key not set")
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {key}"}
            )
            if res.status_code == 200: return {"status": "ok"}
            else: return {"status": "error", "detail": res.text}

    else:
        raise HTTPException(400, "Unknown service")

@router.get("/models")
async def get_openrouter_models(
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: Session = Depends(get_platform_db),
):
    """
    Dynamically fetch available models from OpenRouter.
    Uses the org's own API key if configured, otherwise the platform key.
    Falls back to a curated static list if the request fails.
    """
    from app.core.settings import settings
    from app.core.security import decrypt_string
    from app.database.models import Organization

    # Resolve API key (use org key if available)
    api_key = getattr(settings, "OPENROUTER_API_KEY", None) or ""
    try:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if org and org.openrouter_api_key:
            decrypted = decrypt_string(org.openrouter_api_key)
            if decrypted:
                api_key = decrypted
    except Exception as e:
        print(f"[Models] Error fetching org config: {e}")
        pass

    # Static fallback in case the OpenRouter call fails
    FALLBACK_MODELS = [
        {"id": "mistralai/mistral-7b-instruct", "name": "Mistral 7B Instruct (Free)"},
        {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini"},
        {"id": "openai/gpt-4o", "name": "GPT-4o"},
        {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
        {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku"},
        {"id": "google/gemini-pro", "name": "Gemini Pro"},
        {"id": "meta-llama/llama-3-8b-instruct", "name": "Llama 3 8B Instruct (Free)"},
    ]

    if not api_key:
        return FALLBACK_MODELS

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://saarthi.ai",
                    "X-Title": "Saarthi Revenue OS",
                },
            )

        if res.status_code != 200:
            print(f"[Models] OpenRouter returned {res.status_code} — using fallback.")
            return FALLBACK_MODELS

        data = res.json()
        if not isinstance(data, dict):
            return FALLBACK_MODELS
            
        raw_data = data.get("data", [])
        if not isinstance(raw_data, list):
            return FALLBACK_MODELS

        models = []
        for m in raw_data:
            if not isinstance(m, dict):
                continue
            m_id = m.get("id")
            m_name = m.get("name") or m_id
            if m_id and isinstance(m_id, str):
                models.append({"id": m_id, "name": str(m_name)})

        return models if models else FALLBACK_MODELS

    except Exception as e:
        print(f"[Models] Exception fetching OpenRouter models: {e}")
        return FALLBACK_MODELS
