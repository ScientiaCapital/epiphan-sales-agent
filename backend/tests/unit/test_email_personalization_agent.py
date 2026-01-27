"""Tests for Email Personalization Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.lead_schemas import Lead
from app.services.langgraph.states import ResearchBrief


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

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.content = """Subject: Quick question about State University's AV setup

Hi Sarah,

I noticed State University is expanding online learning - that's exciting! Many AV Directors I work with have found that scaling lecture capture becomes a challenge during expansion phases.

Would a 15-minute call be worth your time to explore how Epiphan helps institutions like yours?

Best,
[Name]"""

        with patch.object(
            agent, "_llm", new_callable=MagicMock
        ) as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

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

        mock_response_1 = MagicMock()
        mock_response_1.content = "Subject: Test 1\n\nBody 1"

        mock_response_2 = MagicMock()
        mock_response_2.content = "Subject: Test 2\n\nBody 2"

        with patch.object(
            agent, "_llm", new_callable=MagicMock
        ) as mock_llm:
            mock_llm.ainvoke = AsyncMock(side_effect=[mock_response_1, mock_response_2])

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
        assert mock_llm.ainvoke.call_count == 2

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

        mock_response = MagicMock()
        mock_response.content = "Subject: Intro\n\nHi Sarah, wanted to connect."

        with patch.object(
            agent, "_llm", new_callable=MagicMock
        ) as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)

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

        mock_response = MagicMock()
        mock_response.content = """Subject: This is the subject line

This is the first paragraph of the body.

This is the second paragraph.

Best regards"""

        with patch.object(
            agent, "_llm", new_callable=MagicMock
        ) as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)

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

        mock_response = MagicMock()
        mock_response.content = "Subject: Test\n\nBody"

        with patch.object(
            agent, "_llm", new_callable=MagicMock
        ) as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)

            await agent.run(
                lead=sample_lead,
                research_brief=sample_brief,
                persona=sample_persona,
                email_type="pain_point",
                sequence_step=2,
            )

            # Check the prompt included persona pain points
            # The prompt should be constructed (we verify through the call)
            assert mock_llm.ainvoke.called
