from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.db.session import get_db
from backend.app.auth.firebase import verify_token
from backend.app.auth.rbac import has_permission, ROLE_PERMISSIONS
from backend.app.models.user import User
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.services.security import security_service
from backend.app.services.entitlement import entitlement_service
from backend.app.config import settings

class AuthContext:
    def __init__(self, user: User, organization: Organization, role: str, auth_method: str = "jwt", permissions: Optional[Any] = None):
        self.user = user
        self.organization = organization
        self.role = role
        self.auth_method = auth_method
        self.permissions = permissions if permissions is not None else ROLE_PERMISSIONS.get(role, set())

    def has_permission(self, permission: str) -> bool:
        if getattr(self.user, "is_superuser", False):
            return True
        if self.permissions and (permission in self.permissions or "*" in self.permissions):
            return True
        return has_permission(self.role, permission)

    def require_permission(self, permission: str):
        if not self.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission}' required"
            )

def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        # Check if local development mode fallback is enabled
        if settings.ENVIRONMENT == "development" or settings.DEBUG:
            dev_user = db.query(User).filter(User.email == "dev@marketai.app").first()
            if not dev_user:
                dev_user = User(
                    email="dev@marketai.app",
                    firebase_uid="dev-uid-12345",
                    full_name="Developer"
                )
                db.add(dev_user)
                db.commit()
                db.refresh(dev_user)
            return dev_user

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "").strip()
    try:
        decoded = verify_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Sync / find user in PostgreSQL
    user = db.query(User).filter(
        (User.firebase_uid == decoded["uid"]) | (User.email == decoded["email"])
    ).first()

    if not user:
        user = User(
            firebase_uid=decoded["uid"],
            email=decoded["email"],
            full_name=decoded.get("name")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user

def get_auth_context(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    org_id_header: Optional[str] = Header(None, alias="X-Organization-ID"),
    db: Session = Depends(get_db)
) -> AuthContext:
    """
    Authoritative authentication and multi-tenant context resolver.
    Supports:
    1. Programmatic API Key (via X-API-Key or Authorization: Bearer mk_live_...)
    2. User Session Token (via Firebase JWT)
    Strictly verifies tenant active status and RBAC role.
    """
    # 1. Check for API Key Authentication
    raw_api_key = x_api_key
    if not raw_api_key and authorization and "mk_live_" in authorization:
        raw_api_key = authorization.replace("Bearer ", "").strip()

    if raw_api_key:
        api_result = security_service.verify_api_key(db, raw_api_key)
        if not api_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or revoked API Key"
            )
        api_key_obj, org, user = api_result

        # Validate tenant entitlement
        if not entitlement_service.can_use_api(org):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API access is not enabled on your organization's subscription tier"
            )

        if org.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Organization workspace is currently {org.status}"
            )

        return AuthContext(user=user, organization=org, role=api_key_obj.role, auth_method="api_key")

    # 2. JWT / User Session Authentication
    user = get_current_user(request, authorization, db)

    # Check memberships
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).all()

    # If no organizations exist yet for this user, create a default organization
    if not memberships:
        default_org = Organization(
            name=f"{user.email.split('@')[0]}'s Workspace",
            slug=f"org-{user.id[:8]}",
            plan="free",
            status="active"
        )
        db.add(default_org)
        db.commit()
        db.refresh(default_org)

        member = OrganizationMember(
            org_id=default_org.id,
            user_id=user.id,
            role="owner"
        )
        db.add(member)
        db.commit()
        
        return AuthContext(user=user, organization=default_org, role="owner", auth_method="jwt")

    # If org_id specified via header, verify membership
    target_org_id = org_id_header
    chosen_membership = None

    if target_org_id:
        for m in memberships:
            if m.org_id == target_org_id:
                chosen_membership = m
                break
        if not chosen_membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have access to the specified organization"
            )
    else:
        chosen_membership = memberships[0]

    org = db.query(Organization).filter(Organization.id == chosen_membership.org_id).first()
    if not org or org.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization workspace is {org.status if org else 'not found'}"
        )

    return AuthContext(user=user, organization=org, role=chosen_membership.role, auth_method="jwt")
