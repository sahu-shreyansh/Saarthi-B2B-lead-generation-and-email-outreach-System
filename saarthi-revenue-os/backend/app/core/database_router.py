import uuid
import logging
from typing import Dict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.settings import settings
from app.core.encryption import decrypt_secret

logger = logging.getLogger(__name__)

# Engine Cache: organization_id -> sqlalchemy.Engine
_engines: Dict[uuid.UUID, Engine] = {}

def get_engine_for_org(organization_id: uuid.UUID) -> Engine:
    """
    Dynamically resolve or create a SQLAlchemy engine for the given organization.
    Returns the platform engine if the organization is in 'managed' mode or config is missing.
    """
    if not organization_id:
        from app.database.database import engine as platform_engine
        return platform_engine

    if organization_id in _engines:
        return _engines[organization_id]

    # We need a temporary DB session to fetch the config.
    # We use the platform engine for this metadata lookup.
    from app.database.database import SessionLocal, engine as platform_engine
    from app.database.models import OrganizationDatabaseConfig

    db = SessionLocal()
    try:
        config = db.query(OrganizationDatabaseConfig).filter(
            OrganizationDatabaseConfig.organization_id == organization_id
        ).first()

        if not config or config.mode == "managed":
            # Cache the default engine too to avoid repeated lookups
            _engines[organization_id] = platform_engine
            return platform_engine
        
        # Construct External DB URL
        # Format: postgresql://user:password@host:port/dbname
        password = decrypt_secret(config.db_password_encrypted) or ""
        db_url = f"postgresql://{config.db_user}:{password}@{config.db_host}:{config.db_port}/{config.db_name}"
        
        logger.info(f"Creating external database engine for Org {organization_id}")
        
        new_engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        
        # Cache it
        _engines[organization_id] = new_engine
        return new_engine

    except Exception as e:
        logger.error(f"Error resolving engine for Org {organization_id}: {str(e)}")
        # Fallback to platform engine on failure
        return platform_engine
    finally:
        db.close()

import subprocess
import os

def run_migrations_for_org(db_url: str) -> bool:
    """Triggers alembic upgrade head for a specific database URL."""
    try:
        # Resolve the backend directory where alembic.ini lives
        backend_dir = "/Users/abhisheksahu/Downloads/Shreyansh/Saarthi/saarthi-revenue-os/backend"
        
        logger.info(f"Running migrations for external database...")
        
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            env={**os.environ, "DATABASE_URL": db_url},
            capture_output=True,
            text=True,
            cwd=backend_dir
        )
        
        if result.returncode != 0:
            logger.error(f"Alembic migration failed: {result.stderr}")
            return False
            
        logger.info("Migrations completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        return False

def test_external_connection(config_data: dict) -> bool:
    """Tests a provided database configuration without saving it."""
    db_url = f"postgresql://{config_data['user']}:{config_data['password']}@{config_data['host']}:{config_data['port']}/{config_data['database']}"
    try:
        temp_engine = create_engine(db_url, connect_args={'connect_timeout': 5})
        with temp_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False
def clear_engine_cache(organization_id: uuid.UUID):
    """Removes the engine for the given organization from the cache."""
    if organization_id in _engines:
        logger.info(f"Clearing database engine cache for Org {organization_id}")
        # Optionally dispose of the engine to close connections
        try:
            _engines[organization_id].dispose()
        except Exception:
            pass
        del _engines[organization_id]
