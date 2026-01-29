"""Tests for LangGraph state schemas."""

from typing import get_type_hints


class TestCompetitorIntelState:
    """Tests for CompetitorIntelState."""

    def test_state_has_required_fields(self):
        """Test that state has all required fields."""
        from app.services.langgraph.states import CompetitorIntelState

        hints = get_type_hints(CompetitorIntelState)

        assert "competitor_name" in hints
        assert "context" in hints
        assert "query_type" in hints
        assert "battlecard" in hints
        assert "response" in hints
        assert "proof_points" in hints
        assert "follow_up_question" in hints

    def test_state_can_be_instantiated(self):
        """Test that state can be created with valid data."""
        from app.services.langgraph.states import CompetitorIntelState

        state: CompetitorIntelState = {
            "competitor_name": "blackmagic",
            "context": "They said ATEM is cheaper",
            "query_type": "claim",
            "battlecard": None,
            "relevant_differentiators": [],
            "response": "",
            "proof_points": [],
            "follow_up_question": None,
        }

        assert state["competitor_name"] == "blackmagic"
        assert state["query_type"] == "claim"


class TestScriptSelectionState:
    """Tests for ScriptSelectionState."""

    def test_state_has_required_fields(self):
        """Test that state has all required fields."""
        from app.services.langgraph.states import ScriptSelectionState

        hints = get_type_hints(ScriptSelectionState)

        assert "lead" in hints
        assert "persona_match" in hints
        assert "trigger" in hints
        assert "call_type" in hints
        assert "personalized_script" in hints
        assert "talking_points" in hints
        assert "objection_responses" in hints

    def test_state_can_be_instantiated(self):
        """Test that state can be created with lead data."""
        from app.data.lead_schemas import Lead
        from app.services.langgraph.states import ScriptSelectionState

        lead = Lead(
            hubspot_id="123",
            email="test@example.com",
            first_name="John",
        )

        state: ScriptSelectionState = {
            "lead": lead,
            "persona_match": "av_director",
            "trigger": "demo_request",
            "call_type": "warm",
            "base_script": None,
            "lead_context": None,
            "persona_profile": None,
            "personalized_script": "",
            "talking_points": [],
            "objection_responses": [],
        }

        assert state["lead"].first_name == "John"
        assert state["call_type"] == "warm"


class TestLeadResearchState:
    """Tests for LeadResearchState."""

    def test_state_has_required_fields(self):
        """Test that state has all required fields."""
        from app.services.langgraph.states import LeadResearchState

        hints = get_type_hints(LeadResearchState)

        assert "lead" in hints
        assert "research_depth" in hints
        assert "apollo_data" in hints
        assert "research_brief" in hints
        assert "talking_points" in hints

    def test_state_can_be_instantiated(self):
        """Test that state can be created with valid data."""
        from app.data.lead_schemas import Lead
        from app.services.langgraph.states import LeadResearchState

        lead = Lead(
            hubspot_id="456",
            email="sarah@university.edu",
        )

        state: LeadResearchState = {
            "lead": lead,
            "research_depth": "deep",
            "apollo_data": None,
            "news_articles": [],
            "linkedin_context": None,
            "research_brief": None,
            "talking_points": [],
            "risk_factors": [],
        }

        assert state["research_depth"] == "deep"


class TestEmailPersonalizationState:
    """Tests for EmailPersonalizationState."""

    def test_state_has_required_fields(self):
        """Test that state has all required fields."""
        from app.services.langgraph.states import EmailPersonalizationState

        hints = get_type_hints(EmailPersonalizationState)

        assert "lead" in hints
        assert "sequence_step" in hints
        assert "email_type" in hints
        assert "subject_line" in hints
        assert "email_body" in hints

    def test_state_can_be_instantiated(self):
        """Test that state can be created with valid data."""
        from app.data.lead_schemas import Lead
        from app.services.langgraph.states import EmailPersonalizationState

        lead = Lead(
            hubspot_id="789",
            email="prospect@company.com",
        )

        state: EmailPersonalizationState = {
            "lead": lead,
            "research_brief": None,
            "persona": None,
            "sequence_step": 1,
            "email_type": "pattern_interrupt",
            "pain_points": [],
            "personalization_hooks": [],
            "subject_line": "",
            "email_body": "",
            "follow_up_note": None,
        }

        assert state["sequence_step"] == 1
        assert state["email_type"] == "pattern_interrupt"


class TestResearchBrief:
    """Tests for ResearchBrief TypedDict."""

    def test_brief_has_required_fields(self):
        """Test that ResearchBrief has all fields."""
        from app.services.langgraph.states import ResearchBrief

        hints = get_type_hints(ResearchBrief)

        assert "company_overview" in hints
        assert "recent_news" in hints
        assert "talking_points" in hints
        assert "risk_factors" in hints
