"""
Tests for GET /api/scripts/cold endpoint.

TDD: These tests define the API contract BEFORE implementation.
Tests should FAIL until the endpoint is created.

Test Categories:
1. Success paths - all 7 verticals return scripts
2. Response schema - all ColdCallScript fields present
3. Validation errors - missing/invalid vertical (422)
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
# Success Paths: All Verticals
# =============================================================================


class TestColdScriptEndpointSuccess:
    """Tests for successful cold script retrieval by vertical."""

    @pytest.mark.asyncio
    async def test_returns_200_for_higher_ed(self, client: AsyncClient):
        """Should return 200 for higher_ed vertical."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "higher_ed"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_200_for_corporate(self, client: AsyncClient):
        """Should return 200 for corporate vertical."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "corporate"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_200_for_healthcare(self, client: AsyncClient):
        """Should return 200 for healthcare vertical."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "healthcare"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_200_for_house_of_worship(self, client: AsyncClient):
        """Should return 200 for house_of_worship vertical."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "house_of_worship"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_200_for_government(self, client: AsyncClient):
        """Should return 200 for government vertical."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "government"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_200_for_live_events(self, client: AsyncClient):
        """Should return 200 for live_events vertical."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "live_events"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_200_for_industrial(self, client: AsyncClient):
        """Should return 200 for industrial vertical."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "industrial"},
        )
        assert response.status_code == 200


# =============================================================================
# Response Schema Validation
# =============================================================================


class TestColdScriptResponseSchema:
    """Tests for response conforming to ColdCallScript schema."""

    @pytest.mark.asyncio
    async def test_response_has_all_required_fields(self, client: AsyncClient):
        """Response should contain all ColdCallScript fields."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "higher_ed"},
        )
        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "id",
            "vertical",
            "vertical_icon",
            "target_persona",
            "pattern_interrupt",
            "value_hook",
            "pain_question",
            "permission",
            "pivot",
            "why_it_works",
            "objection_pivots",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_why_it_works_is_list_of_strings(self, client: AsyncClient):
        """why_it_works should be a list of strings."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "corporate"},
        )
        data = response.json()
        assert isinstance(data["why_it_works"], list)
        assert len(data["why_it_works"]) > 0
        assert all(isinstance(item, str) for item in data["why_it_works"])

    @pytest.mark.asyncio
    async def test_objection_pivots_is_list_of_objects(self, client: AsyncClient):
        """objection_pivots should be a list with objection/response pairs."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "healthcare"},
        )
        data = response.json()
        assert isinstance(data["objection_pivots"], list)
        assert len(data["objection_pivots"]) > 0
        for pivot in data["objection_pivots"]:
            assert "objection" in pivot
            assert "response" in pivot

    @pytest.mark.asyncio
    async def test_vertical_matches_request(self, client: AsyncClient):
        """Returned vertical should match requested vertical."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "government"},
        )
        data = response.json()
        assert data["vertical"] == "government"


# =============================================================================
# Validation Errors (422)
# =============================================================================


class TestColdScriptValidation:
    """Tests for parameter validation returning 422."""

    @pytest.mark.asyncio
    async def test_missing_vertical_returns_422(self, client: AsyncClient):
        """Should return 422 when vertical is missing."""
        response = await client.get("/api/scripts/cold")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_vertical_returns_422(self, client: AsyncClient):
        """Should return 422 for invalid vertical value."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "invalid_vertical"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_vertical_returns_422(self, client: AsyncClient):
        """Should return 422 for empty vertical."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": ""},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_422_response_contains_detail(self, client: AsyncClient):
        """422 response should contain validation error detail."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "bad_value"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


# =============================================================================
# Caching
# =============================================================================


class TestColdScriptCaching:
    """Tests for Cache-Control headers."""

    @pytest.mark.asyncio
    async def test_response_has_cache_control_header(self, client: AsyncClient):
        """Response should include Cache-Control header."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "higher_ed"},
        )
        assert response.status_code == 200
        assert "cache-control" in response.headers
        # Should be public with a max-age value
        cache_header = response.headers["cache-control"]
        assert "public" in cache_header
        assert "max-age=" in cache_header

    @pytest.mark.asyncio
    async def test_cache_max_age_is_reasonable(self, client: AsyncClient):
        """Cache max-age should be at least 1 hour (static data)."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "corporate"},
        )
        cache_header = response.headers.get("cache-control", "")
        # Extract max-age value
        for part in cache_header.split(","):
            part = part.strip()
            if part.startswith("max-age="):
                max_age = int(part.split("=")[1])
                assert max_age >= 3600, "Cache should be at least 1 hour for static data"
                break


# =============================================================================
# Edge Cases
# =============================================================================


class TestColdScriptEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_vertical_is_case_sensitive(self, client: AsyncClient):
        """Vertical should be case sensitive (lowercase required)."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "HIGHER_ED"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_extra_query_params_ignored(self, client: AsyncClient):
        """Extra query params should be ignored."""
        response = await client.get(
            "/api/scripts/cold",
            params={"vertical": "higher_ed", "extra_param": "ignored"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_repeated_requests_return_same_result(self, client: AsyncClient):
        """Same request should return deterministic result."""
        params = {"vertical": "higher_ed"}
        response1 = await client.get("/api/scripts/cold", params=params)
        response2 = await client.get("/api/scripts/cold", params=params)
        assert response1.json() == response2.json()
