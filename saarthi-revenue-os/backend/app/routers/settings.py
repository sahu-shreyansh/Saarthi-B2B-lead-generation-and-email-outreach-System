from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.database.database import get_db, get_platform_db
from app.database.models import Organization, SendingAccount
from app.core.deps import get_current_user_and_org, require_role_admin

router = APIRouter(prefix="/settings", tags=["Settings"])

class SettingsUpdate(BaseModel):
    settings: Dict[str, Any]

class EmailIntegrationConfig(BaseModel):
    provider: str  # smtp, sendgrid, resend
    configuration: Dict[str, Any]

class CalendarIntegrationConfig(BaseModel):
    provider: str  # google, calendly
    configuration: Dict[str, Any]

@router.get("")
def get_org_settings(
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_platform_db)
):
    current_user, active_org_id, role = deps
    org = db.query(Organization).filter(Organization.id == active_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    settings = org.settings or {}
    return {
        "organization": {
            "id": str(org.id),
            "name": org.name,
        },
        "integrations": settings.get("integrations", {}),
        "notifications": settings.get("notifications", {})
    }

@router.patch("")
def update_org_settings(
    schema: SettingsUpdate,
    active_org_id = Depends(require_role_admin),
    db: Session = Depends(get_platform_db)
):
    org = db.query(Organization).filter(Organization.id == active_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    # Merge existing settings
    current_settings = org.settings or {}
    current_settings.update(schema.settings)
    
    org.settings = current_settings
    db.commit()
    db.refresh(org)
    
    return {
        "id": str(org.id),
        "name": org.name,
        "settings": org.settings
    }

@router.post("/integrations/email")
def configure_email_integration(
    config: EmailIntegrationConfig,
    active_org_id = Depends(require_role_admin),
    db: Session = Depends(get_platform_db)
):
    """Configure email provider (smtp, sendgrid, resend) for the organization."""
    org = db.query(Organization).filter(Organization.id == active_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if config.provider not in ("smtp", "sendgrid", "resend"):
        raise HTTPException(status_code=400, detail="Invalid provider. Must be: smtp, sendgrid, or resend")
    
    current_settings = org.settings or {}
    integrations = current_settings.get("integrations", {})
    integrations["email"] = {
        "provider": config.provider,
        "configuration": config.configuration
    }
    current_settings["integrations"] = integrations
    org.settings = current_settings
    
    # --- Sync to SendingAccount table for Outreach Workers ---
    # Invalidate existing accounts
    db.query(SendingAccount).filter(SendingAccount.organization_id == active_org_id).update({"is_active": False})
    
    # Create or update active account
    smtp_host = config.configuration.get("host")
    smtp_port = config.configuration.get("port")
    smtp_user = config.configuration.get("username")
    smtp_password = config.configuration.get("password")
    
    new_account = SendingAccount(
        organization_id=active_org_id,
        provider=config.provider,
        email=smtp_user or "unknown@domain.com",
        smtp_host=smtp_host,
        smtp_port=int(smtp_port) if smtp_port else 587,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        is_active=True,
        daily_limit=200
    )
    db.add(new_account)
    
    db.commit()
    db.refresh(org)
    
    return {"success": True}

@router.post("/integrations/calendar")
def configure_calendar_integration(
    config: CalendarIntegrationConfig,
    active_org_id = Depends(require_role_admin),
    db: Session = Depends(get_platform_db)
):
    """Configure calendar provider (google, calendly) for the organization."""
    org = db.query(Organization).filter(Organization.id == active_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if config.provider not in ("google", "calendly"):
        raise HTTPException(status_code=400, detail="Invalid provider. Must be: google or calendly")
    
    current_settings = org.settings or {}
    integrations = current_settings.get("integrations", {})
    integrations["calendar"] = {
        "provider": config.provider,
        "configuration": config.configuration
    }
    current_settings["integrations"] = integrations
    org.settings = current_settings
    
    db.commit()
    db.refresh(org)
    
    return {"success": True}
