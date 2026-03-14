"""Tests for Competitor Intelligence Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.langgraph.states import CompetitorResponseOutput


class TestCompetitorIntelAgent:
    """Tests for CompetitorIntelAgent."""

    @pytest.mark.asyncio
    async def test_responds_to_claim(self) -> None:
        """Test agent responds to competitor claim with structured output."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        mock_structured = AsyncMock(
            return_value=CompetitorResponseOutput(
                response="Calculate TCO: ATEM + PC + software = $3,000-5,000. Pearl Nano at $1,999 is all-in-one.",
                follow_up_question="What does your current recording setup look like?",
            )
        )

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.with_structured_output.return_value.ainvoke = mock_structured

            result = await agent.run(
                competitor_name="blackmagic",
                context="The prospect said ATEM is cheaper upfront",
                query_type="claim",
            )

        assert result["response"] != ""
        assert "battlecard" in result
        assert isinstance(result["proof_points"], list)

    @pytest.mark.asyncio
    async def test_handles_unknown_competitor(self) -> None:
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
    async def test_includes_follow_up_question(self) -> None:
        """Test agent includes follow-up question via structured output."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        mock_structured = AsyncMock(
            return_value=CompetitorResponseOutput(
                response="Response here.",
                follow_up_question="What's their current recording setup?",
            )
        )

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.with_structured_output.return_value.ainvoke = mock_structured

            result = await agent.run(
                competitor_name="blackmagic",
                context="They use ATEM",
                query_type="objection",
            )

        assert result["follow_up_question"] == "What's their current recording setup?"

    @pytest.mark.asyncio
    async def test_empty_follow_up_returns_none(self) -> None:
        """Test that empty follow_up_question is returned as None."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        mock_structured = AsyncMock(
            return_value=CompetitorResponseOutput(
                response="Test response",
                follow_up_question=None,
            )
        )

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.with_structured_output.return_value.ainvoke = mock_structured

            result = await agent.run(
                competitor_name="blackmagic",
                context="They mentioned recording capabilities",
                query_type="comparison",
            )

        assert result["follow_up_question"] is None

    @pytest.mark.asyncio
    async def test_finds_relevant_differentiators(self) -> None:
        """Test agent finds relevant differentiators from context."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        mock_structured = AsyncMock(
            return_value=CompetitorResponseOutput(
                response="Test response",
                follow_up_question="",
            )
        )

        with patch.object(agent, "llm") as mock_llm:
            mock_llm.with_structured_output.return_value.ainvoke = mock_structured

            result = await agent.run(
                competitor_name="blackmagic",
                context="They mentioned recording capabilities",
                query_type="comparison",
            )

        assert "battlecard" in result
        assert result["battlecard"] is not None


class TestCompetitorIntelAgentGraph:
    """Tests for the LangGraph structure."""

    def test_graph_has_required_nodes(self) -> None:
        """Test that graph has all required nodes."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()
        graph = agent.graph

        assert "lookup_battlecard" in graph.nodes
        assert "match_context" in graph.nodes
        assert "generate_response" in graph.nodes

    def test_graph_compiles(self) -> None:
        """Test that graph compiles without error."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()
        compiled = agent.compiled_graph
        assert compiled is not None

    def test_uses_fast_model(self) -> None:
        """Test that agent uses fast model (Cerebras) for speed."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()
        assert agent.llm is not None
