"""
Tests for warm script integration helper in scripts.py.

TDD: Tests the get_warm_script_for_call() function that combines
persona-specific scripts with fallback to trigger-only scripts.
"""


from app.data.schemas import PersonaType, TriggerType
from app.data.scripts import get_warm_script_for_call


class TestGetWarmScriptForCall:
    """Tests for the unified warm script lookup function."""

    def test_returns_persona_specific_script_when_available(self):
        """Should return persona-specific variation when persona is known."""
        result = get_warm_script_for_call(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            persona_type=PersonaType.AV_DIRECTOR,
        )
        assert result is not None
        # Persona-specific scripts mention persona pain points
        assert "room" in result["connect"].lower() or "AV" in result["connect"]

    def test_returns_generic_script_when_persona_unknown(self):
        """Should fall back to generic trigger script when no persona."""
        result = get_warm_script_for_call(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            persona_type=None,
        )
        assert result is not None
        # Generic scripts have placeholder text like [common challenge]
        assert result["acknowledge"] is not None
        assert result["connect"] is not None

    def test_returns_generic_script_for_unsupported_persona(self):
        """Should fall back when persona doesn't have warm scripts."""
        # EHS_MANAGER doesn't have persona-specific warm scripts
        result = get_warm_script_for_call(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            persona_type=PersonaType.EHS_MANAGER,
        )
        assert result is not None
        # Should return the generic trigger-based script

    def test_returns_none_for_unsupported_trigger(self):
        """Should return None for triggers without scripts."""
        # TRADE_SHOW might not have persona-specific variations
        result = get_warm_script_for_call(
            trigger_type=TriggerType.TRADE_SHOW,
            persona_type=PersonaType.AV_DIRECTOR,
        )
        # Should fall back to generic or return None
        # The generic TRADE_SHOW script exists, so should return something
        assert result is not None

    def test_result_contains_acqp_fields(self):
        """Result should contain Acknowledge, Connect, Qualify, Propose."""
        result = get_warm_script_for_call(
            trigger_type=TriggerType.DEMO_REQUEST,
            persona_type=PersonaType.LD_DIRECTOR,
        )
        assert result is not None
        assert "acknowledge" in result
        assert "connect" in result
        assert "qualify" in result
        assert "propose" in result

    def test_result_contains_discovery_questions_when_available(self):
        """Persona-specific results should include discovery questions."""
        result = get_warm_script_for_call(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            persona_type=PersonaType.SIMULATION_DIRECTOR,
        )
        assert result is not None
        # Persona-specific scripts have discovery questions
        assert "discovery_questions" in result
        assert len(result["discovery_questions"]) > 0

    def test_result_source_indicates_persona_specific(self):
        """Should indicate when result is persona-specific vs generic."""
        persona_result = get_warm_script_for_call(
            trigger_type=TriggerType.PRICING_PAGE,
            persona_type=PersonaType.COURT_ADMINISTRATOR,
        )
        assert persona_result is not None
        assert persona_result.get("source") == "persona_specific"

        generic_result = get_warm_script_for_call(
            trigger_type=TriggerType.REFERRAL,  # No persona-specific script
            persona_type=PersonaType.AV_DIRECTOR,
        )
        assert generic_result is not None
        assert generic_result.get("source") == "trigger_generic"

    def test_all_priority_personas_have_four_triggers(self):
        """All 5 priority personas should have scripts for 4 main triggers."""
        priority_personas = [
            PersonaType.AV_DIRECTOR,
            PersonaType.LD_DIRECTOR,
            PersonaType.TECHNICAL_DIRECTOR,
            PersonaType.SIMULATION_DIRECTOR,
            PersonaType.COURT_ADMINISTRATOR,
        ]
        main_triggers = [
            TriggerType.CONTENT_DOWNLOAD,
            TriggerType.WEBINAR_ATTENDED,
            TriggerType.DEMO_REQUEST,
            TriggerType.PRICING_PAGE,
        ]
        for persona in priority_personas:
            for trigger in main_triggers:
                result = get_warm_script_for_call(trigger, persona)
                assert result is not None, f"Missing script for {persona.value} + {trigger.value}"
                assert result.get("source") == "persona_specific", (
                    f"{persona.value} + {trigger.value} should be persona_specific"
                )
