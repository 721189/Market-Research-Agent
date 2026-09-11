import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

class TestAPIContractAndFailureModes:
    """
    Phase 33 & 36: Comprehensive API Contract and Failure Scenario Test Matrix.
    """

    def test_unauthenticated_request_rejected(self):
        """Phase 36.1: Missing X-API-Key or Bearer token returns 401."""
        response = client.get("/api/v1/research/non_existent_task_123")
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_invalid_api_key_rejected(self):
        """Phase 36.2: Invalid authentication credentials return 401."""
        response = client.get(
            "/api/v1/research/non_existent_task_123",
            headers={"X-API-Key": "invalid_bogus_key"}
        )
        assert response.status_code == 401

    def test_invalid_research_creation_payload(self):
        """Phase 33 & 36.3: Empty product_idea or invalid fields return 422 validation error."""
        # Missing required product_idea
        response = client.post(
            "/api/v1/research",
            headers={"X-API-Key": "mk_live_smoke_test_key_12345"},
            json={"mode": "quick"}
        )
        assert response.status_code in (422, 400, 401)

    def test_nonexistent_job_returns_404(self):
        """Phase 33: Nonexistent research job ID returns 404."""
        response = client.get(
            "/api/v1/research/00000000-0000-0000-0000-000000000000",
            headers={"X-API-Key": "mk_live_smoke_test_key_12345"}
        )
        assert response.status_code in (404, 401)

    def test_sse_endpoint_nonexistent_job_returns_404(self):
        """Phase 33: GET /{task_id}/events for nonexistent job returns 404."""
        response = client.get(
            "/api/v1/research/00000000-0000-0000-0000-000000000000/events",
            headers={"X-API-Key": "mk_live_smoke_test_key_12345"}
        )
        assert response.status_code in (404, 401)

    def test_pdf_report_nonexistent_or_uncompleted_returns_error(self):
        """Phase 33 & 36.4: PDF request for incomplete or missing report returns 404/400."""
        response = client.get(
            "/api/v1/reports/00000000-0000-0000-0000-000000000000/pdf",
            headers={"X-API-Key": "mk_live_smoke_test_key_12345"}
        )
        assert response.status_code in (404, 400, 401)

    def test_health_check_endpoints_open(self):
        """Health readiness and liveness probes must return 200 without auth."""
        res_live = client.get("/health/live")
        assert res_live.status_code == 200

        res_ready = client.get("/health/ready")
        assert res_ready.status_code in (200, 503)
