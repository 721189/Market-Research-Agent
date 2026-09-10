import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import stripe
from backend.app.db.session import get_db
from backend.app.api.deps import get_auth_context, AuthContext
from backend.app.auth.rbac import PERM_BILLING_VIEW, PERM_BILLING_MANAGE
from backend.app.models.billing import Subscription, BillingEvent
from backend.app.models.organization import Organization
from backend.app.services.entitlement import PLAN_LIMITS
from backend.app.config import settings

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])

class CheckoutSessionRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str

class PortalSessionRequest(BaseModel):
    return_url: str

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
        "stripe_customer_id": sub.stripe_customer_id if sub else None,
        "limits": plan_conf
    }

@router.post("/create-checkout-session")
def create_checkout_session(
    payload: CheckoutSessionRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    auth.require_permission(PERM_BILLING_MANAGE)

    if payload.plan not in ("starter", "pro", "enterprise"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan selected")

    if not settings.STRIPE_SECRET_KEY:
        # Development fallback session
        return {
            "session_id": f"dev_session_{auth.organization.id}_{payload.plan}",
            "url": f"{payload.success_url}?session_id=mock_success"
        }

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        # Look up existing customer ID
        sub = db.query(Subscription).filter(Subscription.org_id == auth.organization.id).first()
        customer_kwargs = {}
        if sub and sub.stripe_customer_id:
            customer_kwargs["customer"] = sub.stripe_customer_id
        else:
            customer_kwargs["customer_email"] = auth.user.email

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            client_reference_id=auth.organization.id,
            metadata={
                "org_id": auth.organization.id,
                "plan": payload.plan,
                "user_id": auth.user.id
            },
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"MarketAI {payload.plan.capitalize()} Plan",
                        "description": f"Market intelligence subscription ({payload.plan} tier)"
                    },
                    "unit_amount": 4900 if payload.plan == "starter" else (19900 if payload.plan == "pro" else 99900),
                    "recurring": {"interval": "month"}
                },
                "quantity": 1
            }],
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
            **customer_kwargs
        )
        return {"session_id": session.id, "url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.user_message or e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Stripe session creation failed: {str(e)}")

@router.post("/create-portal-session")
def create_customer_portal_session(
    payload: PortalSessionRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Creates a Stripe Customer Portal session for subscription management, invoice downloads, and card updates.
    """
    auth.require_permission(PERM_BILLING_MANAGE)

    sub = db.query(Subscription).filter(Subscription.org_id == auth.organization.id).first()
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active Stripe customer found for this organization. Upgrade to a paid plan first."
        )

    if not settings.STRIPE_SECRET_KEY:
        return {"url": f"{payload.return_url}?portal=mock"}

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=payload.return_url
        )
        return {"url": portal_session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.user_message or e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Portal creation failed: {str(e)}")

@router.post("/cancel-subscription")
def cancel_subscription(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """Schedules subscription cancellation at the end of the current billing cycle."""
    auth.require_permission(PERM_BILLING_MANAGE)

    sub = db.query(Subscription).filter(Subscription.org_id == auth.organization.id).first()
    if not sub or not sub.stripe_subscription_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found")

    if settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            stripe.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=True
            )
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    sub.cancel_at_period_end = True
    db.commit()
    return {"status": "scheduled_cancellation", "cancel_at_period_end": True}

@router.post("/resume-subscription")
def resume_subscription(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """Reactivates a subscription that was marked to cancel at period end."""
    auth.require_permission(PERM_BILLING_MANAGE)

    sub = db.query(Subscription).filter(Subscription.org_id == auth.organization.id).first()
    if not sub or not sub.stripe_subscription_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found")

    if settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            stripe.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=False
            )
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    sub.cancel_at_period_end = False
    db.commit()
    return {"status": "resumed", "cancel_at_period_end": False}

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Robust Stripe webhook handler with signature verification,
    idempotent event processing, and comprehensive lifecycle state synchronization.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not settings.STRIPE_WEBHOOK_SECRET or not settings.STRIPE_SECRET_KEY:
        return {"received": True, "mode": "development_unconfigured"}

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook signature verification failed: {str(e)}"
        )

    event_type = event["type"]
    event_id = event["id"]
    event_obj = event["data"]["object"]

    # 1. Idempotency check: record BillingEvent
    existing_event = db.query(BillingEvent).filter(BillingEvent.stripe_event_id == event_id).first()
    if existing_event:
        return {"received": True, "status": "duplicate_ignored"}

    # Resolve organization ID
    org_id = None
    if "metadata" in event_obj and event_obj["metadata"].get("org_id"):
        org_id = event_obj["metadata"]["org_id"]
    elif event_obj.get("client_reference_id"):
        org_id = event_obj.get("client_reference_id")
    elif event_obj.get("customer"):
        sub_by_cust = db.query(Subscription).filter(Subscription.stripe_customer_id == event_obj["customer"]).first()
        if sub_by_cust:
            org_id = sub_by_cust.org_id

    # Fallback to first active org if unresolvable
    if not org_id:
        fallback_org = db.query(Organization).first()
        org_id = fallback_org.id if fallback_org else "unknown"

    # Save billing event record
    billing_log = BillingEvent(
        org_id=org_id,
        event_type=event_type,
        amount_cents=event_obj.get("amount_total") or event_obj.get("amount_paid") or 0,
        currency=event_obj.get("currency", "usd"),
        status=event_obj.get("status", "succeeded"),
        stripe_event_id=event_id,
        event_payload=event_obj
    )
    db.add(billing_log)

    # 2. Lifecycle state machines
    if event_type == "checkout.session.completed":
        target_org_id = event_obj.get("client_reference_id") or (event_obj.get("metadata", {}).get("org_id"))
        purchased_plan = event_obj.get("metadata", {}).get("plan", "starter")
        stripe_cust_id = event_obj.get("customer")
        stripe_sub_id = event_obj.get("subscription")

        if target_org_id:
            org = db.query(Organization).filter(Organization.id == target_org_id).first()
            if org:
                org.plan = purchased_plan

            sub = db.query(Subscription).filter(Subscription.org_id == target_org_id).first()
            if not sub:
                sub = Subscription(
                    org_id=target_org_id,
                    plan_id=purchased_plan,
                    status="active",
                    stripe_customer_id=stripe_cust_id,
                    stripe_subscription_id=stripe_sub_id
                )
                db.add(sub)
            else:
                sub.plan_id = purchased_plan
                sub.status = "active"
                sub.stripe_customer_id = stripe_cust_id
                sub.stripe_subscription_id = stripe_sub_id

    elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
        stripe_sub_id = event_obj.get("id")
        sub_status = event_obj.get("status", "active")
        cancel_at_period_end = event_obj.get("cancel_at_period_end", False)
        current_period_end_ts = event_obj.get("current_period_end")

        sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == stripe_sub_id).first()
        if sub:
            sub.status = sub_status
            sub.cancel_at_period_end = cancel_at_period_end
            if current_period_end_ts:
                sub.current_period_end = datetime.datetime.utcfromtimestamp(current_period_end_ts)

    elif event_type == "customer.subscription.deleted":
        stripe_sub_id = event_obj.get("id")
        sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == stripe_sub_id).first()
        if sub:
            sub.status = "canceled"
            org = db.query(Organization).filter(Organization.id == sub.org_id).first()
            if org:
                # Downgrade to free tier upon subscription termination
                org.plan = "free"

    elif event_type == "invoice.payment_failed":
        stripe_cust_id = event_obj.get("customer")
        sub = db.query(Subscription).filter(Subscription.stripe_customer_id == stripe_cust_id).first()
        if sub:
            sub.status = "past_due"

    elif event_type == "invoice.payment_action_required":
        # 3DS authentication required
        stripe_cust_id = event_obj.get("customer")
        sub = db.query(Subscription).filter(Subscription.stripe_customer_id == stripe_cust_id).first()
        if sub:
            sub.status = "incomplete"

    elif event_type == "invoice.payment_succeeded":
        stripe_cust_id = event_obj.get("customer")
        sub = db.query(Subscription).filter(Subscription.stripe_customer_id == stripe_cust_id).first()
        if sub:
            sub.status = "active"

    db.commit()
    return {"received": True, "event_type": event_type}
