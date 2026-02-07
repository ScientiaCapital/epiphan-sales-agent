"""Tests for phone endpoint authentication.

Verifies that /api/webhooks/phones/pending and /api/webhooks/phones/approve
require JWT authentication (added in security fix).

These endpoints are on the webhook router which intentionally has NO
router-level auth (webhooks use HMAC). The phone endpoints are BDR-facing
data endpoints that require per-endpoint Depends(require_auth).
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.middleware.auth import require_auth


@pytest.fixture
def unauthenticated_client() -> TestClient:
    """Test client WITHOUT JWT bypass — tests real auth behavior."""
    # Remove the conftest's auto-bypass so require_auth actually runs
    app.dependency_overrides.pop(require_auth, None)
    client = TestClient(app)
    yield client  # type: ignore[misc]
    # Restore bypass for other tests (conftest will also restore on next test)


class TestPhoneEndpointAuth:
    """Phone endpoints must require JWT authentication."""

    def test_pending_phones_returns_401_without_token(
        self, unauthenticated_client: TestClient
    ) -> None:
        """GET /api/webhooks/phones/pending without auth should return 401/403."""
        response = unauthenticated_client.get("/api/webhooks/phones/pending")
        assert response.status_code in (401, 403)

    def test_approve_phones_returns_401_without_token(
        self, unauthenticated_client: TestClient
    ) -> None:
        """POST /api/webhooks/phones/approve without auth should return 401/403."""
        response = unauthenticated_client.post(
            "/api/webhooks/phones/approve",
            json={"phone_ids": [1, 2, 3]},
        )
        assert response.status_code in (401, 403)

    @patch("app.services.database.supabase_client.supabase_client")
    def test_pending_phones_returns_200_with_auth(
        self, mock_db: object
    ) -> None:
        """GET /api/webhooks/phones/pending with auth bypass should return 200."""
        # Uses the conftest's autouse _bypass_jwt_auth fixture
        mock_db.get_unsynced_phones = lambda **_kwargs: []  # type: ignore[union-attr]
        client = TestClient(app)
        response = client.get("/api/webhooks/phones/pending")
        assert response.status_code == 200

    def test_webhook_endpoints_still_unauthenticated(
        self, unauthenticated_client: TestClient
    ) -> None:
        """Actual webhook endpoints should NOT require JWT (they use HMAC)."""
        # Apollo webhook — should return 400/422 (bad payload), not 401
        response = unauthenticated_client.post(
            "/api/webhooks/apollo/phone-reveal",
            json={},
        )
        # 401/403 would mean auth is blocking — anything else means the
        # endpoint is reachable (even if payload validation fails)
        assert response.status_code not in (401, 403)
