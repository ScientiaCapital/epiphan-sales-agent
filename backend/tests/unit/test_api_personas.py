"""
Tests for GET /api/personas and GET /api/personas/{persona_id} endpoints.

TDD: These tests define the API contract BEFORE implementation.
Tests should FAIL until the endpoints are created.

Test Categories:
1. List personas - returns all 8 personas, filter by vertical
2. Get persona by ID - valid ID returns 200, invalid returns 404
3. Response schema - pain_points, discovery_questions, objections present
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
# List Personas
# =============================================================================


class TestListPersonas:
    """Tests for GET /api/personas endpoint."""

    @pytest.mark.asyncio
    async def test_returns_200(self, client: AsyncClient):
        """Should return 200 when listing all personas."""
        response = await client.get("/api/personas")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_all_8_personas(self, client: AsyncClient):
        """Should return all 8 persona profiles."""
        response = await client.get("/api/personas")
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 8

    @pytest.mark.asyncio
    async def test_all_persona_ids_present(self, client: AsyncClient):
        """All expected persona IDs should be in the response."""
        response = await client.get("/api/personas")
        data = response.json()
        persona_ids = {p["id"] for p in data}
        expected_ids = {
            "av_director",
            "ld_director",
            "technical_director",
            "simulation_director",
            "court_administrator",
            "corp_comms_director",
            "ehs_manager",
            "law_firm_it",
        }
        assert persona_ids == expected_ids

    @pytest.mark.asyncio
    async def test_filter_by_vertical_higher_ed(self, client: AsyncClient):
        """Filtering by higher_ed should return personas with that vertical."""
        response = await client.get("/api/personas", params={"vertical": "higher_ed"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        # All returned personas should have higher_ed in their verticals
        for persona in data:
            assert "higher_ed" in persona["verticals"]

    @pytest.mark.asyncio
    async def test_filter_by_vertical_healthcare(self, client: AsyncClient):
        """Filtering by healthcare should return relevant personas."""
        response = await client.get("/api/personas", params={"vertical": "healthcare"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        for persona in data:
            assert "healthcare" in persona["verticals"]

    @pytest.mark.asyncio
    async def test_filter_by_invalid_vertical_returns_422(self, client: AsyncClient):
        """Invalid vertical value should return 422."""
        response = await client.get("/api/personas", params={"vertical": "invalid"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_has_cache_control_header(self, client: AsyncClient):
        """Response should include Cache-Control header."""
        response = await client.get("/api/personas")
        assert "cache-control" in response.headers
        cache_header = response.headers["cache-control"]
        assert "public" in cache_header
        assert "max-age=" in cache_header


# =============================================================================
# Get Persona by ID
# =============================================================================


class TestGetPersonaById:
    """Tests for GET /api/personas/{persona_id} endpoint."""

    @pytest.mark.asyncio
    async def test_returns_200_for_valid_id(self, client: AsyncClient):
        """Should return 200 for valid persona ID."""
        response = await client.get("/api/personas/av_director")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_404_for_invalid_id(self, client: AsyncClient):
        """Should return 404 for non-existent persona ID."""
        response = await client.get("/api/personas/invalid_persona")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_404_response_has_detail(self, client: AsyncClient):
        """404 response should contain error detail."""
        response = await client.get("/api/personas/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_returns_correct_persona(self, client: AsyncClient):
        """Should return the correct persona matching the ID."""
        response = await client.get("/api/personas/simulation_director")
        data = response.json()
        assert data["id"] == "simulation_director"
        assert data["title"] == "Simulation Center Director"

    @pytest.mark.asyncio
    async def test_all_persona_ids_accessible(self, client: AsyncClient):
        """All 8 persona IDs should be accessible."""
        persona_ids = [
            "av_director",
            "ld_director",
            "technical_director",
            "simulation_director",
            "court_administrator",
            "corp_comms_director",
            "ehs_manager",
            "law_firm_it",
        ]
        for persona_id in persona_ids:
            response = await client.get(f"/api/personas/{persona_id}")
            assert response.status_code == 200, f"Failed for {persona_id}"

    @pytest.mark.asyncio
    async def test_has_cache_control_header(self, client: AsyncClient):
        """Response should include Cache-Control header."""
        response = await client.get("/api/personas/av_director")
        assert "cache-control" in response.headers


# =============================================================================
# Response Schema Validation
# =============================================================================


class TestPersonaSchema:
    """Tests for PersonaProfile response schema."""

    @pytest.mark.asyncio
    async def test_has_pain_points_list(self, client: AsyncClient):
        """Persona should have pain_points as a list."""
        response = await client.get("/api/personas/av_director")
        data = response.json()
        assert "pain_points" in data
        assert isinstance(data["pain_points"], list)
        assert len(data["pain_points"]) > 0

    @pytest.mark.asyncio
    async def test_pain_points_have_required_fields(self, client: AsyncClient):
        """Each pain point should have point, emotional_impact, solution."""
        response = await client.get("/api/personas/ld_director")
        data = response.json()
        for pain in data["pain_points"]:
            assert "point" in pain
            assert "emotional_impact" in pain
            assert "solution" in pain

    @pytest.mark.asyncio
    async def test_has_discovery_questions(self, client: AsyncClient):
        """Persona should have discovery_questions list."""
        response = await client.get("/api/personas/technical_director")
        data = response.json()
        assert "discovery_questions" in data
        assert isinstance(data["discovery_questions"], list)
        assert len(data["discovery_questions"]) > 0

    @pytest.mark.asyncio
    async def test_has_objections_list(self, client: AsyncClient):
        """Persona should have objections as a list."""
        response = await client.get("/api/personas/court_administrator")
        data = response.json()
        assert "objections" in data
        assert isinstance(data["objections"], list)
        assert len(data["objections"]) > 0

    @pytest.mark.asyncio
    async def test_objections_have_objection_and_response(self, client: AsyncClient):
        """Each objection should have objection and response fields."""
        response = await client.get("/api/personas/ehs_manager")
        data = response.json()
        for obj in data["objections"]:
            assert "objection" in obj
            assert "response" in obj

    @pytest.mark.asyncio
    async def test_has_buying_signals(self, client: AsyncClient):
        """Persona should have buying_signals with high and medium lists."""
        response = await client.get("/api/personas/law_firm_it")
        data = response.json()
        assert "buying_signals" in data
        assert "high" in data["buying_signals"]
        assert "medium" in data["buying_signals"]

    @pytest.mark.asyncio
    async def test_has_verticals_list(self, client: AsyncClient):
        """Persona should have verticals list."""
        response = await client.get("/api/personas/corp_comms_director")
        data = response.json()
        assert "verticals" in data
        assert isinstance(data["verticals"], list)
        assert len(data["verticals"]) > 0

    @pytest.mark.asyncio
    async def test_has_all_required_persona_fields(self, client: AsyncClient):
        """Persona should have all required PersonaProfile fields."""
        response = await client.get("/api/personas/av_director")
        data = response.json()

        required_fields = [
            "id",
            "title",
            "title_variations",
            "reports_to",
            "team_size",
            "budget_authority",
            "verticals",
            "day_to_day",
            "kpis",
            "pain_points",
            "hot_buttons",
            "discovery_questions",
            "objections",
            "buying_signals",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
