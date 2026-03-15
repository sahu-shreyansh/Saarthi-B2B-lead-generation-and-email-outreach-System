from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from app.database.database import get_db, get_platform_db
from app.database.models import OrganizationDatabaseConfig
from app.core.database_router import test_external_connection, run_migrations_for_org, clear_engine_cache
from app.core.encryption import encrypt_secret

router = APIRouter(prefix="/database", tags=["database"])

class DatabaseTestRequest(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password: str

class DatabaseConnectRequest(DatabaseTestRequest):
    mode: str = "external"

@router.post("/test")
async def test_db_connection(data: DatabaseTestRequest):
    """Tests an external database connection before saving."""
    success = test_external_connection(data.dict())
    if not success:
        raise HTTPException(status_code=400, detail="Database connection failed. Please check your credentials.")
    return {"success": True}

@router.post("/connect")
async def connect_external_db(data: DatabaseConnectRequest, request: Request, db: Session = Depends(get_platform_db)):
    """Saves the database configuration for the organization."""
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(status_code=401, detail="Organization context missing.")

    # 1. Test again for safety
    if not test_external_connection(data.dict()):
         raise HTTPException(status_code=400, detail="Database connection failed.")

    # 2. Encrypt password
    encrypted_password = encrypt_secret(data.password)

    # 3. Save or update config
    config = db.query(OrganizationDatabaseConfig).filter(
        OrganizationDatabaseConfig.organization_id == org_id
    ).first()

    if not config:
        config = OrganizationDatabaseConfig(
            organization_id=org_id,
            mode="external",
            db_host=data.host,
            db_port=data.port,
            db_name=data.database,
            db_user=data.user,
            db_password_encrypted=encrypted_password
        )
        db.add(config)
    else:
        config.mode = "external"
        config.db_host = data.host
        config.db_port = data.port
        config.db_name = data.database
        config.db_user = data.user
        config.db_password_encrypted = encrypted_password

    db.commit()
    
    # 4. Refresh engine cache in case settings changed
    clear_engine_cache(org_id)

    # 5. Trigger Automatic Schema Setup (Phase 7)
    db_url = f"postgresql://{data.user}:{data.password}@{data.host}:{data.port}/{data.database}"
    migration_success = run_migrations_for_org(db_url)
    
    if not migration_success:
        return {
            "success": True, 
            "message": "Database config saved, but automatic migration failed. Please check logs.",
            "migration_status": "failed"
        }

    return {"success": True, "message": "External database connected and schema initialized successfully."}

@router.post("/disconnect")
async def disconnect_external_db(request: Request, db: Session = Depends(get_platform_db)):
    """Reverts the organization to the managed Saarthi database."""
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(status_code=401, detail="Organization context missing.")

    config = db.query(OrganizationDatabaseConfig).filter(
        OrganizationDatabaseConfig.organization_id == org_id
    ).first()

    if config:
        config.mode = "managed"
        db.commit()
        # Clear external engine from cache
        clear_engine_cache(org_id)
    
    return {"success": True, "message": "Reverted to managed Saarthi database."}
