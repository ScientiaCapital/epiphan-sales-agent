"""Tests for Agent API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestAgentAPIEndpoints:
    """Tests for agent API routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from app.main import app

        return TestClient(app)

    @pytest.fixture
    def sample_lead_payload(self) -> dict:
        """Sample lead data for API requests."""
        return {
            "hubspot_id": "hs-lead-123",
            "email": "sarah.johnson@stateuniversity.edu",
            "first_name": "Sarah",
            "last_name": "Johnson",
            "company": "State University",
            "title": "AV Director",
        }

    def test_research_endpoint_returns_brief(
        self, client: TestClient, sample_lead_payload: dict
    ):
        """Test POST /api/agents/research returns research brief."""
        mock_result = {
            "research_brief": {
                "company_overview": "State University is a research institution.",
                "recent_news": [],
                "talking_points": ["Higher education focus"],
                "risk_factors": [],
                "linkedin_summary": None,
            },
            "talking_points": ["Higher education focus"],
            "risk_factors": [],
        }

        with patch(
            "app.api.routes.agents.lead_research_agent.run",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = mock_result

            response = client.post(
                "/api/agents/research",
                json={"lead": sample_lead_payload, "research_depth": "quick"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "research_brief" in data
        assert "talking_points" in data

    def test_scripts_endpoint_returns_personalized_script(
        self, client: TestClient, sample_lead_payload: dict
    ):
        """Test POST /api/agents/scripts returns personalized script."""
        mock_result = {
            "personalized_script": "Hi Sarah, I noticed State University...",
            "talking_points": ["Lecture capture", "Hybrid learning"],
            "objection_responses": [],
        }

        with patch(
            "app.api.routes.agents.script_selection_agent.run",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = mock_result

            response = client.post(
                "/api/agents/scripts",
                json={
                    "lead": sample_lead_payload,
                    "persona_match": "av_director",
                    "trigger": "demo_request",
                    "call_type": "warm",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "personalized_script" in data

    def test_competitors_endpoint_returns_response(
        self, client: TestClient
    ):
        """Test POST /api/agents/competitors returns competitor response."""
        mock_result = {
            "response": "Pearl's all-in-one solution provides...",
            "proof_points": ["State University case study"],
            "follow_up_question": "What's most important to you?",
        }

        with patch(
            "app.api.routes.agents.competitor_intel_agent.run",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = mock_result

            response = client.post(
                "/api/agents/competitors",
                json={
                    "competitor_name": "vaddio",
                    "context": "Prospect mentioned Vaddio",
                    "query_type": "comparison",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_emails_endpoint_returns_personalized_email(
        self, client: TestClient, sample_lead_payload: dict
    ):
        """Test POST /api/agents/emails returns personalized email."""
        mock_result = {
            "subject_line": "Quick question about State University",
            "email_body": "Hi Sarah, I noticed...",
            "follow_up_note": None,
        }

        with patch(
            "app.api.routes.agents.email_personalization_agent.run",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = mock_result

            response = client.post(
                "/api/agents/emails",
                json={
                    "lead": sample_lead_payload,
                    "email_type": "pattern_interrupt",
                    "sequence_step": 1,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "subject_line" in data
        assert "email_body" in data

    def test_research_endpoint_validates_lead(self, client: TestClient):
        """Test research endpoint validates lead data."""
        response = client.post(
            "/api/agents/research",
            json={"lead": {"email": "invalid"}},  # Missing required fields
        )

        assert response.status_code == 422  # Validation error

    def test_competitors_endpoint_validates_competitor(self, client: TestClient):
        """Test competitors endpoint validates input."""
        response = client.post(
            "/api/agents/competitors",
            json={},  # Missing required fields
        )

        assert response.status_code == 422

    def test_emails_endpoint_validates_sequence_step(
        self, client: TestClient, sample_lead_payload: dict
    ):
        """Test emails endpoint validates sequence_step range."""
        mock_result = {
            "subject_line": "Test",
            "email_body": "Body",
            "follow_up_note": None,
        }

        with patch(
            "app.api.routes.agents.email_personalization_agent.run",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = mock_result

            # Valid step
            response = client.post(
                "/api/agents/emails",
                json={
                    "lead": sample_lead_payload,
                    "email_type": "pattern_interrupt",
                    "sequence_step": 1,
                },
            )

            assert response.status_code == 200
