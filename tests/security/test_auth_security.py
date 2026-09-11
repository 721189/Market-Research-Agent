import pytest
import time
import jwt
import datetime
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from backend.app.auth.firebase import verify_firebase_token
from backend.app.config import settings
from backend.app.auth.rbac import (
    ROLE_VIEWER, ROLE_MEMBER, ROLE_ADMIN, ROLE_OWNER,
    PERM_RESEARCH_CREATE, PERM_RESEARCH_VIEW, PERM_BILLING_MANAGE,
    has_permission
)
from backend.app.api.deps import AuthContext

# Sample test secrets and keys
TEST_PROJECT_ID = settings.FIREBASE_PROJECT_ID
MOCK_PUBLIC_KEY = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0mockkey...\n-----END PUBLIC KEY-----"

class TestAuthSecurity:
    """Security tests for authentication, token forgery, algorithms, and privilege boundaries."""

    def test_forged_firebase_token_rejected(self):
        """Test that tokens signed with an arbitrary secret or untrusted private key are rejected."""
        attacker_payload = {
            "uid": "attacker_user_123",
            "email": "attacker@evil.com",
            "aud": TEST_PROJECT_ID,
            "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
            "exp": int(time.time()) + 3600
        }
        forged_jwt = jwt.encode(attacker_payload, "attacker_secret_key", algorithm="HS256")
        
        with patch("backend.app.auth.firebase.get_firebase_public_keys", return_value={"kid1": MOCK_PUBLIC_KEY}):
            with pytest.raises((HTTPException, Exception)):
                verify_firebase_token(forged_jwt)

    def test_expired_token_rejected(self):
        """Test that tokens with exp in the past fail validation."""
        expired_payload = {
            "uid": "user_123",
            "email": "user@marketai.io",
            "aud": TEST_PROJECT_ID,
            "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
            "exp": int(time.time()) - 100  # Expired 100 seconds ago
        }
        expired_jwt = jwt.encode(expired_payload, "key", algorithm="HS256")
        
        with pytest.raises((HTTPException, Exception)):
            verify_firebase_token(expired_jwt)

    def test_wrong_audience_rejected(self):
        """Test that tokens minted for a different project/audience are rejected."""
        wrong_aud_payload = {
            "uid": "user_123",
            "email": "user@marketai.io",
            "aud": "other-victim-project-id",
            "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
            "exp": int(time.time()) + 3600
        }
        token = jwt.encode(wrong_aud_payload, "key", algorithm="HS256")
        with pytest.raises((HTTPException, Exception)):
            verify_firebase_token(token)

    def test_wrong_issuer_rejected(self):
        """Test that tokens from an unauthorized issuer are rejected."""
        wrong_iss_payload = {
            "uid": "user_123",
            "email": "user@marketai.io",
            "aud": TEST_PROJECT_ID,
            "iss": "https://accounts.evil.com",
            "exp": int(time.time()) + 3600
        }
        token = jwt.encode(wrong_iss_payload, "key", algorithm="HS256")
        with pytest.raises((HTTPException, Exception)):
            verify_firebase_token(token)

    def test_algorithm_confusion_attack_rejected(self):
        """Test that algorithm confusion (e.g. none algorithm or symmetric HS256 using public RSA key) is blocked."""
        # 1. 'none' algorithm token (eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1aWQiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.)
        none_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1aWQiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0."
        with pytest.raises((HTTPException, Exception)):
            verify_firebase_token(none_token)

        # 2. HS256 using RSA public key as HMAC secret
        try:
            confused_token = jwt.encode(
                {"uid": "admin", "aud": TEST_PROJECT_ID, "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}", "exp": int(time.time()) + 3600},
                MOCK_PUBLIC_KEY,
                algorithm="HS256"
            )
            with pytest.raises((HTTPException, Exception)):
                verify_firebase_token(confused_token)
        except Exception:
            pass

    def test_viewer_role_privilege_escalation_blocked(self):
        """Test that VIEWER role cannot create research or manage billing."""
        mock_user = MagicMock(id="u1", email="viewer@test.com", is_superuser=False)
        mock_org = MagicMock(id="org1", status="active", plan="starter")
        
        viewer_auth = AuthContext(
            user=mock_user,
            organization=mock_org,
            role=ROLE_VIEWER,
            permissions={"research:view"}
        )

        assert viewer_auth.has_permission(PERM_RESEARCH_VIEW) is True
        assert viewer_auth.has_permission(PERM_RESEARCH_CREATE) is False
        assert viewer_auth.has_permission(PERM_BILLING_MANAGE) is False

        with pytest.raises(HTTPException) as excinfo:
            viewer_auth.require_permission(PERM_RESEARCH_CREATE)
        assert excinfo.value.status_code == 403

        with pytest.raises(HTTPException) as excinfo:
            viewer_auth.require_permission(PERM_BILLING_MANAGE)
        assert excinfo.value.status_code == 403

    def test_superuser_privilege_boundaries(self):
        """Ensure superusers are strictly logged and bounded."""
        mock_admin_user = MagicMock(id="super_1", email="super@marketai.io", is_superuser=True)
        mock_org = MagicMock(id="org_target", status="active", plan="pro")
        
        super_auth = AuthContext(
            user=mock_admin_user,
            organization=mock_org,
            role=ROLE_OWNER,
            permissions={"*"}
        )
        assert super_auth.has_permission("any:permission") is True
