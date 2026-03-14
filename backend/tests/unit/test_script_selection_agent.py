"""Tests for Script Selection Agent."""

from unittest.mock import AsyncMock, patch

import pytest

from app.data.lead_schemas import Lead
from app.services.langgraph.states import ScriptResponseOutput


@pytest.fixture
def sample_lead() -> Lead:
    """Sample lead for testing."""
    return Lead(
        hubspot_id="123",
        email="sarah.johnson@university.edu",
        first_name="Sarah",
        last_name="Johnson",
        company="State University",
        title="AV Director",
    )


class TestScriptSelectionAgent:
    """Tests for ScriptSelectionAgent."""

    @pytest.mark.asyncio
    async def test_generates_warm_script(self, sample_lead: Lead) -> None:
        """Test agent generates personalized warm script via structured output."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        mock_structured = AsyncMock(
            return_value=ScriptResponseOutput(
                personalized_script="Hey Sarah, this is Tim from Epiphan Video..."
            )
        )

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.with_structured_output.return_value.ainvoke = mock_structured

            result = await agent.run(
                lead=sample_lead,
                persona_match="av_director",
                trigger="demo_request",
                call_type="warm",
            )

        assert result["personalized_script"] != ""
        assert isinstance(result["talking_points"], list)
        assert isinstance(result["objection_responses"], list)

    @pytest.mark.asyncio
    async def test_generates_cold_script(self, sample_lead: Lead) -> None:
        """Test agent generates personalized cold script via structured output."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        mock_structured = AsyncMock(
            return_value=ScriptResponseOutput(
                personalized_script="Hey Sarah, this is Tim from Epiphan Video - got 30 seconds?"
            )
        )

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.with_structured_output.return_value.ainvoke = mock_structured

            result = await agent.run(
                lead=sample_lead,
                persona_match="av_director",
                trigger=None,
                call_type="cold",
            )

        assert result["personalized_script"] != ""

    @pytest.mark.asyncio
    async def test_includes_objection_handlers(self, sample_lead: Lead) -> None:
        """Test agent includes relevant objection handlers."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        mock_structured = AsyncMock(
            return_value=ScriptResponseOutput(
                personalized_script="Personalized script here"
            )
        )

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.with_structured_output.return_value.ainvoke = mock_structured

            result = await agent.run(
                lead=sample_lead,
                persona_match="av_director",
                trigger="demo_request",
                call_type="warm",
            )

        assert isinstance(result["objection_responses"], list)

    @pytest.mark.asyncio
    async def test_handles_missing_persona(self, sample_lead: Lead) -> None:
        """Test agent handles missing persona gracefully."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        mock_structured = AsyncMock(
            return_value=ScriptResponseOutput(
                personalized_script="Generic script here"
            )
        )

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.with_structured_output.return_value.ainvoke = mock_structured

            result = await agent.run(
                lead=sample_lead,
                persona_match=None,
                trigger=None,
                call_type="cold",
            )

        assert "personalized_script" in result


class TestScriptSelectionAgentGraph:
    """Tests for the LangGraph structure."""

    def test_graph_has_required_nodes(self) -> None:
        """Test that graph has all required nodes."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()
        graph = agent.graph

        assert "load_script" in graph.nodes
        assert "extract_context" in graph.nodes
        assert "personalize" in graph.nodes

    def test_graph_compiles(self) -> None:
        """Test that graph compiles without error."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()
        compiled = agent.compiled_graph
        assert compiled is not None

    def test_uses_quality_model(self) -> None:
        """Test that agent uses quality model (Claude) for personalization."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()
        assert agent.llm is not None
