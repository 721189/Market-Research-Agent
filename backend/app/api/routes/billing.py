from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import stripe
from backend.app.db.session import get_db
from backend.app.api.deps import get_auth_context, AuthContext
from backend.app.auth.rbac import PERM_BILLING_VIEW, PERM_BILLING_MANAGE
from backend.app.models.billing import Subscription, BillingEvent
from backend.app.models.organization import Organization
from backend.app.services.entitlement import PLAN_LIMITS
from backend.app.config import settings

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])

@router.get("/subscription")
def get_subscription(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    auth.require_permission(PERM_BILLING_VIEW)

    sub = db.query(Subscription).filter(Subscription.org_id == auth.organization.id).first()
    plan_conf = PLAN_LIMITS.get(auth.organization.plan, PLAN_LIMITS["free"])

    return {
        "organization_id": auth.organization.id,
        "plan": auth.organization.plan,
        "status": sub.status if sub else "active",
        "current_period_start": sub.current_period_start if sub else None,
        "current_period_end": sub.current_period_end if sub else None,
        "cancel_at_period_end": sub.cancel_at_period_end if sub else False,
        "limits": plan_conf
    }

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe webhook handler with signature verification.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not settings.STRIPE_WEBHOOK_SECRET or not settings.STRIPE_SECRET_KEY:
        # Graceful development acknowledgment
        return {"received": True, "mode": "development_unconfigured"}

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Webhook signature verification failed: {str(e)}")

    event_type = event["type"]
    event_obj = event["data"]["object"]

    # Record BillingEvent idempotently
    existing_event = db.query(BillingEvent).filter(BillingEvent.stripe_event_id == event["id"]).first()
    if existing_event:
        return {"received": True, "status": "duplicate"}

    # Handle subscription updates
    if event_type == "customer.subscription.updated":
        stripe_sub_id = event_obj.get("id")
        sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == stripe_sub_id).first()
        if sub:
            sub.status = event_obj.get("status", sub.status)
            db.commit()

    return {"received": True}
