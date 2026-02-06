"""Tests for Clay.com webhook endpoint.

PHONES ARE GOLD! Clay POSTs enrichment results back to us
after enriching leads through its 75+ provider waterfall.
"""

import hashlib
import hmac as hmac_module
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _sign_payload(payload: dict, secret: str = "test-secret") -> str:
    """Generate HMAC-SHA256 signature for a payload."""
    body = json.dumps(payload).encode()
    return hmac_module.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _clay_payload(
    lead_id: str = "lead_123",
    phones: list | None = None,
    emails: list | None = None,
    **kwargs: object,
) -> dict:
    """Build a Clay webhook payload."""
    return {
        "lead_id": lead_id,
        "phones": phones or [],
        "emails": emails or [],
        "company_name": kwargs.get("company_name"),
        "industry": kwargs.get("industry"),
        "employee_count": kwargs.get("employee_count"),
        **{k: v for k, v in kwargs.items() if k not in ("company_name", "industry", "employee_count")},
    }


# =============================================================================
# Clay Webhook Endpoint Tests
# =============================================================================


class TestClayWebhookEndpoint:
    """Tests for POST /api/webhooks/clay/enrichment."""

    @patch("app.api.routes.webhooks.settings")
    def test_valid_payload(self, mock_settings: MagicMock, client: TestClient) -> None:
        """Valid payload with phones is processed and stored."""
        mock_settings.clay_webhook_secret = ""
        mock_settings.environment = "development"

        payload = _clay_payload(
            phones=[{"number": "+14155551234", "type": "direct", "provider": "zoominfo"}],
            emails=[{"email": "john@acme.com", "type": "work"}],
            company_name="Acme Corp",
        )

        with patch("app.services.database.supabase_client.supabase_client") as mock_db:
            mock_db.store_clay_enrichment.return_value = {"id": "uuid-1"}
            response = client.post("/api/webhooks/clay/enrichment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["phones_received"] == 1
        assert data["emails_received"] == 1
        assert data["lead_id"] == "lead_123"

    @patch("app.api.routes.webhooks.settings")
    def test_invalid_signature(self, mock_settings: MagicMock, client: TestClient) -> None:
        """Invalid HMAC signature returns 401."""
        mock_settings.clay_webhook_secret = "real-secret"
        mock_settings.environment = "production"

        payload = _clay_payload()
        response = client.post(
            "/api/webhooks/clay/enrichment",
            json=payload,
            headers={"x-clay-signature": "bad-signature"},
        )
        assert response.status_code == 401

    @patch("app.api.routes.webhooks.settings")
    def test_missing_signature_production(self, mock_settings: MagicMock, client: TestClient) -> None:
        """Missing signature in production returns 401."""
        mock_settings.clay_webhook_secret = "real-secret"
        mock_settings.environment = "production"

        payload = _clay_payload()
        response = client.post("/api/webhooks/clay/enrichment", json=payload)
        assert response.status_code == 401

    @patch("app.api.routes.webhooks.settings")
    def test_empty_payload(self, mock_settings: MagicMock, client: TestClient) -> None:
        """Empty payload (no lead_id) returns 400."""
        mock_settings.clay_webhook_secret = ""
        mock_settings.environment = "development"

        response = client.post("/api/webhooks/clay/enrichment", json={})
        assert response.status_code == 400
        assert "lead_id" in response.json()["detail"].lower()

    @patch("app.api.routes.webhooks.settings")
    def test_missing_lead_id(self, mock_settings: MagicMock, client: TestClient) -> None:
        """Payload without lead_id returns 400."""
        mock_settings.clay_webhook_secret = ""
        mock_settings.environment = "development"

        response = client.post(
            "/api/webhooks/clay/enrichment",
            json={"phones": [{"number": "+1234", "type": "mobile"}]},
        )
        assert response.status_code == 400

    @patch("app.api.routes.webhooks.settings")
    def test_phones_extracted(self, mock_settings: MagicMock, client: TestClient) -> None:
        """Phones are parsed from payload and counted."""
        mock_settings.clay_webhook_secret = ""
        mock_settings.environment = "development"

        payload = _clay_payload(
            phones=[
                {"number": "+14155551111", "type": "direct"},
                {"number": "+14155552222", "type": "mobile"},
            ],
        )
        with patch("app.services.database.supabase_client.supabase_client"):
            response = client.post("/api/webhooks/clay/enrichment", json=payload)

        assert response.json()["phones_received"] == 2

    @patch("app.api.routes.webhooks.settings")
    def test_emails_extracted(self, mock_settings: MagicMock, client: TestClient) -> None:
        """Emails are parsed and counted."""
        mock_settings.clay_webhook_secret = ""
        mock_settings.environment = "development"

        payload = _clay_payload(
            emails=[
                {"email": "john@acme.com", "type": "work"},
                {"email": "john.doe@gmail.com", "type": "personal"},
            ],
        )
        with patch("app.services.database.supabase_client.supabase_client"):
            response = client.post("/api/webhooks/clay/enrichment", json=payload)

        assert response.json()["emails_received"] == 2

    @patch("app.api.routes.webhooks.settings")
    def test_company_data_extracted(self, mock_settings: MagicMock, client: TestClient) -> None:
        """Firmographic data is passed through to storage."""
        mock_settings.clay_webhook_secret = ""
        mock_settings.environment = "development"

        payload = _clay_payload(
            company_name="Acme Corp",
            industry="Technology",
            employee_count=500,
        )

        with patch("app.services.database.supabase_client.supabase_client") as mock_db:
            mock_db.store_clay_enrichment.return_value = {"id": "uuid-1"}
            response = client.post("/api/webhooks/clay/enrichment", json=payload)

        assert response.status_code == 200
        call_args = mock_db.store_clay_enrichment.call_args
        assert call_args.kwargs["data"]["company_name"] == "Acme Corp"
        assert call_args.kwargs["data"]["industry"] == "Technology"

    @patch("app.api.routes.webhooks.settings")
    def test_partial_data(self, mock_settings: MagicMock, client: TestClient) -> None:
        """Gracefully handles payload with only lead_id."""
        mock_settings.clay_webhook_secret = ""
        mock_settings.environment = "development"

        payload = {"lead_id": "lead_minimal"}
        with patch("app.services.database.supabase_client.supabase_client"):
            response = client.post("/api/webhooks/clay/enrichment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["phones_received"] == 0
        assert data["emails_received"] == 0

    @patch("app.api.routes.webhooks.settings")
    def test_db_failure_still_returns_200(self, mock_settings: MagicMock, client: TestClient) -> None:
        """DB storage failure doesn't block the webhook response."""
        mock_settings.clay_webhook_secret = ""
        mock_settings.environment = "development"

        payload = _clay_payload(phones=[{"number": "+1234", "type": "mobile"}])
        with patch("app.services.database.supabase_client.supabase_client") as mock_db:
            mock_db.store_clay_enrichment.side_effect = Exception("DB down")
            response = client.post("/api/webhooks/clay/enrichment", json=payload)

        # Still 200 — don't make Clay retry on our failures
        assert response.status_code == 200
