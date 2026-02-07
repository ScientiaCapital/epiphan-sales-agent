"""Tests for university account API endpoints.

Tests the REST API for university account management:
- POST /api/university-accounts (create & score)
- POST /api/university-accounts/batch (batch import)
- GET /api/university-accounts (list with filters)
- GET /api/university-accounts/gap-analysis
- GET /api/university-accounts/summary
- GET /api/university-accounts/{id}
- PATCH /api/university-accounts/{id}/contacts
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def mock_supabase() -> MagicMock:
    """Mock Supabase client for university account tests."""
    mock = MagicMock()
    mock.upsert_university_account.return_value = {
        "id": "test-uuid-123",
        "name": "MIT",
        "state": "MA",
    }
    mock.upsert_university_accounts_batch.return_value = 5
    mock.get_university_account.return_value = None
    mock.get_university_accounts_by_tier.return_value = []
    mock.get_university_accounts_filtered.return_value = []
    mock.get_university_account_tier_counts.return_value = {
        "A": 10, "B": 25, "C": 40, "D": 15,
    }
    mock.get_university_gap_accounts.return_value = []
    mock.update_university_account_contacts.return_value = {}
    mock.get_university_account_by_domain.return_value = None
    return mock


@pytest.fixture
async def client() -> AsyncClient:
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# =============================================================================
# Create & Score Account
# =============================================================================


class TestCreateAndScoreAccount:
    """Tests for POST /api/university-accounts."""

    @pytest.mark.asyncio
    async def test_score_r1_university(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.post(
                "/api/university-accounts",
                json={
                    "name": "University of Michigan",
                    "carnegie_classification": "r1",
                    "institution_type": "public",
                    "enrollment": 47000,
                    "lms_platform": "Canvas",
                    "video_platform": "Panopto",
                    "athletic_division": "ncaa_d1",
                    "state": "MI",
                    "contact_count": 3,
                    "decision_maker_count": 1,
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["account"]["account_tier"] == "A"
        assert data["account"]["total_score"] >= 75
        assert "next_action" in data
        assert "missing_data" in data

    @pytest.mark.asyncio
    async def test_score_minimal_data(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.post(
                "/api/university-accounts",
                json={"name": "Unknown College"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["account"]["account_tier"] == "D"
        assert len(data["missing_data"]) > 0

    @pytest.mark.asyncio
    async def test_score_breakdown_included(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.post(
                "/api/university-accounts",
                json={
                    "name": "Test University",
                    "carnegie_classification": "r2",
                    "enrollment": 20000,
                    "state": "CA",
                },
            )
        data = response.json()
        breakdown = data["account"]["score_breakdown"]
        assert "carnegie_classification" in breakdown
        assert "enrollment_size" in breakdown
        assert "technology_signals" in breakdown
        assert "engagement_level" in breakdown
        assert "strategic_fit" in breakdown
        assert breakdown["carnegie_classification"]["raw_score"] == 8

    @pytest.mark.asyncio
    async def test_db_failure_still_returns_score(
        self, client: AsyncClient, mock_supabase: MagicMock
    ) -> None:
        """Score should be returned even if DB persistence fails."""
        mock_supabase.upsert_university_account.side_effect = Exception("DB down")
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.post(
                "/api/university-accounts",
                json={
                    "name": "Resilient University",
                    "carnegie_classification": "r1",
                    "enrollment": 30000,
                    "state": "TX",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["account"]["total_score"] > 0
        assert data["account"]["id"] is None  # DB failed, no ID


# =============================================================================
# Batch Import
# =============================================================================


class TestBatchImport:
    """Tests for POST /api/university-accounts/batch."""

    @pytest.mark.asyncio
    async def test_batch_import_multiple(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.post(
                "/api/university-accounts/batch",
                json={
                    "source": "carnegie_classification",
                    "accounts": [
                        {
                            "name": "University of Michigan",
                            "carnegie_classification": "r1",
                            "enrollment": 47000,
                            "state": "MI",
                            "institution_type": "public",
                        },
                        {
                            "name": "Harvard University",
                            "carnegie_classification": "r1",
                            "enrollment": 31000,
                            "state": "MA",
                            "institution_type": "private_nonprofit",
                        },
                        {
                            "name": "Small CC",
                            "carnegie_classification": "associate",
                            "enrollment": 500,
                            "state": "OH",
                        },
                    ],
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["scored"] == 3
        assert data["failed"] == 0
        assert "tier_distribution" in data
        assert sum(data["tier_distribution"].values()) == 3

    @pytest.mark.asyncio
    async def test_batch_empty_list(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.post(
                "/api/university-accounts/batch",
                json={"accounts": []},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


# =============================================================================
# List Accounts
# =============================================================================


class TestListAccounts:
    """Tests for GET /api/university-accounts."""

    @pytest.mark.asyncio
    async def test_list_all(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        mock_supabase.get_university_accounts_filtered.return_value = [
            {"id": "1", "name": "MIT", "state": "MA", "account_tier": "A", "total_score": 85},
        ]
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.get("/api/university-accounts")
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
        assert data["total_count"] == 1

    @pytest.mark.asyncio
    async def test_filter_by_tier(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.get("/api/university-accounts?tier=A")
        assert response.status_code == 200
        mock_supabase.get_university_accounts_filtered.assert_called_once()
        call_kwargs = mock_supabase.get_university_accounts_filtered.call_args
        assert call_kwargs.kwargs.get("tier") == "A" or call_kwargs[1].get("tier") == "A"

    @pytest.mark.asyncio
    async def test_filter_by_state(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.get("/api/university-accounts?state=CA")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_no_contacts(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        """View 1 equivalent: A-tier with zero contacts."""
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.get("/api/university-accounts?tier=A&max_contacts=0")
        assert response.status_code == 200


# =============================================================================
# Gap Analysis
# =============================================================================


class TestGapAnalysis:
    """Tests for GET /api/university-accounts/gap-analysis."""

    @pytest.mark.asyncio
    async def test_gap_analysis_empty(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.get("/api/university-accounts/gap-analysis")
        assert response.status_code == 200
        data = response.json()
        assert data["total_gaps"] == 0

    @pytest.mark.asyncio
    async def test_gap_analysis_with_gaps(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        mock_supabase.get_university_accounts_by_tier.side_effect = [
            [  # A-tier
                {"id": "1", "name": "MIT", "account_tier": "A", "total_score": 90,
                 "contact_count": 0, "decision_maker_count": 0},
                {"id": "2", "name": "Stanford", "account_tier": "A", "total_score": 88,
                 "contact_count": 3, "decision_maker_count": 0},
            ],
            [  # B-tier
                {"id": "3", "name": "Oregon State", "account_tier": "B", "total_score": 60,
                 "contact_count": 2, "decision_maker_count": 1},
            ],
        ]
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.get("/api/university-accounts/gap-analysis")
        data = response.json()
        assert data["total_gaps"] == 3
        assert data["summary"]["no_contacts"] == 1
        assert data["summary"]["no_decision_maker"] == 1
        assert data["summary"]["ready"] == 1

        # Verify sort order: no_contacts first
        assert data["gaps"][0]["gap_type"] == "no_contacts"
        assert data["gaps"][1]["gap_type"] == "no_decision_maker"

    @pytest.mark.asyncio
    async def test_gap_analysis_recommended_actions(
        self, client: AsyncClient, mock_supabase: MagicMock
    ) -> None:
        mock_supabase.get_university_accounts_by_tier.side_effect = [
            [{"id": "1", "name": "MIT", "account_tier": "A", "total_score": 90,
              "contact_count": 0, "decision_maker_count": 0}],
            [],
        ]
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.get("/api/university-accounts/gap-analysis")
        data = response.json()
        assert "LinkedIn" in data["gaps"][0]["recommended_action"]


# =============================================================================
# Tier Summary
# =============================================================================


class TestTierSummary:
    """Tests for GET /api/university-accounts/summary."""

    @pytest.mark.asyncio
    async def test_summary(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.get("/api/university-accounts/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_accounts"] == 90  # 10 + 25 + 40 + 15
        assert "tier_counts" in data
        assert data["tier_counts"]["A"] == 10


# =============================================================================
# Single Account
# =============================================================================


class TestSingleAccount:
    """Tests for GET /api/university-accounts/{id}."""

    @pytest.mark.asyncio
    async def test_get_not_found(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.get("/api/university-accounts/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_existing_account(self, client: AsyncClient, mock_supabase: MagicMock) -> None:
        mock_supabase.get_university_account.return_value = {
            "id": "test-123",
            "name": "MIT",
            "state": "MA",
            "carnegie_classification": "r1",
            "enrollment": 11000,
            "account_tier": "A",
            "total_score": 85,
            "score_breakdown": None,
            "contact_count": 2,
            "decision_maker_count": 1,
        }
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.get("/api/university-accounts/test-123")
        assert response.status_code == 200
        data = response.json()
        assert data["account"]["name"] == "MIT"
        assert "next_action" in data


# =============================================================================
# Update Contacts
# =============================================================================


class TestUpdateContacts:
    """Tests for PATCH /api/university-accounts/{id}/contacts."""

    @pytest.mark.asyncio
    async def test_update_contacts_not_found(
        self, client: AsyncClient, mock_supabase: MagicMock
    ) -> None:
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.patch(
                "/api/university-accounts/nonexistent/contacts?contact_count=5"
            )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_contacts_rescores(
        self, client: AsyncClient, mock_supabase: MagicMock
    ) -> None:
        mock_supabase.get_university_account.return_value = {
            "id": "test-123",
            "name": "MIT",
            "state": "MA",
            "carnegie_classification": "r1",
            "institution_type": "public",
            "enrollment": 30000,
            "lms_platform": "Canvas",
            "video_platform": None,
            "av_system": None,
            "athletic_division": "ncaa_d1",
            "is_existing_customer": False,
            "has_active_opportunity": False,
            "contact_count": 0,
            "decision_maker_count": 0,
            "total_score": 60,
            "account_tier": "B",
        }
        with patch(
            "app.api.routes.university_accounts.supabase_client", mock_supabase
        ):
            response = await client.patch(
                "/api/university-accounts/test-123/contacts"
                "?contact_count=5&decision_maker_count=2"
            )
        assert response.status_code == 200
        data = response.json()
        assert data["contact_count"] == 5
        assert data["decision_maker_count"] == 2
        assert data["new_score"] > 60  # Score should increase with contacts
