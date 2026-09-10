from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.db.session import get_db
from backend.app.auth.firebase import verify_token
from backend.app.auth.rbac import has_permission
from backend.app.models.user import User
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.config import settings

class AuthContext:
    def __init__(self, user: User, organization: Organization, role: str):
        self.user = user
        self.organization = organization
        self.role = role

    def require_permission(self, permission: str):
        if not has_permission(self.role, permission):
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
            # Fallback dev user
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
    user: User = Depends(get_current_user),
    org_id_header: Optional[str] = Header(None, alias="X-Organization-ID"),
    db: Session = Depends(get_db)
) -> AuthContext:
    # Check memberships
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).all()

    # If no organizations exist yet for this user, create a default organization
    if not memberships:
        default_org = Organization(
            name=f"{user.email.split('@')[0]}'s Workspace",
            slug=f"org-{user.id[:8]}",
            plan="free"
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
        
        return AuthContext(user=user, organization=default_org, role="owner")

    # If org_id specified (either via header or body if checked later), verify membership
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
        # Default to first organization
        chosen_membership = memberships[0]

    org = db.query(Organization).filter(Organization.id == chosen_membership.org_id).first()
    return AuthContext(user=user, organization=org, role=chosen_membership.role)
