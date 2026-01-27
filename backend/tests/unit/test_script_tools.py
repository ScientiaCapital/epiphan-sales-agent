"""Tests for script selection tools."""

import pytest


class TestGetWarmScript:
    """Tests for get_warm_script tool."""

    def test_returns_script_for_valid_persona_trigger(self):
        """Test returning script for valid persona and trigger."""
        from app.services.langgraph.tools.script_tools import get_warm_script

        result = get_warm_script("av_director", "demo_request")

        assert result is not None
        # ACQP framework: acknowledge, connect, qualify, propose
        assert "acknowledge" in result or "connect" in result

    def test_returns_none_for_invalid_persona(self):
        """Test returning None for invalid persona."""
        from app.services.langgraph.tools.script_tools import get_warm_script

        result = get_warm_script("invalid_persona", "demo_request")

        assert result is None

    def test_returns_script_with_objection_handlers(self):
        """Test that script includes objection handlers."""
        from app.services.langgraph.tools.script_tools import get_warm_script

        result = get_warm_script("av_director", "demo_request")

        assert result is not None
        assert "objection_handlers" in result
        assert isinstance(result["objection_handlers"], list)

    def test_different_triggers_return_different_scripts(self):
        """Test that different triggers return different scripts."""
        from app.services.langgraph.tools.script_tools import get_warm_script

        demo_script = get_warm_script("av_director", "demo_request")
        content_script = get_warm_script("av_director", "content_download")

        # Both should exist but have different content
        assert demo_script is not None
        assert content_script is not None
        # Triggers should be different
        assert demo_script.get("trigger") != content_script.get("trigger")


class TestGetColdScript:
    """Tests for get_cold_script tool."""

    def test_returns_script_for_valid_vertical(self):
        """Test returning script for valid vertical."""
        from app.services.langgraph.tools.script_tools import get_cold_script

        result = get_cold_script("higher_ed")

        assert result is not None
        assert "pattern_interrupt" in result
        assert "value_hook" in result

    def test_returns_none_for_invalid_vertical(self):
        """Test returning None for invalid vertical."""
        from app.services.langgraph.tools.script_tools import get_cold_script

        result = get_cold_script("invalid_vertical")

        assert result is None

    def test_includes_objection_pivots(self):
        """Test that script includes objection pivots."""
        from app.services.langgraph.tools.script_tools import get_cold_script

        result = get_cold_script("corporate")

        assert result is not None
        assert "objection_pivots" in result
        assert isinstance(result["objection_pivots"], list)


class TestGetPersonaProfile:
    """Tests for get_persona_profile tool."""

    def test_returns_profile_for_valid_persona(self):
        """Test returning profile for valid persona ID."""
        from app.services.langgraph.tools.script_tools import get_persona_profile

        result = get_persona_profile("av_director")

        assert result is not None
        assert result["id"] == "av_director"
        assert "pain_points" in result
        assert "objections" in result

    def test_returns_none_for_invalid_persona(self):
        """Test returning None for invalid persona."""
        from app.services.langgraph.tools.script_tools import get_persona_profile

        result = get_persona_profile("invalid_xyz")

        assert result is None

    def test_profile_has_discovery_questions(self):
        """Test that profile includes discovery questions."""
        from app.services.langgraph.tools.script_tools import get_persona_profile

        result = get_persona_profile("ld_director")

        assert result is not None
        assert "discovery_questions" in result
        assert isinstance(result["discovery_questions"], list)
        assert len(result["discovery_questions"]) > 0

    def test_profile_has_hot_buttons(self):
        """Test that profile includes hot buttons."""
        from app.services.langgraph.tools.script_tools import get_persona_profile

        result = get_persona_profile("technical_director")

        assert result is not None
        assert "hot_buttons" in result
        assert isinstance(result["hot_buttons"], list)

    def test_profile_has_buying_signals(self):
        """Test that profile includes buying signals."""
        from app.services.langgraph.tools.script_tools import get_persona_profile

        result = get_persona_profile("av_director")

        assert result is not None
        assert "buying_signals" in result
        assert "high" in result["buying_signals"]
        assert "medium" in result["buying_signals"]
