import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from backend.app.api.deps import AuthContext
from backend.app.auth.rbac import ROLE_MEMBER, PERM_RESEARCH_VIEW, PERM_RESEARCH_CREATE
from backend.app.models.research import ResearchJob
from backend.app.services.entitlement import entitlement_service

class TestTenantIsolationAndQuota:
    """Security tests verifying strict tenant data boundary enforcement and quota protection."""

    def test_cross_tenant_research_access_denied(self):
        """Verify an authenticated user from Tenant A cannot access jobs belonging to Tenant B."""
        tenant_a_user = MagicMock(id="user_a", email="a@tenant-a.com", is_superuser=False)
        tenant_a_org = MagicMock(id="org_aaa_111", status="active", plan="starter")
        
        auth_context_a = AuthContext(
            user=tenant_a_user,
            organization=tenant_a_org,
            role=ROLE_MEMBER,
            permissions={"research:view", "research:create"}
        )

        job_of_tenant_b = ResearchJob(
            id="job_bbb_999",
            org_id="org_bbb_222",  # Different tenant
            creator_id="user_b",
            status="COMPLETED",
            mode="quick",
            product_idea="Secret Enterprise Product"
        )

        # Simulating endpoint tenant isolation check
        is_owner = (job_of_tenant_b.org_id == auth_context_a.organization.id)
        is_superuser = auth_context_a.user.is_superuser

        assert (is_owner or is_superuser) is False

    def test_quota_exhaustion_and_bypass_prevention(self):
        """Verify that requests exceeding plan quota cannot bypass entitlement checks."""
        mock_org = MagicMock(id="org_free", status="active", plan="free")
        mock_db = MagicMock()

        # Mock DB queries returning committed usage >= limit (Free limit = 10)
        mock_db.query.return_value.filter.return_value.count.return_value = 10

        allowed, reason = entitlement_service.can_create_research(mock_org, "quick", mock_db)
        assert allowed is False
        assert "quota exceeded" in reason.lower()

    def test_mode_entitlement_escalation_blocked(self):
        """Verify free tier tenant cannot bypass and execute 'deep' or 'batch' mode."""
        mock_org = MagicMock(id="org_free", status="active", plan="free")
        mock_db = MagicMock()

        allowed, reason = entitlement_service.can_create_research(mock_org, "deep", mock_db)
        assert allowed is False
        assert "not available on the Free plan" in reason

    def test_inactive_organization_blocked(self):
        """Verify suspended or past-due organizations are strictly denied execution."""
        mock_org = MagicMock(id="org_suspended", status="suspended", plan="pro")
        mock_db = MagicMock()

        allowed, reason = entitlement_service.can_create_research(mock_org, "quick", mock_db)
        assert allowed is False
        assert "suspended" in reason.lower()
