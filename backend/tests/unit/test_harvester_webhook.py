"""Tests for Lead Harvester webhook endpoint.

Real-time sync from Harvester eliminates manual CSV exports.
PHONES ARE GOLD! Auto-qualify leads as they come in.
"""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_monitoring_state():
    """Reset monitoring state before each test."""
    from app.api.routes.monitoring import (
        _active_batches,
        _completed_batches,
    )

    _active_batches.clear()
    _completed_batches.clear()

    yield

    _active_batches.clear()
    _completed_batches.clear()


class TestHarvesterWebhook:
    """Tests for POST /api/webhooks/harvester/lead-push endpoint."""

    def test_webhook_accepts_valid_payload(self, client: TestClient):
        """Test webhook accepts valid lead push payload."""
        payload = {
            "source": "harvester",
            "timestamp": "2025-01-29T12:00:00Z",
            "leads": [
                {
                    "external_id": "harv_001",
                    "company_name": "Stanford University",
                    "contact_title": "AV Director",
                    "contact_email": "av@stanford.edu",
                }
            ],
        }

        with patch(
            "app.services.enrichment.pipeline.queue_harvester_batch",
            new_callable=AsyncMock,
        ) as mock_queue:
            response = client.post("/api/webhooks/harvester/lead-push", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert data["leads_received"] == 1
            assert "batch_id" in data
            assert data["batch_id"].startswith("harv_")

            # Verify queue was called
            mock_queue.assert_called_once()

    def test_webhook_handles_multiple_leads(self, client: TestClient):
        """Test webhook handles batch of multiple leads."""
        payload = {
            "source": "harvester",
            "leads": [
                {
                    "external_id": f"harv_{i:03d}",
                    "company_name": f"University {i}",
                    "contact_email": f"contact{i}@example.edu",
                }
                for i in range(5)
            ],
        }

        with patch(
            "app.services.enrichment.pipeline.queue_harvester_batch",
            new_callable=AsyncMock,
        ):
            response = client.post("/api/webhooks/harvester/lead-push", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["leads_received"] == 5

    def test_webhook_handles_empty_leads(self, client: TestClient):
        """Test webhook handles empty leads list gracefully."""
        payload = {"source": "harvester", "leads": []}

        response = client.post("/api/webhooks/harvester/lead-push", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["leads_received"] == 0

    def test_webhook_handles_malformed_payload(self, client: TestClient):
        """Test webhook rejects malformed JSON."""
        response = client.post(
            "/api/webhooks/harvester/lead-push",
            content=b"not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400

    def test_webhook_requires_leads_array(self, client: TestClient):
        """Test webhook requires leads field."""
        payload = {"source": "harvester"}

        response = client.post("/api/webhooks/harvester/lead-push", json=payload)

        assert response.status_code == 400  # Pydantic validation error caught as 400

    def test_webhook_registers_batch_for_monitoring(self, client: TestClient):
        """Test webhook registers batch with monitoring system."""
        from app.api.routes.monitoring import get_batch

        payload = {
            "source": "harvester",
            "leads": [{"external_id": "harv_001", "company_name": "Test Corp"}],
        }

        with patch(
            "app.services.enrichment.pipeline.queue_harvester_batch",
            new_callable=AsyncMock,
        ):
            response = client.post("/api/webhooks/harvester/lead-push", json=payload)

            batch_id = response.json()["batch_id"]
            batch = get_batch(batch_id)

            assert batch is not None
            assert batch.total_leads == 1

    def test_webhook_handles_queue_failure_gracefully(self, client: TestClient):
        """Test webhook returns accepted even if queue fails."""
        payload = {
            "source": "harvester",
            "leads": [{"external_id": "harv_001", "company_name": "Test Corp"}],
        }

        with patch(
            "app.services.enrichment.pipeline.queue_harvester_batch",
            new_callable=AsyncMock,
            side_effect=Exception("Queue connection failed"),
        ):
            response = client.post("/api/webhooks/harvester/lead-push", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert "queue failed" in data["message"].lower()


class TestHarvesterSignatureVerification:
    """Tests for HMAC-SHA256 signature verification for Harvester webhook."""

    def test_valid_signature_accepted(self, client: TestClient):
        """Test webhook accepts valid HMAC-SHA256 signature."""
        secret = "harvester-test-secret"
        payload = {
            "source": "harvester",
            "leads": [{"external_id": "harv_001", "company_name": "Test Corp"}],
        }
        body = json.dumps(payload).encode()

        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        with patch("app.api.routes.webhooks.settings") as mock_settings:
            mock_settings.harvester_webhook_secret = secret
            mock_settings.environment = "production"

            with patch(
                "app.services.enrichment.pipeline.queue_harvester_batch",
                new_callable=AsyncMock,
            ):
                response = client.post(
                    "/api/webhooks/harvester/lead-push",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "x-harvester-signature": f"sha256={signature}",
                    },
                )

                assert response.status_code == 200

    def test_invalid_signature_rejected_in_production(self, client: TestClient):
        """Test webhook rejects invalid signature in production."""
        with patch("app.api.routes.webhooks.settings") as mock_settings:
            mock_settings.harvester_webhook_secret = "real-secret"
            mock_settings.environment = "production"

            payload = {
                "source": "harvester",
                "leads": [{"external_id": "harv_001", "company_name": "Test Corp"}],
            }

            response = client.post(
                "/api/webhooks/harvester/lead-push",
                json=payload,
                headers={"x-harvester-signature": "sha256=invalid"},
            )

            assert response.status_code == 401
            assert "Invalid webhook signature" in response.json()["detail"]

    def test_missing_signature_rejected_in_production(self, client: TestClient):
        """Test webhook rejects missing signature in production."""
        with patch("app.api.routes.webhooks.settings") as mock_settings:
            mock_settings.harvester_webhook_secret = "real-secret"
            mock_settings.environment = "production"

            payload = {
                "source": "harvester",
                "leads": [{"external_id": "harv_001", "company_name": "Test Corp"}],
            }

            response = client.post("/api/webhooks/harvester/lead-push", json=payload)

            assert response.status_code == 401

    def test_no_secret_allows_in_development(self, client: TestClient):
        """Test webhook allows requests when no secret configured in dev."""
        with patch("app.api.routes.webhooks.settings") as mock_settings:
            mock_settings.harvester_webhook_secret = ""
            mock_settings.environment = "development"

            payload = {
                "source": "harvester",
                "leads": [{"external_id": "harv_001", "company_name": "Test Corp"}],
            }

            with patch(
                "app.services.enrichment.pipeline.queue_harvester_batch",
                new_callable=AsyncMock,
            ):
                response = client.post("/api/webhooks/harvester/lead-push", json=payload)

                assert response.status_code == 200


class TestHarvesterLeadPayload:
    """Tests for Harvester lead payload validation."""

    def test_minimal_lead_accepted(self, client: TestClient):
        """Test minimal required fields are accepted."""
        payload = {
            "source": "harvester",
            "leads": [{"external_id": "min_001", "company_name": "Minimal Corp"}],
        }

        with patch(
            "app.services.enrichment.pipeline.queue_harvester_batch",
            new_callable=AsyncMock,
        ):
            response = client.post("/api/webhooks/harvester/lead-push", json=payload)

            assert response.status_code == 200

    def test_full_lead_accepted(self, client: TestClient):
        """Test full lead with all fields is accepted. PHONES ARE GOLD!"""
        payload = {
            "source": "harvester",
            "leads": [
                {
                    "external_id": "full_001",
                    "source": "ipeds_higher_ed",
                    "company_name": "Stanford University",
                    "industry": "Higher Education",
                    "employees": 15000,
                    "city": "Stanford",
                    "state": "CA",
                    "zip": "94305",
                    "website": "https://stanford.edu",
                    "harvester_score": 85.0,
                    "harvester_tier": "A",
                    "contact_name": "Sarah Johnson",
                    "contact_title": "Director of AV Services",
                    "contact_email": "sarah@stanford.edu",
                    "direct_phone": "+1-650-555-1234",
                    "work_phone": "+1-650-555-5678",
                    "mobile_phone": "+1-650-555-9999",
                    "company_phone": "+1-650-555-0000",
                    "tech_stack": ["Zoom", "Panopto", "Canvas"],
                    "raw_data": {"ipeds_id": "123456"},
                }
            ],
        }

        with patch(
            "app.services.enrichment.pipeline.queue_harvester_batch",
            new_callable=AsyncMock,
        ) as mock_queue:
            response = client.post("/api/webhooks/harvester/lead-push", json=payload)

            assert response.status_code == 200

            # Verify all fields passed to queue
            call_args = mock_queue.call_args
            leads = call_args.kwargs["leads"]
            assert leads[0]["contact_title"] == "Director of AV Services"
            assert leads[0]["direct_phone"] == "+1-650-555-1234"

    def test_missing_external_id_rejected(self, client: TestClient):
        """Test lead without external_id is rejected."""
        payload = {
            "source": "harvester",
            "leads": [{"company_name": "No ID Corp"}],
        }

        response = client.post("/api/webhooks/harvester/lead-push", json=payload)

        assert response.status_code == 400  # Pydantic validation error caught as 400

    def test_missing_company_name_rejected(self, client: TestClient):
        """Test lead without company_name is rejected."""
        payload = {
            "source": "harvester",
            "leads": [{"external_id": "no_name_001"}],
        }

        response = client.post("/api/webhooks/harvester/lead-push", json=payload)

        assert response.status_code == 400  # Pydantic validation error caught as 400
