import uuid
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.core.settings import settings

# ── Database Engine (Synchronous) ───────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_platform_db():
    """
    Always returns a session to the Saarthi Managed (Platform) database.
    Used for managing organization-level metadata like BYODB config.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from fastapi import Request
def get_db(request: Request = None):
    """
    Unified database session dependency.
    If org_id is present in request.state, it routes to the correct database (BYODB).
    Otherwise, defaults to the managed Saarthi database.
    """
    from app.core.database_router import get_engine_for_org
    org_id = None
    if request:
        org_id = getattr(request.state, "org_id", None)
    
    if org_id:
        engine_to_use = get_engine_for_org(org_id)
        # Use a scoped session maker for the specific engine
        CustomSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_to_use)
        db = CustomSessionLocal()
    else:
        db = SessionLocal()
        
    try:
        yield db
    finally:
        db.close()


# ── Declarative Base ───────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Base Repository (Multi-tenant) ─────────────────
ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """
    A unified repository pattern to guarantee that EVERY query is scoped to an organization_id.
    """
    def __init__(self, model: Type[ModelType], db: Session, organization_id: uuid.UUID):
        self.model = model
        self.db = db
        self.organization_id = organization_id

    def _apply_org(self, query):
        """Helper to forcefully inject organization_id filter."""
        if hasattr(self.model, "organization_id"):
            return query.filter(self.model.organization_id == self.organization_id)
        return query

    def get(self, id: Any) -> Optional[ModelType]:
        query = self.db.query(self.model).filter(self.model.id == id)
        return self._apply_org(query).first()

    def get_multi(self, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        query = self.db.query(self.model)
        return self._apply_org(query).offset(skip).limit(limit).all()

    def get_by_field(self, **kwargs) -> Optional[ModelType]:
        query = self.db.query(self.model).filter_by(**kwargs)
        return self._apply_org(query).first()

    def create(self, *, obj_in: Dict[str, Any]) -> ModelType:
        if hasattr(self.model, "organization_id"):
            obj_in["organization_id"] = self.organization_id
            
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, *, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def remove(self, *, id: Any) -> ModelType:
        obj = self.get(id=id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
