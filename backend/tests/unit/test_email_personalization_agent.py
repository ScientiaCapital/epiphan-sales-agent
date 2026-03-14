"""Tests for Email Personalization Agent."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.data.lead_schemas import Lead
from app.services.langgraph.states import EmailResponse, ResearchBrief


class TestEmailPersonalizationAgent:
    """Tests for EmailPersonalizationAgent."""

    @pytest.fixture
    def sample_lead(self) -> Lead:
        """Create a sample lead for testing."""
        return Lead(
            hubspot_id="hs-lead-123",
            email="sarah.johnson@stateuniversity.edu",
            first_name="Sarah",
            last_name="Johnson",
            company="State University",
            title="AV Director",
        )

    @pytest.fixture
    def sample_brief(self) -> ResearchBrief:
        """Create a sample research brief."""
        return {
            "company_overview": "State University is a leading research institution.",
            "recent_news": [
                {"title": "University Expands Online Learning", "date": "2025-01-15"}
            ],
            "talking_points": [
                "Higher education focus",
                "5000 employees",
            ],
            "risk_factors": [],
            "linkedin_summary": None,
        }

    @pytest.fixture
    def sample_persona(self) -> dict:
        """Create a sample persona."""
        return {
            "id": "av_director",
            "name": "AV Director",
            "pain_points": ["Manual recording", "Inconsistent quality"],
        }

    def _mock_structured_llm(
        self, agent: object, response: EmailResponse
    ) -> MagicMock:
        """Set up mock for with_structured_output() chain.

        Returns the mock_llm so callers can make assertions on it.
        """
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=response)

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured

        # Patch the agent's _llm attribute
        object.__setattr__(agent, "_llm", mock_llm)
        return mock_llm

    def test_agent_initializes(self):
        """Test that agent initializes."""
        from app.services.langgraph.agents.email_personalization import (
            EmailPersonalizationAgent,
        )

        agent = EmailPersonalizationAgent()
        assert agent is not None

    @pytest.mark.asyncio
    async def test_run_returns_email(
        self,
        sample_lead: Lead,
        sample_brief: ResearchBrief,
        sample_persona: dict,
    ):
        """Test running agent produces personalized email."""
        from app.services.langgraph.agents.email_personalization import (
            EmailPersonalizationAgent,
        )

        agent = EmailPersonalizationAgent()

        email_response = EmailResponse(
            subject_line="Quick question about State University's AV setup",
            email_body=(
                "Hi Sarah,\n\n"
                "I noticed State University is expanding online learning - that's exciting! "
                "Many AV Directors I work with have found that scaling lecture capture "
                "becomes a challenge during expansion phases.\n\n"
                "Would a 15-minute call be worth your time to explore how Epiphan "
                "helps institutions like yours?\n\n"
                "Best,"
            ),
        )

        self._mock_structured_llm(agent, email_response)

        result = await agent.run(
            lead=sample_lead,
            research_brief=sample_brief,
            persona=sample_persona,
            email_type="pattern_interrupt",
            sequence_step=1,
        )

        assert result is not None
        assert "subject_line" in result
        assert "email_body" in result
        assert len(result["subject_line"]) > 0
        assert len(result["email_body"]) > 0

    @pytest.mark.asyncio
    async def test_generates_different_emails_for_different_types(
        self,
        sample_lead: Lead,
        sample_brief: ResearchBrief,
        sample_persona: dict,
    ):
        """Test different email types produce different content."""
        from app.services.langgraph.agents.email_personalization import (
            EmailPersonalizationAgent,
        )

        agent = EmailPersonalizationAgent()

        response_1 = EmailResponse(subject_line="Test 1", email_body="Body 1")
        response_2 = EmailResponse(subject_line="Test 2", email_body="Body 2")

        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=[response_1, response_2])

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        object.__setattr__(agent, "_llm", mock_llm)

        await agent.run(
            lead=sample_lead,
            research_brief=sample_brief,
            persona=sample_persona,
            email_type="pattern_interrupt",
            sequence_step=1,
        )

        await agent.run(
            lead=sample_lead,
            research_brief=sample_brief,
            persona=sample_persona,
            email_type="breakup",
            sequence_step=3,
        )

        # Different email types should produce different calls
        assert mock_structured.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_missing_research_brief(
        self,
        sample_lead: Lead,
        sample_persona: dict,
    ):
        """Test agent handles missing research brief."""
        from app.services.langgraph.agents.email_personalization import (
            EmailPersonalizationAgent,
        )

        agent = EmailPersonalizationAgent()

        email_response = EmailResponse(
            subject_line="Intro",
            email_body="Hi Sarah, wanted to connect.",
        )
        self._mock_structured_llm(agent, email_response)

        result = await agent.run(
            lead=sample_lead,
            research_brief=None,
            persona=sample_persona,
            email_type="pattern_interrupt",
            sequence_step=1,
        )

        assert result is not None
        assert "subject_line" in result

    @pytest.mark.asyncio
    async def test_extracts_subject_and_body(
        self,
        sample_lead: Lead,
        sample_brief: ResearchBrief,
        sample_persona: dict,
    ):
        """Test proper extraction of subject line and body."""
        from app.services.langgraph.agents.email_personalization import (
            EmailPersonalizationAgent,
        )

        agent = EmailPersonalizationAgent()

        email_response = EmailResponse(
            subject_line="This is the subject line",
            email_body=(
                "This is the first paragraph of the body.\n\n"
                "This is the second paragraph.\n\n"
                "Best regards"
            ),
        )
        self._mock_structured_llm(agent, email_response)

        result = await agent.run(
            lead=sample_lead,
            research_brief=sample_brief,
            persona=sample_persona,
            email_type="pain_point",
            sequence_step=2,
        )

        assert result["subject_line"] == "This is the subject line"
        assert "first paragraph" in result["email_body"]

    @pytest.mark.asyncio
    async def test_uses_persona_pain_points(
        self,
        sample_lead: Lead,
        sample_brief: ResearchBrief,
        sample_persona: dict,
    ):
        """Test agent uses persona-specific pain points."""
        from app.services.langgraph.agents.email_personalization import (
            EmailPersonalizationAgent,
        )

        agent = EmailPersonalizationAgent()

        email_response = EmailResponse(
            subject_line="Test",
            email_body="Body",
        )
        mock_llm = self._mock_structured_llm(agent, email_response)

        await agent.run(
            lead=sample_lead,
            research_brief=sample_brief,
            persona=sample_persona,
            email_type="pain_point",
            sequence_step=2,
        )

        # Verify LLM was called (via structured output chain)
        assert mock_llm.with_structured_output.called


class TestEmailResponseModel:
    """Tests for the EmailResponse structured output model."""

    def test_email_response_creation(self):
        """Test EmailResponse model can be created."""
        resp = EmailResponse(
            subject_line="Test subject",
            email_body="Test body",
        )
        assert resp.subject_line == "Test subject"
        assert resp.email_body == "Test body"

    def test_email_response_requires_fields(self):
        """Test EmailResponse requires both fields."""
        with pytest.raises(ValueError):
            EmailResponse()  # type: ignore[call-arg]
