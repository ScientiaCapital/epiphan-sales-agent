"""
Tests for PersonaWarmScript schemas.

TDD: These tests are written FIRST to define the expected behavior
of the persona-specific warm lead scripts schemas.
"""

import pytest
from pydantic import ValidationError

from app.data.schemas import (
    PersonaObjectionResponse,
    PersonaTriggerVariation,
    PersonaType,
    PersonaWarmContext,
    PersonaWarmScript,
    TriggerType,
)


class TestPersonaObjectionResponse:
    """Tests for persona-specific objection response schema."""

    def test_create_valid_objection_response(self):
        """Should create objection response with all required fields."""
        objection = PersonaObjectionResponse(
            objection="We're standardized on another vendor",
            response="Pearl integrates with your existing ecosystem. It adds capability, doesn't replace.",
            persona_context="For AV Directors, emphasize fleet management compatibility",
        )
        assert objection.objection == "We're standardized on another vendor"
        assert objection.response.startswith("Pearl integrates")
        assert "AV Directors" in objection.persona_context

    def test_objection_response_without_persona_context(self):
        """Should allow optional persona_context field."""
        objection = PersonaObjectionResponse(
            objection="Too expensive",
            response="Compare 5-year TCO with no recurring fees.",
        )
        assert objection.objection == "Too expensive"
        assert objection.persona_context is None


class TestPersonaWarmContext:
    """Tests for persona warm call context cues schema."""

    def test_create_valid_context(self):
        """Should create context with all cue lists."""
        context = PersonaWarmContext(
            what_to_listen_for=[
                "Mentions team size relative to room count",
                "Talks about remote campus locations",
            ],
            buying_signals=[
                "Construction project coming up",
                "Recent equipment failure mentioned",
            ],
            red_flags=[
                "Just took this role - no budget authority",
                "Locked into multi-year competitor contract",
            ],
        )
        assert len(context.what_to_listen_for) == 2
        assert len(context.buying_signals) == 2
        assert len(context.red_flags) == 2

    def test_context_with_empty_lists(self):
        """Should allow empty lists for any cue category."""
        context = PersonaWarmContext(
            what_to_listen_for=[],
            buying_signals=["At least one signal"],
            red_flags=[],
        )
        assert context.what_to_listen_for == []
        assert len(context.buying_signals) == 1


class TestPersonaTriggerVariation:
    """Tests for trigger-specific script variation schema."""

    def test_create_valid_trigger_variation(self):
        """Should create trigger variation with ACQP framework."""
        variation = PersonaTriggerVariation(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            acknowledge="Hi [Name], this is Tim from Epiphan. Thanks for downloading our case study.",
            connect="Most AV directors who download that are dealing with the 'too many rooms, too few people' challenge.",
            qualify="How many rooms are you managing, and how big is your support team?",
            propose="NC State manages 300+ rooms with a team of 3. Would a quick look at how they do it be useful?",
            discovery_questions=[
                "What's your biggest reliability pain point right now?",
                "Can you troubleshoot remotely, or do you have to be on-site?",
            ],
            what_to_listen_for=[
                "Team size relative to room count",
                "Mentions of remote locations",
            ],
        )
        assert variation.trigger_type == TriggerType.CONTENT_DOWNLOAD
        assert "[Name]" in variation.acknowledge
        assert "300+" in variation.propose
        assert len(variation.discovery_questions) == 2

    def test_trigger_variation_requires_all_acqp_fields(self):
        """Should require acknowledge, connect, qualify, propose fields."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaTriggerVariation(
                trigger_type=TriggerType.DEMO_REQUEST,
                acknowledge="Hi [Name]...",
                # Missing connect, qualify, propose
            )
        errors = exc_info.value.errors()
        missing_fields = {e["loc"][0] for e in errors}
        assert "connect" in missing_fields
        assert "qualify" in missing_fields
        assert "propose" in missing_fields

    def test_all_trigger_types_valid(self):
        """Should accept all 4 main trigger types."""
        triggers = [
            TriggerType.CONTENT_DOWNLOAD,
            TriggerType.WEBINAR_ATTENDED,
            TriggerType.DEMO_REQUEST,
            TriggerType.PRICING_PAGE,
        ]
        for trigger in triggers:
            variation = PersonaTriggerVariation(
                trigger_type=trigger,
                acknowledge=f"Acknowledge for {trigger.value}",
                connect=f"Connect for {trigger.value}",
                qualify=f"Qualify for {trigger.value}",
                propose=f"Propose for {trigger.value}",
                discovery_questions=[],
                what_to_listen_for=[],
            )
            assert variation.trigger_type == trigger


class TestPersonaWarmScript:
    """Tests for the main persona warm script schema."""

    @pytest.fixture
    def sample_trigger_variation(self) -> PersonaTriggerVariation:
        """Create a sample trigger variation for testing."""
        return PersonaTriggerVariation(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            acknowledge="Hi [Name], Tim from Epiphan.",
            connect="Most AV directors downloading this face the 'too many rooms' challenge.",
            qualify="How many rooms and what's your team size?",
            propose="NC State manages 300+ rooms with 3 people. Want to see how?",
            discovery_questions=["What's your biggest pain point?"],
            what_to_listen_for=["Team size mentions"],
        )

    @pytest.fixture
    def sample_objection(self) -> PersonaObjectionResponse:
        """Create a sample objection for testing."""
        return PersonaObjectionResponse(
            objection="We're standardized on Crestron",
            response="Pearl integrates with Crestron control systems.",
        )

    @pytest.fixture
    def sample_context(self) -> PersonaWarmContext:
        """Create a sample context for testing."""
        return PersonaWarmContext(
            what_to_listen_for=["Team understaffing mentions"],
            buying_signals=["Construction project mentioned"],
            red_flags=["New in role, no budget"],
        )

    def test_create_valid_persona_warm_script(
        self,
        sample_trigger_variation: PersonaTriggerVariation,
        sample_objection: PersonaObjectionResponse,
        sample_context: PersonaWarmContext,
    ):
        """Should create complete persona warm script."""
        script = PersonaWarmScript(
            id="av_director_warm",
            persona_type=PersonaType.AV_DIRECTOR,
            persona_title="AV Director",
            primary_pain="Too many rooms, too few people",
            value_proposition="Remote fleet management for understaffed AV teams",
            reference_story="NC State: 300+ rooms, team of 3",
            trigger_variations=[sample_trigger_variation],
            objections=[sample_objection],
            context_cues=sample_context,
        )
        assert script.id == "av_director_warm"
        assert script.persona_type == PersonaType.AV_DIRECTOR
        assert "300+ rooms" in script.reference_story
        assert len(script.trigger_variations) == 1
        assert len(script.objections) == 1

    def test_persona_warm_script_multiple_triggers(
        self,
        sample_objection: PersonaObjectionResponse,
        sample_context: PersonaWarmContext,
    ):
        """Should support multiple trigger variations per persona."""
        triggers = [
            PersonaTriggerVariation(
                trigger_type=TriggerType.CONTENT_DOWNLOAD,
                acknowledge="Thanks for the download.",
                connect="Common challenge...",
                qualify="How many rooms?",
                propose="Want to see NC State?",
                discovery_questions=[],
                what_to_listen_for=[],
            ),
            PersonaTriggerVariation(
                trigger_type=TriggerType.DEMO_REQUEST,
                acknowledge="Got your demo request!",
                connect="What's driving the interest?",
                qualify="Specific project or building business case?",
                propose="Let's get you on the calendar.",
                discovery_questions=[],
                what_to_listen_for=[],
            ),
        ]
        script = PersonaWarmScript(
            id="av_director_warm",
            persona_type=PersonaType.AV_DIRECTOR,
            persona_title="AV Director",
            primary_pain="Too many rooms, too few people",
            value_proposition="Remote fleet management",
            reference_story="NC State: 300+ rooms, team of 3",
            trigger_variations=triggers,
            objections=[sample_objection],
            context_cues=sample_context,
        )
        assert len(script.trigger_variations) == 2
        trigger_types = [t.trigger_type for t in script.trigger_variations]
        assert TriggerType.CONTENT_DOWNLOAD in trigger_types
        assert TriggerType.DEMO_REQUEST in trigger_types

    def test_persona_warm_script_requires_persona_type(
        self,
        sample_trigger_variation: PersonaTriggerVariation,
        sample_context: PersonaWarmContext,
    ):
        """Should require valid persona_type."""
        with pytest.raises(ValidationError):
            PersonaWarmScript(
                id="invalid",
                persona_type="not_a_persona",  # Invalid enum value
                persona_title="Test",
                primary_pain="Pain",
                value_proposition="Value",
                reference_story="Story",
                trigger_variations=[sample_trigger_variation],
                objections=[],
                context_cues=sample_context,
            )

    def test_all_personas_valid_for_warm_scripts(self):
        """Should accept all 5 priority personas."""
        personas = [
            PersonaType.AV_DIRECTOR,
            PersonaType.LD_DIRECTOR,
            PersonaType.TECHNICAL_DIRECTOR,
            PersonaType.SIMULATION_DIRECTOR,
            PersonaType.COURT_ADMINISTRATOR,
        ]
        context = PersonaWarmContext(
            what_to_listen_for=[],
            buying_signals=[],
            red_flags=[],
        )
        trigger = PersonaTriggerVariation(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            acknowledge="Ack",
            connect="Connect",
            qualify="Qualify",
            propose="Propose",
            discovery_questions=[],
            what_to_listen_for=[],
        )
        for persona in personas:
            script = PersonaWarmScript(
                id=f"{persona.value}_warm",
                persona_type=persona,
                persona_title=persona.value.replace("_", " ").title(),
                primary_pain="Primary pain",
                value_proposition="Value prop",
                reference_story="Reference story",
                trigger_variations=[trigger],
                objections=[],
                context_cues=context,
            )
            assert script.persona_type == persona
