"""Tests for Batch Processing API endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestBatchProcessingEndpoint:
    """Tests for batch processing API route."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from app.main import app

        return TestClient(app)

    @pytest.fixture
    def sample_leads(self) -> list[dict]:
        """Sample lead data for batch processing."""
        return [
            {
                "hubspot_id": "hs-lead-1",
                "email": "sarah@university.edu",
                "first_name": "Sarah",
                "last_name": "Johnson",
                "company": "State University",
                "title": "AV Director",
            },
            {
                "hubspot_id": "hs-lead-2",
                "email": "mike@techcorp.com",
                "first_name": "Mike",
                "last_name": "Smith",
                "company": "TechCorp",
                "title": "IT Director",
            },
        ]

    def test_batch_process_returns_results(
        self, client: TestClient, sample_leads: list[dict]
    ):
        """Test POST /api/batch/process returns results for all leads."""
        mock_research = {
            "research_brief": {"company_overview": "Test"},
            "talking_points": ["Point 1"],
            "risk_factors": [],
        }
        mock_script = {
            "personalized_script": "Hi, this is...",
            "talking_points": [],
            "objection_responses": [],
        }
        mock_email = {
            "subject_line": "Quick question",
            "email_body": "Hi there...",
            "follow_up_note": None,
        }

        with (
            patch(
                "app.api.routes.batch.lead_research_agent.run",
                new_callable=AsyncMock,
            ) as mock_research_agent,
            patch(
                "app.api.routes.batch.script_selection_agent.run",
                new_callable=AsyncMock,
            ) as mock_script_agent,
            patch(
                "app.api.routes.batch.email_personalization_agent.run",
                new_callable=AsyncMock,
            ) as mock_email_agent,
        ):
            mock_research_agent.return_value = mock_research
            mock_script_agent.return_value = mock_script
            mock_email_agent.return_value = mock_email

            response = client.post(
                "/api/batch/process",
                json={
                    "leads": sample_leads,
                    "email_type": "pattern_interrupt",
                    "sequence_step": 1,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2

    def test_batch_process_handles_partial_failure(
        self, client: TestClient, sample_leads: list[dict]
    ):
        """Test batch process continues when one lead fails."""
        mock_research = {
            "research_brief": {"company_overview": "Test"},
            "talking_points": [],
            "risk_factors": [],
        }
        mock_script = {
            "personalized_script": "Script",
            "talking_points": [],
            "objection_responses": [],
        }
        mock_email = {
            "subject_line": "Subject",
            "email_body": "Body",
            "follow_up_note": None,
        }

        with (
            patch(
                "app.api.routes.batch.lead_research_agent.run",
                new_callable=AsyncMock,
            ) as mock_research_agent,
            patch(
                "app.api.routes.batch.script_selection_agent.run",
                new_callable=AsyncMock,
            ) as mock_script_agent,
            patch(
                "app.api.routes.batch.email_personalization_agent.run",
                new_callable=AsyncMock,
            ) as mock_email_agent,
        ):
            # First lead fails research, second succeeds
            mock_research_agent.side_effect = [
                Exception("API Error"),
                mock_research,
            ]
            mock_script_agent.return_value = mock_script
            mock_email_agent.return_value = mock_email

            response = client.post(
                "/api/batch/process",
                json={"leads": sample_leads},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        # First should have error, second should succeed
        assert data["results"][0].get("error") is not None
        assert data["results"][1].get("generated_email") is not None

    def test_batch_process_validates_leads(self, client: TestClient):
        """Test batch process validates lead data."""
        response = client.post(
            "/api/batch/process",
            json={"leads": [{"email": "invalid"}]},  # Missing hubspot_id
        )

        assert response.status_code == 422

    def test_batch_process_respects_concurrency_limit(
        self, client: TestClient, sample_leads: list[dict]
    ):
        """Test batch process respects concurrency limit."""
        mock_research = {
            "research_brief": {},
            "talking_points": [],
            "risk_factors": [],
        }
        mock_script = {
            "personalized_script": "",
            "talking_points": [],
            "objection_responses": [],
        }
        mock_email = {
            "subject_line": "",
            "email_body": "",
            "follow_up_note": None,
        }

        with (
            patch(
                "app.api.routes.batch.lead_research_agent.run",
                new_callable=AsyncMock,
            ) as mock_research_agent,
            patch(
                "app.api.routes.batch.script_selection_agent.run",
                new_callable=AsyncMock,
            ) as mock_script_agent,
            patch(
                "app.api.routes.batch.email_personalization_agent.run",
                new_callable=AsyncMock,
            ) as mock_email_agent,
        ):
            mock_research_agent.return_value = mock_research
            mock_script_agent.return_value = mock_script
            mock_email_agent.return_value = mock_email

            response = client.post(
                "/api/batch/process",
                json={
                    "leads": sample_leads,
                    "concurrency": 1,
                },
            )

        assert response.status_code == 200
        # All leads should still be processed
        assert len(response.json()["results"]) == 2

    def test_batch_process_returns_summary(
        self, client: TestClient, sample_leads: list[dict]
    ):
        """Test batch process returns processing summary."""
        mock_research = {
            "research_brief": {},
            "talking_points": [],
            "risk_factors": [],
        }
        mock_script = {
            "personalized_script": "",
            "talking_points": [],
            "objection_responses": [],
        }
        mock_email = {
            "subject_line": "Test",
            "email_body": "Body",
            "follow_up_note": None,
        }

        with (
            patch(
                "app.api.routes.batch.lead_research_agent.run",
                new_callable=AsyncMock,
            ) as mock_research_agent,
            patch(
                "app.api.routes.batch.script_selection_agent.run",
                new_callable=AsyncMock,
            ) as mock_script_agent,
            patch(
                "app.api.routes.batch.email_personalization_agent.run",
                new_callable=AsyncMock,
            ) as mock_email_agent,
        ):
            mock_research_agent.return_value = mock_research
            mock_script_agent.return_value = mock_script
            mock_email_agent.return_value = mock_email

            response = client.post(
                "/api/batch/process",
                json={"leads": sample_leads},
            )

        data = response.json()
        assert "summary" in data
        assert "total" in data["summary"]
        assert "successful" in data["summary"]
        assert "failed" in data["summary"]
