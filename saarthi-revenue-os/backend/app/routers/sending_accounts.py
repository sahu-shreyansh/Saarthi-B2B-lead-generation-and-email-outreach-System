import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db, BaseRepository
from app.database.models import SendingAccount, User
from app.core.deps import get_current_user, get_current_org_id, get_current_user_and_org

router = APIRouter(prefix="/sending-accounts", tags=["Sending Accounts"])

class SendingAccountResponse(BaseModel):
    id: str
    provider: str
    email: str
    is_active: bool
    daily_limit: int

@router.get("", response_model=List[SendingAccountResponse])
def list_accounts(
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    repo = BaseRepository(SendingAccount, db, org_id)
    accounts = repo.get_multi()
    return [
        {
            "id": str(a.id),
            "provider": a.provider,
            "email": a.email,
            "is_active": a.is_active,
            "daily_limit": a.daily_limit
        } for a in accounts
    ]

# Connect new accounts would go through an OAuth flow, 
# for MVP skeleton we leave it as stubbed or manually inserted mock.
@router.post("/connect/mock", response_model=SendingAccountResponse)
def connect_mock_account(
    email: str,
    provider: str, # "gmail" or "outlook"
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, org_id, _ = deps
    repo = BaseRepository(SendingAccount, db, org_id)
    account = repo.create(obj_in={
        "user_id": current_user.id,
        "provider": provider,
        "email": email,
        "refresh_token": "mock-encrypted-token", # Typically encrypted
        "is_active": True,
        "daily_limit": 50
    })
    
    return {
        "id": str(account.id),
        "provider": account.provider,
        "email": account.email,
        "is_active": account.is_active,
        "daily_limit": account.daily_limit
    }
