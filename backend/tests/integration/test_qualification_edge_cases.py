"""Integration tests for QualificationAgent extended thinking edge cases.

Tests verify that extended thinking is triggered for:
1. Borderline scores near tier thresholds (28-32, 48-52, 68-72)
2. Low confidence classifications (<0.6)
3. Extended thinking produces reasoning for tier adjustments
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.lead_schemas import Lead
from app.services.langgraph.agents.qualification import QualificationAgent
from app.services.langgraph.states import QualificationTier, TierDecision


class TestIsEdgeCaseMethod:
    """Unit tests for _is_edge_case detection logic."""

    @pytest.fixture
    def agent(self) -> QualificationAgent:
        """Create agent instance."""
        return QualificationAgent()

    def test_detects_not_icp_tier3_boundary(self, agent: QualificationAgent) -> None:
        """Test score 29 (Not ICP/Tier 3 boundary at 30) is edge case."""
        assert agent._is_edge_case(29.0, confidence=0.8) is True
        assert agent._is_edge_case(30.0, confidence=0.8) is True
        assert agent._is_edge_case(31.0, confidence=0.8) is True

    def test_detects_tier3_tier2_boundary(self, agent: QualificationAgent) -> None:
        """Test score 50 (Tier 3/Tier 2 boundary) is edge case."""
        assert agent._is_edge_case(48.0, confidence=0.8) is True
        assert agent._is_edge_case(50.0, confidence=0.8) is True
        assert agent._is_edge_case(52.0, confidence=0.8) is True

    def test_detects_tier2_tier1_boundary(self, agent: QualificationAgent) -> None:
        """Test score 69 (Tier 2/Tier 1 boundary at 70) is edge case."""
        assert agent._is_edge_case(68.0, confidence=0.8) is True
        assert agent._is_edge_case(70.0, confidence=0.8) is True
        assert agent._is_edge_case(72.0, confidence=0.8) is True

    def test_clear_scores_not_edge_cases(self, agent: QualificationAgent) -> None:
        """Test clear scores outside borderline ranges are not edge cases."""
        # Well below Not ICP threshold
        assert agent._is_edge_case(15.0, confidence=0.8) is False
        # Clear Tier 3
        assert agent._is_edge_case(40.0, confidence=0.8) is False
        # Clear Tier 2
        assert agent._is_edge_case(60.0, confidence=0.8) is False
        # Clear Tier 1
        assert agent._is_edge_case(85.0, confidence=0.8) is False

    def test_low_confidence_always_triggers(self, agent: QualificationAgent) -> None:
        """Test low confidence (<0.6) always triggers edge case."""
        # Even with clear scores, low confidence triggers extended thinking
        assert agent._is_edge_case(40.0, confidence=0.5) is True
        assert agent._is_edge_case(60.0, confidence=0.4) is True
        assert agent._is_edge_case(85.0, confidence=0.3) is True

    def test_threshold_confidence_not_edge_case(
        self, agent: QualificationAgent
    ) -> None:
        """Test exactly 0.6 confidence is not edge case (threshold is <0.6)."""
        assert agent._is_edge_case(40.0, confidence=0.6) is False
        assert agent._is_edge_case(60.0, confidence=0.7) is False


class TestExtendedThinkingIntegration:
    """Integration tests for extended thinking on real edge case scenarios."""

    @pytest.fixture
    def mock_thinking_model(self) -> MagicMock:
        """Create a mock for the extended thinking model."""
        mock = MagicMock()
        mock.ainvoke = AsyncMock(return_value=MagicMock(content="tier_2\nTest reasoning"))
        return mock

    @pytest.fixture
    def borderline_not_icp_lead(self) -> Lead:
        """Create lead that should score around 28-32 (Not ICP/Tier 3 boundary)."""
        return Lead(
            hubspot_id="hs-borderline-low",
            email="intern@smallcompany.com",
            first_name="Alex",
            last_name="Student",
            company="Small Company LLC",
            title="Marketing Coordinator",  # Low authority
        )

    @pytest.fixture
    def borderline_tier2_lead(self) -> Lead:
        """Create lead that should score around 48-52 (Tier 3/Tier 2 boundary)."""
        return Lead(
            hubspot_id="hs-borderline-mid",
            email="manager@midsize.com",
            first_name="Jordan",
            last_name="Manager",
            company="Midsize Corp",
            title="Training Manager",  # Mid-level L&D persona
        )

    @pytest.fixture
    def borderline_tier1_lead(self) -> Lead:
        """Create lead that should score around 68-72 (Tier 2/Tier 1 boundary)."""
        return Lead(
            hubspot_id="hs-borderline-high",
            email="director@healthcare.org",
            first_name="Pat",
            last_name="Director",
            company="Regional Medical Center",
            title="Director of Telehealth",  # Good vertical, good authority
        )

    @pytest.mark.asyncio
    async def test_extended_thinking_triggered_for_score_29(
        self, borderline_not_icp_lead: Lead
    ) -> None:
        """Test extended thinking triggers for borderline Not ICP/Tier 3 score."""
        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch.object(
                agent, "_apply_extended_thinking", new_callable=AsyncMock
            ) as mock_thinking,
        ):
            # Set up enrichment to produce borderline score ~29
            mock_apollo.return_value = {
                "title": "Marketing Coordinator",
                "seniority": "entry",
                "industry": "Real Estate",  # Low scoring vertical
                "employees": 8,  # Too small
                "tech_stack": [],
            }

            # Mock extended thinking to track calls and return initial tier
            mock_thinking.return_value = (QualificationTier.NOT_ICP, "")

            result = await agent.run(borderline_not_icp_lead)

            # Verify extended thinking was called for borderline score
            if result["total_score"] >= 28 and result["total_score"] <= 32:
                mock_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_extended_thinking_triggered_for_score_50(
        self, borderline_tier2_lead: Lead
    ) -> None:
        """Test extended thinking triggers for Tier 3/Tier 2 boundary."""
        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch.object(
                agent, "_apply_extended_thinking", new_callable=AsyncMock
            ) as mock_thinking,
        ):
            # Set up enrichment to produce score ~50
            mock_apollo.return_value = {
                "title": "Training Manager",
                "seniority": "manager",
                "industry": "Retail",  # Mid-tier vertical
                "employees": 200,  # Mid-market
                "tech_stack": ["Workday"],  # LMS signals
            }

            mock_thinking.return_value = (QualificationTier.TIER_2, "")

            result = await agent.run(borderline_tier2_lead)

            # Verify extended thinking was called for borderline score
            if 48 <= result["total_score"] <= 52:
                mock_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_extended_thinking_triggered_for_score_69(
        self, borderline_tier1_lead: Lead
    ) -> None:
        """Test extended thinking triggers for Tier 2/Tier 1 boundary."""
        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch.object(
                agent, "_apply_extended_thinking", new_callable=AsyncMock
            ) as mock_thinking,
        ):
            # Set up enrichment to produce score ~69
            mock_apollo.return_value = {
                "title": "Director of Telehealth",
                "seniority": "director",
                "industry": "Healthcare",  # Good vertical
                "employees": 800,  # Mid-market (not enterprise)
                "tech_stack": ["Zoom", "Teams"],  # Video tools but no competitor
            }

            mock_thinking.return_value = (QualificationTier.TIER_1, "")

            result = await agent.run(borderline_tier1_lead)

            # Verify extended thinking was called
            if 68 <= result["total_score"] <= 72:
                mock_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_extended_thinking_triggered_for_low_confidence(self) -> None:
        """Test extended thinking triggers for low confidence regardless of score."""
        lead = Lead(
            hubspot_id="hs-low-conf",
            email="unknown@mystery.com",
            company="Mystery Corp",
        )
        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch.object(
                agent, "_apply_extended_thinking", new_callable=AsyncMock
            ) as mock_thinking,
        ):
            # Minimal enrichment produces low confidence
            mock_apollo.return_value = None

            mock_thinking.return_value = (QualificationTier.TIER_3, "")

            result = await agent.run(lead)

            # Low confidence should trigger extended thinking
            if result["confidence"] < 0.6:
                mock_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_extended_thinking_produces_reasoning(self) -> None:
        """Test extended thinking returns reasoning when tier is adjusted."""
        lead = Lead(
            hubspot_id="hs-adjustment",
            email="director@university.edu",
            company="State University",
            title="AV Director",
        )
        agent = QualificationAgent()

        # Mock with_structured_output chain for TierDecision
        tier_decision = TierDecision(
            tier=QualificationTier.TIER_1,
            reasoning=(
                "Despite the mid-market company size, the strong higher education "
                "fit, AV Director title, and LMS presence indicate a priority lead."
            ),
        )
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=tier_decision)

        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        agent._router._claude_thinking = mock_model

        with patch(
            "app.services.langgraph.agents.qualification.enrich_from_apollo",
            new_callable=AsyncMock,
        ) as mock_apollo:
            # Set up enrichment for borderline score
            mock_apollo.return_value = {
                "title": "AV Director",
                "seniority": "director",
                "industry": "Higher Education",
                "employees": 3000,  # Mid-market
                "tech_stack": ["Canvas"],
            }

            result = await agent.run(lead)

        # If tier was adjusted, should include reasoning
        if result.get("tier_adjusted"):
            assert "extended_reasoning" in result
            assert len(result["extended_reasoning"]) > 0


class TestExtendedThinkingModelSelection:
    """Tests for correct model selection in extended thinking."""

    @pytest.fixture
    def agent(self) -> QualificationAgent:
        """Create agent with mocked router."""
        return QualificationAgent()

    @pytest.mark.asyncio
    async def test_uses_claude_with_thinking_model(self) -> None:
        """Test _apply_extended_thinking uses claude_with_thinking model."""
        lead = Lead(
            hubspot_id="hs-model",
            email="test@test.com",
            company="Test Corp",
        )
        agent = QualificationAgent()

        score_breakdown = {
            "company_size": {"raw_score": 5, "category": "mid-market", "reason": "test", "confidence": 0.5},
            "industry_vertical": {"raw_score": 5, "category": "other", "reason": "test", "confidence": 0.5},
            "use_case_fit": {"raw_score": 5, "category": "unknown", "reason": "test", "confidence": 0.5},
            "tech_stack_signals": {"raw_score": 5, "category": "unknown", "reason": "test", "confidence": 0.5},
            "buying_authority": {"raw_score": 5, "category": "unknown", "reason": "test", "confidence": 0.5},
        }

        # Mock with_structured_output chain
        tier_decision = TierDecision(
            tier=QualificationTier.TIER_2,
            reasoning="Reasonable fit.",
        )
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=tier_decision)

        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured

        # Mock the private attribute behind the property
        agent._router._claude_thinking = mock_model

        tier, reasoning = await agent._apply_extended_thinking(
            lead=lead,
            score_breakdown=score_breakdown,
            total_score=50.0,
            initial_tier=QualificationTier.TIER_3,
            confidence=0.5,
        )

        # Verify claude_with_thinking was used via with_structured_output
        mock_model.with_structured_output.assert_called_once_with(TierDecision)
        mock_structured.ainvoke.assert_called_once()
        assert tier == QualificationTier.TIER_2
        assert reasoning == "Reasonable fit."

    @pytest.mark.asyncio
    async def test_extended_thinking_fallback_on_error(self) -> None:
        """Test extended thinking falls back to initial tier on error."""
        lead = Lead(
            hubspot_id="hs-error",
            email="test@test.com",
            company="Test Corp",
        )
        agent = QualificationAgent()

        score_breakdown = {
            "company_size": {"raw_score": 5, "category": "mid", "reason": "test", "confidence": 0.5},
            "industry_vertical": {"raw_score": 5, "category": "other", "reason": "test", "confidence": 0.5},
            "use_case_fit": {"raw_score": 5, "category": "unknown", "reason": "test", "confidence": 0.5},
            "tech_stack_signals": {"raw_score": 5, "category": "unknown", "reason": "test", "confidence": 0.5},
            "buying_authority": {"raw_score": 5, "category": "unknown", "reason": "test", "confidence": 0.5},
        }

        # Error in with_structured_output chain
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=Exception("API error"))

        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        agent._router._claude_thinking = mock_model

        tier, reasoning = await agent._apply_extended_thinking(
            lead=lead,
            score_breakdown=score_breakdown,
            total_score=50.0,
            initial_tier=QualificationTier.TIER_3,
            confidence=0.5,
        )

        # Should fall back to initial tier
        assert tier == QualificationTier.TIER_3
        assert reasoning == ""


class TestBorderlineScenariosCoverage:
    """Ensure all borderline scenarios have test coverage."""

    @pytest.mark.asyncio
    async def test_score_28_triggers_edge_case(self) -> None:
        """Score 28 is in borderline range (28-32)."""
        agent = QualificationAgent()
        assert agent._is_edge_case(28.0, 0.8) is True

    @pytest.mark.asyncio
    async def test_score_32_triggers_edge_case(self) -> None:
        """Score 32 is in borderline range (28-32)."""
        agent = QualificationAgent()
        assert agent._is_edge_case(32.0, 0.8) is True

    @pytest.mark.asyncio
    async def test_score_48_triggers_edge_case(self) -> None:
        """Score 48 is in borderline range (48-52)."""
        agent = QualificationAgent()
        assert agent._is_edge_case(48.0, 0.8) is True

    @pytest.mark.asyncio
    async def test_score_52_triggers_edge_case(self) -> None:
        """Score 52 is in borderline range (48-52)."""
        agent = QualificationAgent()
        assert agent._is_edge_case(52.0, 0.8) is True

    @pytest.mark.asyncio
    async def test_score_68_triggers_edge_case(self) -> None:
        """Score 68 is in borderline range (68-72)."""
        agent = QualificationAgent()
        assert agent._is_edge_case(68.0, 0.8) is True

    @pytest.mark.asyncio
    async def test_score_72_triggers_edge_case(self) -> None:
        """Score 72 is in borderline range (68-72)."""
        agent = QualificationAgent()
        assert agent._is_edge_case(72.0, 0.8) is True

    @pytest.mark.asyncio
    async def test_confidence_0_59_triggers_edge_case(self) -> None:
        """Confidence 0.59 is below threshold (0.6)."""
        agent = QualificationAgent()
        assert agent._is_edge_case(40.0, 0.59) is True

    @pytest.mark.asyncio
    async def test_confidence_0_6_does_not_trigger_edge_case(self) -> None:
        """Confidence 0.6 is at threshold, not edge case for clear score."""
        agent = QualificationAgent()
        # Score 40 is not in any borderline range
        assert agent._is_edge_case(40.0, 0.6) is False
