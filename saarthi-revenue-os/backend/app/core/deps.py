import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Tuple

from app.database.database import get_db
from app.database.models import User
from app.core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_and_org(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Tuple[User, uuid.UUID, str]:
    """
    Extract user from JWT, verify token_version, and ensure they are an active 
    member of the organization_id defined in the token.
    Returns (User, organization_id_uuid, role_string)
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id_str = payload.get("sub")
    org_id_str = payload.get("active_org_id")
    token_role = payload.get("role")
    token_version = payload.get("token_version")

    if not all([user_id_str, org_id_str, token_role, token_version]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload structure",
        )

    try:
        user_id = uuid.UUID(user_id_str)
        org_id = uuid.UUID(org_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed UUIDs in token payload")

    # 1. Fetch user and verify active status & token version
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
        
    if user.token_version != token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token version expired. Please re-authenticate.")

    # 2. Verify Organizational Access matches token assertion
    if user.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have access to this Organization")

    # Double check the role matches what they were assigned
    if user.role != token_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role mismatch. Token refresh required.")

    return user, org_id, user.role


def get_current_user(deps: Tuple[User, uuid.UUID, str] = Depends(get_current_user_and_org)) -> User:
    """Convenience dependency for when ONLY the DB User object is needed."""
    user, _, _ = deps
    return user


def get_current_org_id(deps: Tuple[User, uuid.UUID, str] = Depends(get_current_user_and_org)) -> uuid.UUID:
    """Convenience dependency for strict multi-tenant filtering on API Routes."""
    _, active_org_id, _ = deps
    return active_org_id


def require_role_admin(deps: Tuple[User, uuid.UUID, str] = Depends(get_current_user_and_org)) -> uuid.UUID:
    """Enforces admin role. Returns active_org_id to cascade down to queries."""
    _, active_org_id, role = deps
    if role.lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return active_org_id
