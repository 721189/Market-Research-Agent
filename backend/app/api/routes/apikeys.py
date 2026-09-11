import uuid
import hashlib
import secrets
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.api.deps import get_auth_context, AuthContext
from backend.app.models.organization import ApiKey
from backend.app.auth.rbac import PERM_ADMIN_MANAGE_KEYS

router = APIRouter(prefix="/api/v1/apikeys", tags=["API Key Management"])

class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field("member", pattern="^(admin|member|viewer)$")

class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    role: str
    is_revoked: bool
    created_at: str
    last_used_at: Optional[str] = None

class CreateApiKeyResponse(ApiKeyResponse):
    secret_key: str # Only returned once upon creation

@router.get("", response_model=List[ApiKeyResponse])
def list_api_keys(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """Lists all API keys configured for the tenant organization."""
    auth.require_permission(PERM_ADMIN_MANAGE_KEYS)

    keys = db.query(ApiKey).filter(
        ApiKey.org_id == auth.organization.id,
        ApiKey.is_revoked == False
    ).order_by(ApiKey.created_at.desc()).all()

    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            role=k.role,
            is_revoked=k.is_revoked,
            created_at=k.created_at.isoformat(),
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None
        )
        for k in keys
    ]

@router.post("", response_model=CreateApiKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: CreateApiKeyRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """Generates a new API key for programmatic workspace integration."""
    auth.require_permission(PERM_ADMIN_MANAGE_KEYS)

    raw_token = f"mk_live_{secrets.token_urlsafe(32)}"
    key_prefix = raw_token[:12] + "..."
    key_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    key_id = f"key_{uuid.uuid4().hex[:12]}"
    now = datetime.datetime.utcnow()

    api_key = ApiKey(
        id=key_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=payload.name,
        role=payload.role,
        user_id=auth.user.id,
        org_id=auth.organization.id,
        is_revoked=False,
        created_at=now
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return CreateApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        role=api_key.role,
        is_revoked=api_key.is_revoked,
        created_at=api_key.created_at.isoformat(),
        secret_key=raw_token
    )

@router.delete("/{key_id}")
def revoke_api_key(
    key_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """Revokes an API key for the organization."""
    auth.require_permission(PERM_ADMIN_MANAGE_KEYS)

    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.org_id == auth.organization.id
    ).first()

    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    api_key.is_revoked = True
    db.commit()

    return {"message": "API key revoked successfully", "id": key_id}
