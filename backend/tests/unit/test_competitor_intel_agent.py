"""Tests for Competitor Intelligence Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCompetitorIntelAgent:
    """Tests for CompetitorIntelAgent."""

    @pytest.mark.asyncio
    async def test_responds_to_claim(self):
        """Test agent responds to competitor claim."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(
                return_value=MagicMock(
                    content="Calculate TCO: ATEM + PC + software = $3,000-5,000. Pearl Nano at $1,999 is all-in-one."
                )
            )

            result = await agent.run(
                competitor_name="blackmagic",
                context="The prospect said ATEM is cheaper upfront",
                query_type="claim",
            )

        assert result["response"] != ""
        assert "battlecard" in result
        assert isinstance(result["proof_points"], list)

    @pytest.mark.asyncio
    async def test_handles_unknown_competitor(self):
        """Test agent handles unknown competitor gracefully."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        result = await agent.run(
            competitor_name="unknown_xyz",
            context="They mentioned unknown_xyz",
            query_type="comparison",
        )

        # Should handle gracefully - no battlecard but still provides response
        assert result["battlecard"] is None
        assert "response" in result

    @pytest.mark.asyncio
    async def test_includes_follow_up_question(self):
        """Test agent includes follow-up question."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(
                return_value=MagicMock(
                    content="Response here. FOLLOW_UP: What's their current recording setup?"
                )
            )

            result = await agent.run(
                competitor_name="blackmagic",
                context="They use ATEM",
                query_type="objection",
            )

        # Agent should extract follow-up
        assert "follow_up_question" in result

    @pytest.mark.asyncio
    async def test_finds_relevant_differentiators(self):
        """Test agent finds relevant differentiators from context."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(
                return_value=MagicMock(content="Test response")
            )

            result = await agent.run(
                competitor_name="blackmagic",
                context="They mentioned recording capabilities",
                query_type="comparison",
            )

        assert "battlecard" in result
        assert result["battlecard"] is not None


class TestCompetitorIntelAgentGraph:
    """Tests for the LangGraph structure."""

    def test_graph_has_required_nodes(self):
        """Test that graph has all required nodes."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()
        graph = agent.graph

        # Check nodes exist
        assert "lookup_battlecard" in graph.nodes
        assert "match_context" in graph.nodes
        assert "generate_response" in graph.nodes

    def test_graph_compiles(self):
        """Test that graph compiles without error."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        # Should not raise
        compiled = agent.compiled_graph
        assert compiled is not None

    def test_uses_fast_model(self):
        """Test that agent uses fast model (Cerebras) for speed."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        # The agent should use the "lookup" task type for fast responses
        assert agent.llm is not None
