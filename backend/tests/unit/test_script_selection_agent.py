"""Tests for Script Selection Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.lead_schemas import Lead


@pytest.fixture
def sample_lead():
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
    async def test_generates_warm_script(self, sample_lead):
        """Test agent generates personalized warm script."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(
                return_value=MagicMock(
                    content="Hey Sarah, this is Tim from Epiphan Video..."
                )
            )

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
    async def test_generates_cold_script(self, sample_lead):
        """Test agent generates personalized cold script."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(
                return_value=MagicMock(
                    content="Hey Sarah, this is Tim from Epiphan Video - got 30 seconds?"
                )
            )

            result = await agent.run(
                lead=sample_lead,
                persona_match="av_director",
                trigger=None,
                call_type="cold",
            )

        assert result["personalized_script"] != ""

    @pytest.mark.asyncio
    async def test_includes_objection_handlers(self, sample_lead):
        """Test agent includes relevant objection handlers."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(
                return_value=MagicMock(content="Personalized script here")
            )

            result = await agent.run(
                lead=sample_lead,
                persona_match="av_director",
                trigger="demo_request",
                call_type="warm",
            )

        # Cold scripts from higher_ed vertical should have objection pivots
        assert isinstance(result["objection_responses"], list)

    @pytest.mark.asyncio
    async def test_handles_missing_persona(self, sample_lead):
        """Test agent handles missing persona gracefully."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(
                return_value=MagicMock(content="Generic script here")
            )

            result = await agent.run(
                lead=sample_lead,
                persona_match=None,
                trigger=None,
                call_type="cold",
            )

        # Should still produce a script (falls back to default)
        assert "personalized_script" in result


class TestScriptSelectionAgentGraph:
    """Tests for the LangGraph structure."""

    def test_graph_has_required_nodes(self):
        """Test that graph has all required nodes."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()
        graph = agent.graph

        assert "load_script" in graph.nodes
        assert "extract_context" in graph.nodes
        assert "personalize" in graph.nodes

    def test_graph_compiles(self):
        """Test that graph compiles without error."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()
        compiled = agent.compiled_graph

        assert compiled is not None

    def test_uses_quality_model(self):
        """Test that agent uses quality model (Claude) for personalization."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        # The agent should use the "personalization" task type for quality
        assert agent.llm is not None
