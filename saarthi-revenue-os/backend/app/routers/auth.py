from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from app.database.database import get_db
from app.database.models import User, Organization
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.deps import get_current_user_and_org

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    organization_name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: str
    organization_id: str
    role: str

@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Registers a new Organization and its first Admin User."""
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 1. Create Organization
    org = Organization(name=req.organization_name)
    db.add(org)
    db.commit()
    db.refresh(org)

    # 2. Create User
    user = User(
        email=req.email,
        password_hash=get_password_hash(req.password),
        organization_id=org.id,
        role="admin"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 4. Generate Token
    access_token = create_access_token(
        user_id=user.id, 
        org_id=org.id, 
        role=user.role, 
        token_version=user.token_version
    )
    return {"access_token": access_token}


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Local email/password login."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")

    access_token = create_access_token(
        user_id=user.id, 
        org_id=user.organization_id, 
        role=user.role, 
        token_version=user.token_version
    )
    return {"access_token": access_token}


@router.get("/me", response_model=UserResponse)
def read_users_me(
    deps = Depends(get_current_user_and_org)
):
    """Fetch current user details from current JWT Context."""
    user, active_org_id, role = deps

    return {
        "id": str(user.id),
        "email": user.email,
        "organization_id": str(active_org_id),
        "role": role,
    }
