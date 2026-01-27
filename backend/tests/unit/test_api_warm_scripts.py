"""
Tests for GET /api/scripts/warm endpoint.

TDD: These tests define the API contract BEFORE implementation.
Tests should FAIL until the endpoint is created.

Test Categories:
1. Success paths - persona-specific and generic fallback
2. Validation errors - invalid enum values (422)
3. Response schema - ACQP fields, metadata, lists
4. Edge cases - case sensitivity, missing combos
5. Content quality - persona-relevant keywords
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
# Success Paths: Persona-Specific Scripts
# =============================================================================


class TestWarmScriptEndpointSuccessPersonaSpecific:
    """Tests for successful persona-specific script retrieval."""

    @pytest.mark.asyncio
    async def test_returns_200_for_av_director_content_download(self, client: AsyncClient):
        """Should return 200 for av_director + content_download combo."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "content_download", "persona_type": "av_director"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_persona_specific_source(self, client: AsyncClient):
        """Persona + trigger combo should return source='persona_specific'."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "demo_request", "persona_type": "ld_director"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "persona_specific"

    @pytest.mark.asyncio
    async def test_returns_discovery_questions_for_persona(self, client: AsyncClient):
        """Persona-specific scripts should include discovery questions."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "content_download", "persona_type": "simulation_director"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "discovery_questions" in data
        assert len(data["discovery_questions"]) > 0

    @pytest.mark.asyncio
    async def test_returns_what_to_listen_for_for_persona(self, client: AsyncClient):
        """Persona-specific scripts should include listening cues."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "pricing_page", "persona_type": "court_administrator"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "what_to_listen_for" in data
        assert isinstance(data["what_to_listen_for"], list)

    @pytest.mark.asyncio
    async def test_all_priority_personas_have_demo_request_script(self, client: AsyncClient):
        """All 5 priority personas should have demo_request scripts."""
        priority_personas = [
            "av_director",
            "ld_director",
            "technical_director",
            "simulation_director",
            "court_administrator",
        ]
        for persona in priority_personas:
            response = await client.get(
                "/api/scripts/warm",
                params={"trigger_type": "demo_request", "persona_type": persona},
            )
            assert response.status_code == 200, f"Failed for {persona}"
            data = response.json()
            assert data["source"] == "persona_specific", f"{persona} should be persona_specific"

    @pytest.mark.asyncio
    async def test_includes_persona_type_in_response(self, client: AsyncClient):
        """Response should echo back the persona_type."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "webinar_attended", "persona_type": "technical_director"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["persona_type"] == "technical_director"

    @pytest.mark.asyncio
    async def test_includes_trigger_type_in_response(self, client: AsyncClient):
        """Response should echo back the trigger_type."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "pricing_page", "persona_type": "av_director"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["trigger_type"] == "pricing_page"

    @pytest.mark.asyncio
    async def test_corp_comms_director_has_persona_specific_script(self, client: AsyncClient):
        """Corp Comms Director should have persona-specific scripts."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "content_download", "persona_type": "corp_comms_director"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "persona_specific"


# =============================================================================
# Success Paths: Generic Fallback Scripts
# =============================================================================


class TestWarmScriptEndpointSuccessGenericFallback:
    """Tests for generic trigger-based script fallback."""

    @pytest.mark.asyncio
    async def test_returns_200_without_persona(self, client: AsyncClient):
        """Should return 200 when only trigger_type provided."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "content_download"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_generic_source_without_persona(self, client: AsyncClient):
        """Without persona, should return source='trigger_generic'."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "referral"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "trigger_generic"

    @pytest.mark.asyncio
    async def test_generic_script_has_acqp_fields(self, client: AsyncClient):
        """Generic scripts should still have ACQP fields."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "trade_show"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "acknowledge" in data
        assert "connect" in data
        assert "qualify" in data
        assert "propose" in data

    @pytest.mark.asyncio
    async def test_all_trigger_types_have_generic_scripts(self, client: AsyncClient):
        """All trigger types should have at least a generic script."""
        triggers = [
            "content_download",
            "webinar_attended",
            "demo_request",
            "pricing_page",
            "contact_form",
            "trade_show",
            "referral",
            "return_visitor",
        ]
        for trigger in triggers:
            response = await client.get(
                "/api/scripts/warm",
                params={"trigger_type": trigger},
            )
            assert response.status_code == 200, f"No script for {trigger}"

    @pytest.mark.asyncio
    async def test_generic_fallback_for_unsupported_persona_trigger_combo(
        self, client: AsyncClient
    ):
        """Should fall back to generic when persona doesn't have trigger script."""
        # referral trigger typically doesn't have persona-specific scripts
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "referral", "persona_type": "av_director"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "trigger_generic"

    @pytest.mark.asyncio
    async def test_generic_script_has_empty_discovery_questions(self, client: AsyncClient):
        """Generic scripts should have empty discovery_questions list."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "contact_form"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["discovery_questions"] == []


# =============================================================================
# Validation Errors (422)
# =============================================================================


class TestWarmScriptEndpointInvalidParams:
    """Tests for parameter validation returning 422."""

    @pytest.mark.asyncio
    async def test_missing_trigger_type_returns_422(self, client: AsyncClient):
        """Should return 422 when trigger_type is missing."""
        response = await client.get("/api/scripts/warm")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_trigger_type_returns_422(self, client: AsyncClient):
        """Should return 422 for invalid trigger_type value."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "invalid_trigger"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_persona_type_returns_422(self, client: AsyncClient):
        """Should return 422 for invalid persona_type value."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "demo_request", "persona_type": "ceo"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_trigger_type_returns_422(self, client: AsyncClient):
        """Should return 422 for empty trigger_type."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": ""},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_numeric_trigger_type_returns_422(self, client: AsyncClient):
        """Should return 422 for numeric trigger_type."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": 123},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_422_response_contains_detail(self, client: AsyncClient):
        """422 response should contain validation error detail."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "bad_value"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


# =============================================================================
# Response Schema Validation
# =============================================================================


class TestWarmScriptResponseSchema:
    """Tests for response structure conforming to WarmCallScript schema."""

    @pytest.mark.asyncio
    async def test_response_has_all_required_fields(self, client: AsyncClient):
        """Response should contain all WarmCallScript fields."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "demo_request", "persona_type": "av_director"},
        )
        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "acknowledge",
            "connect",
            "qualify",
            "propose",
            "discovery_questions",
            "what_to_listen_for",
            "source",
            "persona_type",
            "trigger_type",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_acqp_fields_are_strings(self, client: AsyncClient):
        """ACQP fields should be non-empty strings."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "content_download", "persona_type": "ld_director"},
        )
        data = response.json()
        assert isinstance(data["acknowledge"], str) and len(data["acknowledge"]) > 0
        assert isinstance(data["connect"], str) and len(data["connect"]) > 0
        assert isinstance(data["qualify"], str) and len(data["qualify"]) > 0
        assert isinstance(data["propose"], str) and len(data["propose"]) > 0

    @pytest.mark.asyncio
    async def test_discovery_questions_is_list_of_strings(self, client: AsyncClient):
        """discovery_questions should be a list of strings."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "demo_request", "persona_type": "simulation_director"},
        )
        data = response.json()
        assert isinstance(data["discovery_questions"], list)
        if data["discovery_questions"]:
            assert all(isinstance(q, str) for q in data["discovery_questions"])

    @pytest.mark.asyncio
    async def test_source_is_valid_enum_value(self, client: AsyncClient):
        """source should be either 'persona_specific' or 'trigger_generic'."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "pricing_page", "persona_type": "technical_director"},
        )
        data = response.json()
        assert data["source"] in ["persona_specific", "trigger_generic"]

    @pytest.mark.asyncio
    async def test_persona_type_null_when_not_provided(self, client: AsyncClient):
        """persona_type in response should be null when not in request."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "return_visitor"},
        )
        data = response.json()
        assert data["persona_type"] is None


# =============================================================================
# Edge Cases
# =============================================================================


class TestWarmScriptEndpointEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_trigger_type_is_case_sensitive(self, client: AsyncClient):
        """Trigger type should be case sensitive (lowercase required)."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "DEMO_REQUEST"},
        )
        # Enum values are lowercase, uppercase should fail
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_persona_type_is_case_sensitive(self, client: AsyncClient):
        """Persona type should be case sensitive (lowercase required)."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "demo_request", "persona_type": "AV_DIRECTOR"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_extra_query_params_ignored(self, client: AsyncClient):
        """Extra query params should be ignored."""
        response = await client.get(
            "/api/scripts/warm",
            params={
                "trigger_type": "demo_request",
                "persona_type": "av_director",
                "extra_param": "should_be_ignored",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_whitespace_in_trigger_type_returns_422(self, client: AsyncClient):
        """Whitespace in trigger_type returns 422 (not stripped)."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": " demo_request "},
        )
        # Query params with whitespace don't match enum values exactly
        # " demo_request " != "demo_request"
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_null_persona_type_is_valid(self, client: AsyncClient):
        """Explicitly passing null persona_type should work."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "demo_request"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_repeated_requests_return_same_result(self, client: AsyncClient):
        """Same request should return deterministic result."""
        params = {"trigger_type": "content_download", "persona_type": "av_director"}
        response1 = await client.get("/api/scripts/warm", params=params)
        response2 = await client.get("/api/scripts/warm", params=params)
        assert response1.json() == response2.json()


# =============================================================================
# Content Quality
# =============================================================================


class TestWarmScriptContentQuality:
    """Tests for content quality and persona relevance."""

    @pytest.mark.asyncio
    async def test_av_director_script_mentions_rooms_or_fleet(self, client: AsyncClient):
        """AV Director scripts should mention rooms, fleet, or campus."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "content_download", "persona_type": "av_director"},
        )
        data = response.json()
        script_text = " ".join([
            data["acknowledge"],
            data["connect"],
            data["qualify"],
            data["propose"],
        ]).lower()
        assert any(
            keyword in script_text for keyword in ["room", "fleet", "campus", "remote"]
        ), "AV Director script should contain relevant keywords"

    @pytest.mark.asyncio
    async def test_simulation_director_script_mentions_hipaa_or_training(
        self, client: AsyncClient
    ):
        """Simulation Director scripts should mention HIPAA, training, or sim."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "demo_request", "persona_type": "simulation_director"},
        )
        data = response.json()
        script_text = " ".join([
            data["acknowledge"],
            data["connect"],
            data["qualify"],
            data["propose"],
        ]).lower()
        assert any(
            keyword in script_text
            for keyword in ["hipaa", "training", "sim", "compliance", "clinical", "debrief"]
        ), "Simulation Director script should contain relevant keywords"

    @pytest.mark.asyncio
    async def test_court_administrator_script_mentions_court_or_record(
        self, client: AsyncClient
    ):
        """Court Administrator scripts should mention court, record, or hearing."""
        response = await client.get(
            "/api/scripts/warm",
            params={"trigger_type": "pricing_page", "persona_type": "court_administrator"},
        )
        data = response.json()
        script_text = " ".join([
            data["acknowledge"],
            data["connect"],
            data["qualify"],
            data["propose"],
        ]).lower()
        assert any(
            keyword in script_text
            for keyword in ["court", "record", "hearing", "reporter", "proceeding"]
        ), "Court Administrator script should contain relevant keywords"
