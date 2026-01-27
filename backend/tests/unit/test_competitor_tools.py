"""Tests for competitor intelligence tools."""

import pytest


class TestGetBattlecard:
    """Tests for get_battlecard tool."""

    def test_returns_battlecard_for_valid_competitor(self):
        """Test returning battlecard for known competitor."""
        from app.services.langgraph.tools.competitor_tools import get_battlecard

        result = get_battlecard("blackmagic")

        assert result is not None
        assert result["id"] == "blackmagic_atem"
        assert "key_differentiators" in result

    def test_returns_none_for_unknown_competitor(self):
        """Test returning None for unknown competitor."""
        from app.services.langgraph.tools.competitor_tools import get_battlecard

        result = get_battlecard("unknown_competitor_xyz")

        assert result is None

    def test_matches_partial_name(self):
        """Test matching partial competitor name."""
        from app.services.langgraph.tools.competitor_tools import get_battlecard

        result = get_battlecard("atem")

        assert result is not None
        assert "blackmagic" in result["id"].lower() or "atem" in result["name"].lower()

    def test_matches_company_name(self):
        """Test matching by company name."""
        from app.services.langgraph.tools.competitor_tools import get_battlecard

        result = get_battlecard("blackmagic design")

        assert result is not None
        assert result["company"] == "Blackmagic Design"

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        from app.services.langgraph.tools.competitor_tools import get_battlecard

        result = get_battlecard("BLACKMAGIC")

        assert result is not None
        assert result["id"] == "blackmagic_atem"


class TestSearchDifferentiators:
    """Tests for search_differentiators tool."""

    def test_finds_differentiators_by_keyword(self):
        """Test finding differentiators by keyword."""
        from app.services.langgraph.tools.competitor_tools import search_differentiators

        result = search_differentiators("blackmagic_atem", "recording")

        assert len(result) > 0
        assert any("recording" in str(d).lower() for d in result)

    def test_returns_empty_for_no_match(self):
        """Test returning empty list when no match."""
        from app.services.langgraph.tools.competitor_tools import search_differentiators

        result = search_differentiators("blackmagic_atem", "xyznonexistent")

        assert result == []

    def test_returns_empty_for_unknown_competitor(self):
        """Test returning empty for unknown competitor."""
        from app.services.langgraph.tools.competitor_tools import search_differentiators

        result = search_differentiators("unknown_xyz", "recording")

        assert result == []

    def test_finds_multiple_matches(self):
        """Test finding multiple matching differentiators."""
        from app.services.langgraph.tools.competitor_tools import search_differentiators

        # "fleet" should match Fleet Management differentiator
        result = search_differentiators("blackmagic_atem", "fleet")

        assert len(result) >= 1


class TestGetClaimResponses:
    """Tests for get_claim_responses tool."""

    def test_returns_claim_responses(self):
        """Test returning claim responses for competitor."""
        from app.services.langgraph.tools.competitor_tools import get_claim_responses

        result = get_claim_responses("blackmagic_atem")

        assert len(result) > 0
        assert all("claim" in r and "response" in r for r in result)

    def test_filters_by_keyword(self):
        """Test filtering claim responses by keyword."""
        from app.services.langgraph.tools.competitor_tools import get_claim_responses

        result = get_claim_responses("blackmagic_atem", keyword="cheaper")

        assert len(result) > 0
        assert any("cheaper" in r["claim"].lower() for r in result)

    def test_returns_empty_for_unknown_competitor(self):
        """Test returning empty for unknown competitor."""
        from app.services.langgraph.tools.competitor_tools import get_claim_responses

        result = get_claim_responses("unknown_xyz")

        assert result == []

    def test_returns_all_when_no_keyword(self):
        """Test returning all claims when no keyword."""
        from app.services.langgraph.tools.competitor_tools import get_claim_responses

        result = get_claim_responses("blackmagic_atem")

        # Blackmagic has at least 3 claims
        assert len(result) >= 3


class TestBattlecardToDict:
    """Tests for _battlecard_to_dict helper."""

    def test_converts_all_fields(self):
        """Test that all fields are converted."""
        from app.services.langgraph.tools.competitor_tools import get_battlecard

        result = get_battlecard("blackmagic_atem")

        assert result is not None
        assert "id" in result
        assert "name" in result
        assert "company" in result
        assert "price_range" in result
        assert "positioning" in result
        assert "key_differentiators" in result
        assert "claims" in result
        assert isinstance(result["key_differentiators"], list)
        assert isinstance(result["claims"], list)
