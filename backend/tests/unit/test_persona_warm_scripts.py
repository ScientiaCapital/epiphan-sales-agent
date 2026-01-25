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
        """Should have at least 5 persona scripts (one per priority persona)."""
        # Currently 7 scripts: 5 priority + Law Firm IT + Technical Director
        assert len(PERSONA_WARM_SCRIPTS) >= 5

    def test_total_trigger_variations(self):
        """Each persona should have 4 trigger variations."""
        total_variations = sum(
            len(script.trigger_variations) for script in PERSONA_WARM_SCRIPTS
        )
        # Each persona has 4 triggers, so total = num_personas * 4
        assert total_variations == len(PERSONA_WARM_SCRIPTS) * 4


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
# Corp Comms Director Script Tests
# ============================================================================


class TestCorpCommsDirectorWarmScript:
    """Tests for Corp Comms Director (Corporate) warm scripts."""

    @pytest.fixture
    def corp_comms_script(self) -> PersonaWarmScript:
        """Get the Corp Comms Director warm script."""
        script = get_persona_warm_script(PersonaType.CORP_COMMS_DIRECTOR)
        assert script is not None, "Corp Comms Director script not found"
        return script

    def test_corp_comms_primary_pain(self, corp_comms_script: PersonaWarmScript):
        """Should mention 'CEO events' or 'zero tolerance for failures'."""
        primary_pain_lower = corp_comms_script.primary_pain.lower()
        assert any(
            phrase in primary_pain_lower
            for phrase in ["ceo", "zero tolerance", "failure"]
        ), f"Expected 'ceo', 'zero tolerance', or 'failure' in primary_pain: {corp_comms_script.primary_pain}"

    def test_corp_comms_reference_story(self, corp_comms_script: PersonaWarmScript):
        """Should mention 'OpenAI' or 'Freeman'."""
        reference_story = corp_comms_script.reference_story
        assert any(
            name in reference_story
            for name in ["OpenAI", "Freeman"]
        ), f"Expected 'OpenAI' or 'Freeman' in reference_story: {reference_story}"

    def test_corp_comms_value_proposition(self, corp_comms_script: PersonaWarmScript):
        """Should focus on broadcast quality without production team."""
        value_prop_lower = corp_comms_script.value_proposition.lower()
        assert any(
            phrase in value_prop_lower
            for phrase in ["broadcast", "production", "quality"]
        ), f"Expected 'broadcast', 'production', or 'quality' in value_proposition: {corp_comms_script.value_proposition}"


class TestEHSManagerWarmScript:
    """Tests for EHS Manager (Industrial) warm scripts."""

    @pytest.fixture
    def ehs_script(self) -> PersonaWarmScript:
        """Get the EHS Manager warm script."""
        script = get_persona_warm_script(PersonaType.EHS_MANAGER)
        assert script is not None, "EHS Manager script not found"
        return script

    def test_ehs_manager_primary_pain(self, ehs_script: PersonaWarmScript):
        """Should mention 'OSHA', 'compliance', or 'documentation'."""
        primary_pain_lower = ehs_script.primary_pain.lower()
        assert any(
            phrase in primary_pain_lower
            for phrase in ["osha", "compliance", "documentation", "training"]
        ), f"Expected 'osha', 'compliance', 'documentation', or 'training' in primary_pain: {ehs_script.primary_pain}"

    def test_ehs_manager_reference_story(self, ehs_script: PersonaWarmScript):
        """Should mention OSHA violation costs."""
        reference_story = ehs_script.reference_story
        assert any(
            amount in reference_story
            for amount in ["$100K", "$500K", "OSHA", "violation"]
        ), f"Expected '$100K', '$500K', 'OSHA', or 'violation' in reference_story: {reference_story}"

    def test_ehs_manager_value_proposition(self, ehs_script: PersonaWarmScript):
        """Should focus on video proof or compliance documentation."""
        value_prop_lower = ehs_script.value_proposition.lower()
        assert any(
            phrase in value_prop_lower
            for phrase in ["proof", "compliance", "documentation", "osha"]
        ), f"Expected 'proof', 'compliance', 'documentation', or 'osha' in value_proposition: {ehs_script.value_proposition}"


class TestLawFirmITWarmScript:
    """Tests for Law Firm IT Director (Legal) warm scripts."""

    @pytest.fixture
    def law_firm_script(self) -> PersonaWarmScript:
        """Get the Law Firm IT warm script."""
        script = get_persona_warm_script(PersonaType.LAW_FIRM_IT)
        assert script is not None, "Law Firm IT script not found"
        return script

    def test_law_firm_it_primary_pain(self, law_firm_script: PersonaWarmScript):
        """Should mention 'confidential', 'discovery', or 'cloud risk'."""
        primary_pain_lower = law_firm_script.primary_pain.lower()
        assert any(
            phrase in primary_pain_lower
            for phrase in ["confidential", "discovery", "cloud", "risk"]
        ), f"Expected 'confidential', 'discovery', 'cloud', or 'risk' in primary_pain: {law_firm_script.primary_pain}"

    def test_law_firm_it_reference_story(self, law_firm_script: PersonaWarmScript):
        """Should mention local recording or server storage."""
        reference_story_lower = law_firm_script.reference_story.lower()
        assert any(
            phrase in reference_story_lower
            for phrase in ["local", "server", "cloud", "discovery"]
        ), f"Expected 'local', 'server', 'cloud', or 'discovery' in reference_story: {law_firm_script.reference_story}"

    def test_law_firm_it_value_proposition(self, law_firm_script: PersonaWarmScript):
        """Should focus on local recording or eliminating cloud exposure."""
        value_prop_lower = law_firm_script.value_proposition.lower()
        assert any(
            phrase in value_prop_lower
            for phrase in ["local", "cloud", "deposition", "server"]
        ), f"Expected 'local', 'cloud', 'deposition', or 'server' in value_proposition: {law_firm_script.value_proposition}"


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

    def test_all_personas_have_warm_scripts(self):
        """All 8 personas should now have warm scripts."""
        # All 8 personas are now implemented
        all_personas = [
            PersonaType.AV_DIRECTOR,
            PersonaType.LD_DIRECTOR,
            PersonaType.TECHNICAL_DIRECTOR,
            PersonaType.SIMULATION_DIRECTOR,
            PersonaType.COURT_ADMINISTRATOR,
            PersonaType.CORP_COMMS_DIRECTOR,
            PersonaType.EHS_MANAGER,
            PersonaType.LAW_FIRM_IT,
        ]
        for persona in all_personas:
            script = get_persona_warm_script(persona)
            assert script is not None, f"{persona.value} should have a warm script"

    def test_get_warm_script_for_persona_trigger_found(self):
        """Should return trigger variation for valid combo."""
        variation = get_warm_script_for_persona_trigger(
            PersonaType.AV_DIRECTOR,
            TriggerType.CONTENT_DOWNLOAD
        )
        assert variation is not None
        assert variation.trigger_type == TriggerType.CONTENT_DOWNLOAD

    def test_get_warm_script_for_persona_trigger_not_found(self):
        """Should return None for trigger type without warm scripts."""
        # TRADE_SHOW trigger doesn't have persona-specific warm scripts
        variation = get_warm_script_for_persona_trigger(
            PersonaType.AV_DIRECTOR,
            TriggerType.TRADE_SHOW
        )
        assert variation is None
