"""Tests for Apollo webhook endpoint.

PHONES ARE GOLD! These tests verify webhook phone delivery works correctly.
More phones = More dials = More conversations = More deals.
"""

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app

    return TestClient(app)


class TestApolloPhoneWebhook:
    """Tests for /api/webhooks/apollo/phone-reveal endpoint."""

    def test_webhook_accepts_valid_payload(self, client: TestClient):
        """Test webhook accepts valid phone payload. PHONES ARE GOLD!"""
        payload = {
            "person_id": "apollo_123",
            "email": "sarah@university.edu",
            "phone_numbers": [
                {"sanitized_number": "+14155551234", "type": "work_direct"},
                {"sanitized_number": "+14155559999", "type": "mobile"},
            ],
        }

        response = client.post("/api/webhooks/apollo/phone-reveal", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["phones_received"] == 2

    def test_webhook_handles_empty_phones(self, client: TestClient):
        """Test webhook handles payload with no phones gracefully."""
        payload = {"email": "nophones@example.com", "phone_numbers": []}

        response = client.post("/api/webhooks/apollo/phone-reveal", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["phones_received"] == 0

    def test_webhook_ignores_missing_email(self, client: TestClient):
        """Test webhook ignores payload without email identifier."""
        payload = {
            "person_id": "123",
            "phone_numbers": [{"sanitized_number": "+1555", "type": "mobile"}],
        }

        response = client.post("/api/webhooks/apollo/phone-reveal", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    def test_webhook_handles_malformed_payload(self, client: TestClient):
        """Test webhook rejects malformed JSON."""
        response = client.post(
            "/api/webhooks/apollo/phone-reveal",
            content=b"not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400

    def test_webhook_processes_single_phone(self, client: TestClient):
        """Test webhook processes single phone correctly."""
        payload = {
            "email": "single@example.com",
            "phone_numbers": [{"sanitized_number": "+1-800-EPIPHAN", "type": "mobile"}],
        }

        response = client.post("/api/webhooks/apollo/phone-reveal", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["phones_received"] == 1

    def test_webhook_processes_all_phone_types(self, client: TestClient):
        """Test webhook processes all phone types. PHONES ARE GOLD!"""
        payload = {
            "email": "allphones@example.com",
            "phone_numbers": [
                {"sanitized_number": "+1-DIRECT", "type": "work_direct"},
                {"sanitized_number": "+1-MOBILE", "type": "mobile"},
                {"sanitized_number": "+1-WORK", "type": "work"},
                {"sanitized_number": "+1-HQ", "type": "work_hq"},
            ],
        }

        response = client.post("/api/webhooks/apollo/phone-reveal", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["phones_received"] == 4


class TestSignatureVerification:
    """Tests for HMAC-SHA256 signature verification."""

    def test_valid_signature_accepted(self, client: TestClient):
        """Test webhook accepts valid HMAC-SHA256 signature."""
        secret = "test-webhook-secret"
        payload = {"email": "test@example.com", "phone_numbers": []}
        body = json.dumps(payload).encode()

        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        with patch("app.api.routes.webhooks.settings") as mock_settings:
            mock_settings.apollo_webhook_secret = secret
            mock_settings.environment = "production"

            response = client.post(
                "/api/webhooks/apollo/phone-reveal",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "x-apollo-signature": f"sha256={signature}",
                },
            )

            assert response.status_code == 200

    def test_invalid_signature_rejected_in_production(self, client: TestClient):
        """Test webhook rejects invalid signature in production."""
        with patch("app.api.routes.webhooks.settings") as mock_settings:
            mock_settings.apollo_webhook_secret = "real-secret"
            mock_settings.environment = "production"

            payload = {"email": "test@example.com", "phone_numbers": []}

            response = client.post(
                "/api/webhooks/apollo/phone-reveal",
                json=payload,
                headers={"x-apollo-signature": "sha256=invalid-signature"},
            )

            assert response.status_code == 401
            assert "Invalid webhook signature" in response.json()["detail"]

    def test_missing_signature_rejected_in_production(self, client: TestClient):
        """Test webhook rejects missing signature in production."""
        with patch("app.api.routes.webhooks.settings") as mock_settings:
            mock_settings.apollo_webhook_secret = "real-secret"
            mock_settings.environment = "production"

            payload = {"email": "test@example.com", "phone_numbers": []}

            response = client.post("/api/webhooks/apollo/phone-reveal", json=payload)

            assert response.status_code == 401

    def test_no_secret_allows_in_development(self, client: TestClient):
        """Test webhook allows requests when no secret configured in development."""
        with patch("app.api.routes.webhooks.settings") as mock_settings:
            mock_settings.apollo_webhook_secret = ""
            mock_settings.environment = "development"

            payload = {"email": "test@example.com", "phone_numbers": []}

            response = client.post("/api/webhooks/apollo/phone-reveal", json=payload)

            # Should succeed without signature in dev mode
            assert response.status_code == 200

    def test_signature_without_prefix_accepted(self, client: TestClient):
        """Test webhook accepts signature without sha256= prefix."""
        secret = "test-secret"
        payload = {"email": "test@example.com", "phone_numbers": []}
        body = json.dumps(payload).encode()

        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        with patch("app.api.routes.webhooks.settings") as mock_settings:
            mock_settings.apollo_webhook_secret = secret
            mock_settings.environment = "production"

            response = client.post(
                "/api/webhooks/apollo/phone-reveal",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "x-apollo-signature": signature,  # No prefix
                },
            )

            assert response.status_code == 200


class TestPhoneExtraction:
    """Tests for phone type extraction logic."""

    def test_extract_direct_phone(self):
        """Test direct phone extraction. Direct dial is GOLD!"""
        from app.api.routes.webhooks import extract_phones_from_payload

        phones = [
            {"sanitized_number": "+1-DIRECT", "type": "work_direct"},
            {"sanitized_number": "+1-MOBILE", "type": "mobile"},
        ]

        result = extract_phones_from_payload(phones)

        assert result["direct_phone"] == "+1-DIRECT"
        assert result["mobile_phone"] == "+1-MOBILE"

    def test_extract_work_phone_not_hq(self):
        """Test work phone extraction excludes HQ phones."""
        from app.api.routes.webhooks import extract_phones_from_payload

        phones = [
            {"sanitized_number": "+1-WORK", "type": "work"},
            {"sanitized_number": "+1-HQ", "type": "work_hq"},
        ]

        result = extract_phones_from_payload(phones)

        assert result["work_phone"] == "+1-WORK"
        # HQ should not be extracted as work phone
        assert result["direct_phone"] is None

    def test_extract_uses_number_field_fallback(self):
        """Test fallback to 'number' if 'sanitized_number' missing."""
        from app.api.routes.webhooks import extract_phones_from_payload

        phones = [
            {"number": "+1-FALLBACK", "type": "mobile"},
        ]

        result = extract_phones_from_payload(phones)

        assert result["mobile_phone"] == "+1-FALLBACK"

    def test_extract_skips_empty_numbers(self):
        """Test extraction skips phones without numbers."""
        from app.api.routes.webhooks import extract_phones_from_payload

        phones = [
            {"type": "mobile"},  # No number field
            {"sanitized_number": "", "type": "work"},  # Empty string
            {"sanitized_number": "+1-VALID", "type": "work_direct"},
        ]

        result = extract_phones_from_payload(phones)

        assert result["direct_phone"] == "+1-VALID"
        assert result["mobile_phone"] is None
        assert result["work_phone"] is None

    def test_extract_case_insensitive_type(self):
        """Test phone type matching is case insensitive."""
        from app.api.routes.webhooks import extract_phones_from_payload

        phones = [
            {"sanitized_number": "+1-DIRECT", "type": "WORK_DIRECT"},
            {"sanitized_number": "+1-MOBILE", "type": "MOBILE"},
        ]

        result = extract_phones_from_payload(phones)

        assert result["direct_phone"] == "+1-DIRECT"
        assert result["mobile_phone"] == "+1-MOBILE"

    def test_extract_first_of_each_type(self):
        """Test extraction takes first occurrence of each type."""
        from app.api.routes.webhooks import extract_phones_from_payload

        phones = [
            {"sanitized_number": "+1-MOBILE-1", "type": "mobile"},
            {"sanitized_number": "+1-MOBILE-2", "type": "mobile"},
        ]

        result = extract_phones_from_payload(phones)

        assert result["mobile_phone"] == "+1-MOBILE-1"

    def test_extract_empty_list(self):
        """Test extraction handles empty phone list."""
        from app.api.routes.webhooks import extract_phones_from_payload

        result = extract_phones_from_payload([])

        assert result["direct_phone"] is None
        assert result["mobile_phone"] is None
        assert result["work_phone"] is None

    def test_extract_handles_missing_type(self):
        """Test extraction handles phones without type field."""
        from app.api.routes.webhooks import extract_phones_from_payload

        phones = [
            {"sanitized_number": "+1-UNKNOWN"},  # No type field
        ]

        result = extract_phones_from_payload(phones)

        # Should not extract unknown type
        assert result["direct_phone"] is None
        assert result["mobile_phone"] is None
        assert result["work_phone"] is None


class TestUpdateLeadPhones:
    """Tests for lead phone update function."""

    @pytest.mark.asyncio
    async def test_update_lead_phones_logs_correctly(self):
        """Test update_lead_phones logs phone data."""
        from app.api.routes.webhooks import update_lead_phones

        phones = [
            {"sanitized_number": "+1-DIRECT", "type": "work_direct"},
            {"sanitized_number": "+1-MOBILE", "type": "mobile"},
        ]

        with patch("app.api.routes.webhooks.logger") as mock_logger:
            result = await update_lead_phones("test@example.com", phones)

            assert result is True
            # Verify logging was called
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_update_lead_phones_returns_true(self):
        """Test update_lead_phones returns success."""
        from app.api.routes.webhooks import update_lead_phones

        result = await update_lead_phones(
            "test@example.com",
            [{"sanitized_number": "+1-TEST", "type": "mobile"}],
        )

        assert result is True
