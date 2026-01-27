"""Tests for Leads API endpoints.

TDD tests for lead management API routes.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("app.api.routes.leads.supabase_client") as mock:
        yield mock


@pytest.fixture
def mock_hubspot_sync():
    """Mock HubSpot sync service."""
    with patch("app.api.routes.leads.hubspot_sync_service") as mock:
        yield mock


@pytest.fixture
def mock_lead_scorer():
    """Mock lead scorer."""
    with patch("app.api.routes.leads.lead_scorer") as mock:
        yield mock


@pytest.fixture
def sample_leads():
    """Sample lead data."""
    return [
        {
            "id": "uuid-1",
            "hubspot_id": "12345",
            "email": "av@university.edu",
            "first_name": "John",
            "last_name": "Smith",
            "company": "State University",
            "title": "AV Director",
            "persona_match": "av_director",
            "persona_confidence": 0.95,
            "vertical": "higher_ed",
            "persona_score": 23,
            "vertical_score": 25,
            "company_score": 20,
            "engagement_score": 15,
            "total_score": 83,
            "tier": "warm",
        },
        {
            "id": "uuid-2",
            "hubspot_id": "12346",
            "email": "ld@corp.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "TechCorp Inc",
            "title": "L&D Director",
            "persona_match": "ld_director",
            "persona_confidence": 0.90,
            "vertical": "corporate",
            "persona_score": 22,
            "vertical_score": 20,
            "company_score": 18,
            "engagement_score": 10,
            "total_score": 70,
            "tier": "warm",
        },
    ]


class TestLeadsSyncEndpoint:
    """Tests for POST /api/leads/sync endpoint."""

    def test_sync_success(self, client, mock_hubspot_sync):
        """Test successful sync trigger."""
        mock_hubspot_sync.full_sync = AsyncMock(
            return_value=MagicMock(
                success=True,
                contacts_fetched=100,
                contacts_synced=95,
                contacts_skipped=5,
                errors=[],
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                duration_seconds=5.2,
            )
        )

        response = client.post("/api/leads/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["contacts_fetched"] == 100
        assert data["contacts_synced"] == 95

    def test_sync_with_errors(self, client, mock_hubspot_sync):
        """Test sync with errors returns partial success."""
        mock_hubspot_sync.full_sync = AsyncMock(
            return_value=MagicMock(
                success=False,
                contacts_fetched=50,
                contacts_synced=45,
                contacts_skipped=5,
                errors=["HubSpot API rate limited"],
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                duration_seconds=3.1,
            )
        )

        response = client.post("/api/leads/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0

    def test_incremental_sync(self, client, mock_hubspot_sync):
        """Test incremental sync with since parameter."""
        mock_hubspot_sync.incremental_sync = AsyncMock(
            return_value=MagicMock(
                success=True,
                contacts_fetched=10,
                contacts_synced=10,
                contacts_skipped=0,
                errors=[],
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                duration_seconds=0.5,
            )
        )

        response = client.post(
            "/api/leads/sync",
            json={"since": "2024-01-20T00:00:00Z"},
        )

        assert response.status_code == 200
        mock_hubspot_sync.incremental_sync.assert_called_once()


class TestLeadsScoreEndpoint:
    """Tests for POST /api/leads/score endpoint."""

    def test_score_unscored_leads(self, client, mock_supabase, mock_lead_scorer):
        """Test scoring all unscored leads."""
        from app.data.lead_schemas import LeadTier

        # Mock unscored leads - include all required fields
        mock_supabase.get_unscored_leads = MagicMock(
            return_value=[
                {
                    "id": "uuid-1",
                    "hubspot_id": "123",
                    "email": "test@test.com",
                    "title": "Director",
                    "company": "Test Corp",
                },
                {
                    "id": "uuid-2",
                    "hubspot_id": "456",
                    "email": "test2@test.com",
                    "title": "Manager",
                    "company": "Test Inc",
                },
            ]
        )

        # Mock scorer - use actual LeadTier enum
        mock_lead_scorer.score_lead = MagicMock(
            return_value=MagicMock(
                persona_score=20,
                vertical_score=15,
                company_score=10,
                engagement_score=5,
                total_score=50,
                tier=LeadTier.NURTURE,
                persona_match="av_director",
                persona_confidence=0.8,
                vertical="higher_ed",
            )
        )

        # Mock update
        mock_supabase.update_lead_scores = MagicMock(return_value={})

        response = client.post("/api/leads/score")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["leads_scored"] == 2

    def test_score_with_limit(self, client, mock_supabase, mock_lead_scorer):  # noqa: ARG002
        """Test scoring with limit parameter."""
        mock_supabase.get_unscored_leads = MagicMock(return_value=[])

        response = client.post("/api/leads/score", json={"limit": 50})

        assert response.status_code == 200
        mock_supabase.get_unscored_leads.assert_called_once_with(limit=50)

    def test_score_no_unscored_leads(self, client, mock_supabase):
        """Test scoring when no unscored leads exist."""
        mock_supabase.get_unscored_leads = MagicMock(return_value=[])

        response = client.post("/api/leads/score")

        assert response.status_code == 200
        data = response.json()
        assert data["leads_scored"] == 0


class TestLeadsPrioritizedEndpoint:
    """Tests for GET /api/leads/prioritized endpoint."""

    def test_get_prioritized_leads(self, client, mock_supabase, sample_leads):
        """Test getting prioritized leads."""
        mock_supabase.get_prioritized_leads = MagicMock(return_value=sample_leads)
        mock_supabase.get_total_lead_count = MagicMock(return_value=1000)
        mock_supabase.get_lead_count_by_tier = MagicMock(
            return_value={"hot": 50, "warm": 200, "nurture": 400, "cold": 350}
        )

        response = client.get("/api/leads/prioritized")

        assert response.status_code == 200
        data = response.json()
        assert len(data["leads"]) == 2
        assert data["total_count"] == 1000
        assert "tier_counts" in data

    def test_get_prioritized_leads_filter_by_tier(self, client, mock_supabase, sample_leads):
        """Test filtering by tier."""
        mock_supabase.get_prioritized_leads = MagicMock(return_value=sample_leads)
        mock_supabase.get_total_lead_count = MagicMock(return_value=200)
        mock_supabase.get_lead_count_by_tier = MagicMock(
            return_value={"hot": 50, "warm": 200, "nurture": 400, "cold": 350}
        )

        response = client.get("/api/leads/prioritized?tier=warm")

        assert response.status_code == 200
        mock_supabase.get_prioritized_leads.assert_called_once()
        call_kwargs = mock_supabase.get_prioritized_leads.call_args[1]
        assert call_kwargs["tier"] == "warm"

    def test_get_prioritized_leads_filter_by_persona(self, client, mock_supabase, sample_leads):
        """Test filtering by persona."""
        mock_supabase.get_prioritized_leads = MagicMock(return_value=sample_leads[:1])
        mock_supabase.get_total_lead_count = MagicMock(return_value=100)
        mock_supabase.get_lead_count_by_tier = MagicMock(
            return_value={"hot": 50, "warm": 200, "nurture": 400, "cold": 350}
        )

        response = client.get("/api/leads/prioritized?persona=av_director")

        assert response.status_code == 200
        call_kwargs = mock_supabase.get_prioritized_leads.call_args[1]
        assert call_kwargs["persona"] == "av_director"

    def test_get_prioritized_leads_pagination(self, client, mock_supabase, sample_leads):
        """Test pagination parameters."""
        mock_supabase.get_prioritized_leads = MagicMock(return_value=sample_leads)
        mock_supabase.get_total_lead_count = MagicMock(return_value=1000)
        mock_supabase.get_lead_count_by_tier = MagicMock(
            return_value={"hot": 50, "warm": 200, "nurture": 400, "cold": 350}
        )

        response = client.get("/api/leads/prioritized?limit=10&offset=20")

        assert response.status_code == 200
        call_kwargs = mock_supabase.get_prioritized_leads.call_args[1]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 20


class TestLeadByIdEndpoint:
    """Tests for GET /api/leads/{id} endpoint."""

    def test_get_lead_by_id(self, client, mock_supabase, sample_leads):
        """Test getting single lead by ID."""
        mock_supabase.get_lead_by_id = MagicMock(return_value=sample_leads[0])

        response = client.get("/api/leads/uuid-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "uuid-1"
        assert data["email"] == "av@university.edu"
        assert data["persona_match"] == "av_director"

    def test_get_lead_not_found(self, client, mock_supabase):
        """Test 404 when lead not found."""
        mock_supabase.get_lead_by_id = MagicMock(return_value=None)

        response = client.get("/api/leads/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
