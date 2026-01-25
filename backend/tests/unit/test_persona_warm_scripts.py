"""
Tests for persona-specific warm lead scripts data.

TDD: These tests define what the persona warm scripts data should contain
before we implement the actual scripts in persona_warm_scripts.py.
"""

import pytest

from app.data.persona_warm_scripts import (
    PERSONA_WARM_SCRIPTS,
    get_persona_warm_script,
    get_warm_script_for_persona_trigger,
)
from app.data.schemas import (
    PersonaType,
    PersonaWarmScript,
    TriggerType,
)

# ============================================================================
# Data Completeness Tests
# ============================================================================


class TestPersonaWarmScriptsCompleteness:
    """Tests to ensure all required personas and triggers are covered."""

    REQUIRED_PERSONAS = [
        PersonaType.AV_DIRECTOR,
        PersonaType.LD_DIRECTOR,
        PersonaType.TECHNICAL_DIRECTOR,
        PersonaType.SIMULATION_DIRECTOR,
        PersonaType.COURT_ADMINISTRATOR,
    ]

    REQUIRED_TRIGGERS = [
        TriggerType.CONTENT_DOWNLOAD,
        TriggerType.WEBINAR_ATTENDED,
        TriggerType.DEMO_REQUEST,
        TriggerType.PRICING_PAGE,
    ]

    def test_all_required_personas_have_scripts(self):
        """Should have warm scripts for all 5 priority personas."""
        persona_types_in_scripts = {s.persona_type for s in PERSONA_WARM_SCRIPTS}
        for persona in self.REQUIRED_PERSONAS:
            assert persona in persona_types_in_scripts, (
                f"Missing warm script for {persona.value}"
            )

    def test_each_persona_has_four_trigger_variations(self):
        """Each persona should have scripts for all 4 main triggers."""
        for script in PERSONA_WARM_SCRIPTS:
            trigger_types = {v.trigger_type for v in script.trigger_variations}
            for trigger in self.REQUIRED_TRIGGERS:
                assert trigger in trigger_types, (
                    f"{script.persona_type.value} missing trigger variation for {trigger.value}"
                )

    def test_total_script_count(self):
        """Should have exactly 5 persona scripts (one per persona)."""
        assert len(PERSONA_WARM_SCRIPTS) == 5

    def test_total_trigger_variations(self):
        """Should have exactly 20 trigger variations (5 personas × 4 triggers)."""
        total_variations = sum(
            len(script.trigger_variations) for script in PERSONA_WARM_SCRIPTS
        )
        assert total_variations == 20


# ============================================================================
# AV Director Script Tests
# ============================================================================


class TestAVDirectorWarmScript:
    """Tests for AV Director persona warm scripts."""

    @pytest.fixture
    def av_script(self) -> PersonaWarmScript:
        """Get the AV Director warm script."""
        script = get_persona_warm_script(PersonaType.AV_DIRECTOR)
        assert script is not None, "AV Director script not found"
        return script

    def test_av_director_primary_pain(self, av_script: PersonaWarmScript):
        """Should address the 'too many rooms, too few people' pain."""
        assert "room" in av_script.primary_pain.lower()
        assert any(
            word in av_script.primary_pain.lower()
            for word in ["team", "people", "staff", "few"]
        )

    def test_av_director_reference_story(self, av_script: PersonaWarmScript):
        """Should reference NC State (300+ rooms, team of 3)."""
        assert "NC State" in av_script.reference_story or "nc state" in av_script.reference_story.lower()
        assert "300" in av_script.reference_story

    def test_av_director_content_download_variation(self, av_script: PersonaWarmScript):
        """Content download script should acknowledge the download and connect to remote management pain."""
        variation = next(
            (v for v in av_script.trigger_variations
             if v.trigger_type == TriggerType.CONTENT_DOWNLOAD),
            None
        )
        assert variation is not None
        # Acknowledge should reference the content
        assert "[" in variation.acknowledge  # Template variable
        # Connect should mention the pain
        assert any(
            word in variation.connect.lower()
            for word in ["room", "remote", "manage", "troubleshoot"]
        )

    def test_av_director_demo_request_variation(self, av_script: PersonaWarmScript):
        """Demo request script should have urgency (highest intent trigger)."""
        variation = next(
            (v for v in av_script.trigger_variations
             if v.trigger_type == TriggerType.DEMO_REQUEST),
            None
        )
        assert variation is not None
        # Propose should offer to schedule
        assert any(
            word in variation.propose.lower()
            for word in ["calendar", "schedule", "time", "demo"]
        )

    def test_av_director_has_objections(self, av_script: PersonaWarmScript):
        """Should have persona-specific objections."""
        assert len(av_script.objections) >= 2
        # Should include common AV objection about existing vendors
        objection_texts = [o.objection.lower() for o in av_script.objections]
        assert any(
            "standard" in obj or "vendor" in obj or "crestron" in obj.lower()
            for obj in objection_texts
        )


# ============================================================================
# L&D Director Script Tests
# ============================================================================


class TestLDDirectorWarmScript:
    """Tests for L&D Director persona warm scripts."""

    @pytest.fixture
    def ld_script(self) -> PersonaWarmScript:
        """Get the L&D Director warm script."""
        script = get_persona_warm_script(PersonaType.LD_DIRECTOR)
        assert script is not None, "L&D Director script not found"
        return script

    def test_ld_director_primary_pain(self, ld_script: PersonaWarmScript):
        """Should address content creation scaling pain."""
        assert any(
            word in ld_script.primary_pain.lower()
            for word in ["scale", "content", "production", "cost"]
        )

    def test_ld_director_reference_story(self, ld_script: PersonaWarmScript):
        """Should reference OpenAI ('workhorse of streams')."""
        assert "OpenAI" in ld_script.reference_story or "openai" in ld_script.reference_story.lower()

    def test_ld_director_value_proposition(self, ld_script: PersonaWarmScript):
        """Should focus on self-service content creation."""
        assert any(
            word in ld_script.value_proposition.lower()
            for word in ["self-service", "production", "scale", "team"]
        )


# ============================================================================
# Technical Director Script Tests
# ============================================================================


class TestTechnicalDirectorWarmScript:
    """Tests for Technical Director (HoW/Live Events) warm scripts."""

    @pytest.fixture
    def tech_script(self) -> PersonaWarmScript:
        """Get the Technical Director warm script."""
        script = get_persona_warm_script(PersonaType.TECHNICAL_DIRECTOR)
        assert script is not None, "Technical Director script not found"
        return script

    def test_technical_director_primary_pain(self, tech_script: PersonaWarmScript):
        """Should address reliability/Sunday morning anxiety."""
        assert any(
            word in tech_script.primary_pain.lower()
            for word in ["fail", "sunday", "reliable", "crash", "volunteer"]
        )

    def test_technical_director_reference_story(self, tech_script: PersonaWarmScript):
        """Should reference 5-minute volunteer training."""
        assert any(
            phrase in tech_script.reference_story.lower()
            for phrase in ["5-minute", "5 minute", "volunteer", "training"]
        )


# ============================================================================
# Simulation Director Script Tests
# ============================================================================


class TestSimulationDirectorWarmScript:
    """Tests for Simulation Director (Healthcare) warm scripts."""

    @pytest.fixture
    def sim_script(self) -> PersonaWarmScript:
        """Get the Simulation Director warm script."""
        script = get_persona_warm_script(PersonaType.SIMULATION_DIRECTOR)
        assert script is not None, "Simulation Director script not found"
        return script

    def test_simulation_director_primary_pain(self, sim_script: PersonaWarmScript):
        """Should address HIPAA compliance."""
        assert any(
            word in sim_script.primary_pain.lower()
            for word in ["hipaa", "compliance", "accreditation", "phi"]
        )

    def test_simulation_director_value_proposition(self, sim_script: PersonaWarmScript):
        """Should emphasize local recording (no cloud)."""
        assert any(
            word in sim_script.value_proposition.lower()
            for word in ["local", "network", "cloud", "phi"]
        )


# ============================================================================
# Court Administrator Script Tests
# ============================================================================


class TestCourtAdministratorWarmScript:
    """Tests for Court Administrator (Government) warm scripts."""

    @pytest.fixture
    def court_script(self) -> PersonaWarmScript:
        """Get the Court Administrator warm script."""
        script = get_persona_warm_script(PersonaType.COURT_ADMINISTRATOR)
        assert script is not None, "Court Administrator script not found"
        return script

    def test_court_admin_primary_pain(self, court_script: PersonaWarmScript):
        """Should address court reporter shortage."""
        assert any(
            word in court_script.primary_pain.lower()
            for word in ["reporter", "shortage", "transcript", "record"]
        )

    def test_court_admin_reference_story(self, court_script: PersonaWarmScript):
        """Should reference 33 states or 1.78M hearings."""
        assert any(
            stat in court_script.reference_story
            for stat in ["33", "1.78", "states"]
        )


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestHelperFunctions:
    """Tests for lookup helper functions."""

    def test_get_persona_warm_script_found(self):
        """Should return script for valid persona."""
        script = get_persona_warm_script(PersonaType.AV_DIRECTOR)
        assert script is not None
        assert script.persona_type == PersonaType.AV_DIRECTOR

    def test_get_persona_warm_script_not_found(self):
        """Should return None for persona without warm script."""
        # EHS_MANAGER is not in our 5 priority personas
        script = get_persona_warm_script(PersonaType.EHS_MANAGER)
        assert script is None

    def test_get_warm_script_for_persona_trigger_found(self):
        """Should return trigger variation for valid combo."""
        variation = get_warm_script_for_persona_trigger(
            PersonaType.AV_DIRECTOR,
            TriggerType.CONTENT_DOWNLOAD
        )
        assert variation is not None
        assert variation.trigger_type == TriggerType.CONTENT_DOWNLOAD

    def test_get_warm_script_for_persona_trigger_not_found(self):
        """Should return None for invalid persona/trigger combo."""
        # EHS_MANAGER doesn't have warm scripts
        variation = get_warm_script_for_persona_trigger(
            PersonaType.EHS_MANAGER,
            TriggerType.CONTENT_DOWNLOAD
        )
        assert variation is None
