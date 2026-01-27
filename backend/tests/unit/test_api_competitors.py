"""
Tests for GET /api/competitors and GET /api/competitors/{competitor_id} endpoints.

TDD: These tests define the API contract BEFORE implementation.
Tests should FAIL until the endpoints are created.

Test Categories:
1. List competitors - default returns active only, filter by vertical
2. Get competitor by ID - valid ID returns 200, invalid returns 404
3. Response schema - key_differentiators, talk_track, claims present
4. Caching - Cache-Control header present
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def client() -> AsyncClient:
    """HTTP client configured with our FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# List Competitors
# =============================================================================


class TestListCompetitors:
    """Tests for GET /api/competitors endpoint."""

    @pytest.mark.asyncio
    async def test_returns_200(self, client: AsyncClient):
        """Should return 200 when listing competitors."""
        response = await client.get("/api/competitors")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_list_of_competitors(self, client: AsyncClient):
        """Should return a list of competitor battlecards."""
        response = await client.get("/api/competitors")
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_default_returns_active_only(self, client: AsyncClient):
        """Default listing should return only active competitors."""
        response = await client.get("/api/competitors")
        data = response.json()
        for competitor in data:
            assert competitor["status"] == "active"

    @pytest.mark.asyncio
    async def test_include_inactive_returns_all(self, client: AsyncClient):
        """include_inactive=true should return discontinued/complementary too."""
        response = await client.get("/api/competitors", params={"include_inactive": "true"})
        data = response.json()
        statuses = {c["status"] for c in data}
        # Should include at least active, may include discontinued/complementary
        assert "active" in statuses
        # Total should be more than just active
        assert len(data) >= 10  # We have 13 competitors total

    @pytest.mark.asyncio
    async def test_filter_by_vertical_house_of_worship(self, client: AsyncClient):
        """Filtering by vertical should return relevant competitors."""
        response = await client.get(
            "/api/competitors", params={"vertical": "house_of_worship"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        for competitor in data:
            assert "house_of_worship" in competitor["target_verticals"]

    @pytest.mark.asyncio
    async def test_filter_by_vertical_higher_ed(self, client: AsyncClient):
        """Filtering by higher_ed should return education-focused competitors."""
        response = await client.get("/api/competitors", params={"vertical": "higher_ed"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        for competitor in data:
            assert "higher_ed" in competitor["target_verticals"]

    @pytest.mark.asyncio
    async def test_filter_by_invalid_vertical_returns_422(self, client: AsyncClient):
        """Invalid vertical value should return 422."""
        response = await client.get("/api/competitors", params={"vertical": "invalid"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_has_cache_control_header(self, client: AsyncClient):
        """Response should include Cache-Control header."""
        response = await client.get("/api/competitors")
        assert "cache-control" in response.headers
        cache_header = response.headers["cache-control"]
        assert "public" in cache_header
        assert "max-age=" in cache_header


# =============================================================================
# Get Competitor by ID
# =============================================================================


class TestGetCompetitorById:
    """Tests for GET /api/competitors/{competitor_id} endpoint."""

    @pytest.mark.asyncio
    async def test_returns_200_for_valid_id(self, client: AsyncClient):
        """Should return 200 for valid competitor ID."""
        response = await client.get("/api/competitors/blackmagic_atem")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_404_for_invalid_id(self, client: AsyncClient):
        """Should return 404 for non-existent competitor ID."""
        response = await client.get("/api/competitors/invalid_competitor")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_404_response_has_detail(self, client: AsyncClient):
        """404 response should contain error detail."""
        response = await client.get("/api/competitors/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_returns_correct_competitor(self, client: AsyncClient):
        """Should return the correct competitor matching the ID."""
        response = await client.get("/api/competitors/tricaster")
        data = response.json()
        assert data["id"] == "tricaster"
        assert data["name"] == "TriCaster"
        assert data["company"] == "Vizrt (formerly NewTek)"

    @pytest.mark.asyncio
    async def test_top_competitors_accessible(self, client: AsyncClient):
        """Top competitors should be accessible by ID."""
        competitor_ids = [
            "blackmagic_atem",
            "tricaster",
            "vmix",
            "teradek",
            "yolobox",
        ]
        for competitor_id in competitor_ids:
            response = await client.get(f"/api/competitors/{competitor_id}")
            assert response.status_code == 200, f"Failed for {competitor_id}"

    @pytest.mark.asyncio
    async def test_has_cache_control_header(self, client: AsyncClient):
        """Response should include Cache-Control header."""
        response = await client.get("/api/competitors/blackmagic_atem")
        assert "cache-control" in response.headers


# =============================================================================
# Response Schema Validation
# =============================================================================


class TestCompetitorSchema:
    """Tests for CompetitorBattlecard response schema."""

    @pytest.mark.asyncio
    async def test_has_key_differentiators(self, client: AsyncClient):
        """Competitor should have key_differentiators list."""
        response = await client.get("/api/competitors/blackmagic_atem")
        data = response.json()
        assert "key_differentiators" in data
        assert isinstance(data["key_differentiators"], list)
        assert len(data["key_differentiators"]) > 0

    @pytest.mark.asyncio
    async def test_key_differentiator_structure(self, client: AsyncClient):
        """Each differentiator should have required fields."""
        response = await client.get("/api/competitors/tricaster")
        data = response.json()
        for diff in data["key_differentiators"]:
            assert "feature" in diff
            assert "competitor_capability" in diff
            assert "pearl_capability" in diff
            assert "why_it_matters" in diff

    @pytest.mark.asyncio
    async def test_has_talk_track(self, client: AsyncClient):
        """Competitor should have talk_track with opening and closing."""
        response = await client.get("/api/competitors/vmix")
        data = response.json()
        assert "talk_track" in data
        assert "opening" in data["talk_track"]
        assert "closing" in data["talk_track"]

    @pytest.mark.asyncio
    async def test_has_claims_list(self, client: AsyncClient):
        """Competitor should have claims with claim/response pairs."""
        response = await client.get("/api/competitors/teradek")
        data = response.json()
        assert "claims" in data
        assert isinstance(data["claims"], list)
        for claim in data["claims"]:
            assert "claim" in claim
            assert "response" in claim

    @pytest.mark.asyncio
    async def test_has_when_to_compete_list(self, client: AsyncClient):
        """Competitor should have when_to_compete list."""
        response = await client.get("/api/competitors/yolobox")
        data = response.json()
        assert "when_to_compete" in data
        assert isinstance(data["when_to_compete"], list)
        assert len(data["when_to_compete"]) > 0

    @pytest.mark.asyncio
    async def test_has_when_to_walk_away_list(self, client: AsyncClient):
        """Competitor should have when_to_walk_away list."""
        response = await client.get("/api/competitors/blackmagic_atem")
        data = response.json()
        assert "when_to_walk_away" in data
        assert isinstance(data["when_to_walk_away"], list)

    @pytest.mark.asyncio
    async def test_has_target_verticals(self, client: AsyncClient):
        """Competitor should have target_verticals list."""
        response = await client.get("/api/competitors/lumens")
        data = response.json()
        assert "target_verticals" in data
        assert isinstance(data["target_verticals"], list)

    @pytest.mark.asyncio
    async def test_has_all_required_fields(self, client: AsyncClient):
        """Competitor should have all required CompetitorBattlecard fields."""
        response = await client.get("/api/competitors/blackmagic_atem")
        data = response.json()

        required_fields = [
            "id",
            "name",
            "company",
            "price_range",
            "positioning",
            "market_context",
            "status",
            "target_verticals",
            "when_to_compete",
            "when_to_walk_away",
            "key_differentiators",
            "claims",
            "proof_points",
            "talk_track",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_status_is_valid_enum(self, client: AsyncClient):
        """Status should be a valid CompetitorStatus value."""
        response = await client.get("/api/competitors/slingstudio")
        data = response.json()
        assert data["status"] in ["active", "discontinued", "complementary"]
