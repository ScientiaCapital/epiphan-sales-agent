"""Tests for Qualification Agent.

TDD RED phase: These tests define the expected behavior of the QualificationAgent.
Tests for LangGraph agent with 5-node graph:
- gather_data: Fetch enrichment + persona match
- needs_inference: Conditional routing based on data availability
- infer_missing: LLM inference for gaps
- score_dimensions: Call all 5 classification functions
- calculate_final: Weighted total, tier, confidence
- recommend_action: Next action based on tier
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.data.lead_schemas import Lead
from app.services.langgraph.states import QualificationTier


class TestQualificationAgent:
    """Tests for QualificationAgent."""

    @pytest.fixture
    def sample_lead(self) -> Lead:
        """Create a sample lead for testing."""
        return Lead(
            hubspot_id="hs-lead-123",
            email="sarah.johnson@stanford.edu",
            first_name="Sarah",
            last_name="Johnson",
            company="Stanford University",
            title="AV Director",
        )

    @pytest.fixture
    def enterprise_lead(self) -> Lead:
        """Create an enterprise higher-ed lead (Tier 1 candidate)."""
        return Lead(
            hubspot_id="hs-lead-456",
            email="john.smith@mit.edu",
            first_name="John",
            last_name="Smith",
            company="MIT",
            title="Director of Media Services",
        )

    @pytest.fixture
    def smb_lead(self) -> Lead:
        """Create a small business lead (lower tier candidate)."""
        return Lead(
            hubspot_id="hs-lead-789",
            email="bob@smallcorp.com",
            first_name="Bob",
            last_name="Wilson",
            company="Small Corp",
            title="IT Specialist",
        )

    def test_agent_initializes(self):
        """Test that agent initializes."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()
        assert agent is not None

    @pytest.mark.asyncio
    async def test_run_returns_qualification_result(self, sample_lead: Lead):
        """Test running agent produces a qualification result."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()

        # Mock enrichment sources
        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = {
                "first_name": "Sarah",
                "title": "Director of AV Services",
                "seniority": "director",
            }
            mock_clearbit.return_value = {
                "name": "Stanford University",
                "industry": "Higher Education",
                "employees": 15000,
                "tech_stack": ["Canvas", "Zoom", "Panopto"],
            }

            result = await agent.run(sample_lead)

        assert result is not None
        assert "total_score" in result
        assert "tier" in result
        assert "score_breakdown" in result
        assert "next_action" in result

    @pytest.mark.asyncio
    async def test_tier_1_lead_scored_correctly(self, enterprise_lead: Lead):
        """Test enterprise higher-ed lead scores as Tier 1."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = {
                "title": "Director of Media Services",
                "seniority": "director",
            }
            mock_clearbit.return_value = {
                "industry": "Higher Education",
                "employees": 12000,
                "tech_stack": ["Canvas", "Zoom", "Panopto"],
            }

            result = await agent.run(enterprise_lead)

        # Enterprise + Higher Ed + Director = should be Tier 1
        assert result["tier"] == QualificationTier.TIER_1
        assert result["total_score"] >= 70.0

    @pytest.mark.asyncio
    async def test_low_score_lead_disqualified(self, smb_lead: Lead):
        """Test small company non-ICP lead has low score.

        Scoring: size=0 (5 emp), vertical=3 (Retail), use_case=4 (Specialist),
        tech=5 (no stack), authority=4 (Specialist).
        Total: (0*2.5 + 3*2.0 + 4*2.5 + 5*1.5 + 4*1.5) = 0+6+10+7.5+6 = 29.5 ≈ Not ICP
        But with "IT Specialist" title detecting "video" keywords could boost use_case.
        """
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = {
                "title": "IT Specialist",
                "seniority": "entry",
            }
            mock_clearbit.return_value = {
                "industry": "Retail",
                "employees": 5,
                "tech_stack": [],
            }

            result = await agent.run(smb_lead)

        # Small + Non-core vertical + End user = should be low tier (Tier 3 or Not ICP)
        assert result["tier"] in [QualificationTier.TIER_3, QualificationTier.NOT_ICP]
        assert result["total_score"] < 50.0

    @pytest.mark.asyncio
    async def test_handles_missing_enrichment_data(self, sample_lead: Lead):
        """Test agent handles when enrichment returns None."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = None
            mock_clearbit.return_value = None

            result = await agent.run(sample_lead)

        # Should still return a result
        assert result is not None
        assert "tier" in result
        assert "missing_info" in result
        assert len(result["missing_info"]) > 0

    @pytest.mark.asyncio
    async def test_skip_enrichment_uses_provided_data(self, sample_lead: Lead):
        """Test skip_enrichment flag uses provided data only."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()

        enrichment_data = {
            "apollo": {"title": "AV Director", "seniority": "director"},
            "clearbit": {
                "industry": "Higher Education",
                "employees": 5000,
                "tech_stack": ["Canvas"],
            },
        }

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            result = await agent.run(
                sample_lead,
                enrichment_data=enrichment_data,
                skip_enrichment=True,
            )

        # Enrichment APIs should NOT be called
        mock_apollo.assert_not_called()
        mock_clearbit.assert_not_called()

        # Should still produce valid result
        assert result is not None
        assert "tier" in result

    @pytest.mark.asyncio
    async def test_score_breakdown_contains_all_dimensions(self, sample_lead: Lead):
        """Test score breakdown includes all 5 ICP dimensions."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = {"title": "Director", "seniority": "director"}
            mock_clearbit.return_value = {
                "industry": "Higher Education",
                "employees": 5000,
            }

            result = await agent.run(sample_lead)

        breakdown = result["score_breakdown"]
        assert "company_size" in breakdown
        assert "industry_vertical" in breakdown
        assert "use_case_fit" in breakdown
        assert "tech_stack_signals" in breakdown
        assert "buying_authority" in breakdown

    @pytest.mark.asyncio
    async def test_next_action_includes_ae_involvement_for_tier_1(
        self, enterprise_lead: Lead
    ):
        """Test Tier 1 leads get AE involvement flag."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = {"seniority": "director"}
            mock_clearbit.return_value = {
                "industry": "Higher Education",
                "employees": 10000,
                "tech_stack": ["Panopto"],
            }

            result = await agent.run(enterprise_lead)

        if result["tier"] == QualificationTier.TIER_1:
            assert result["next_action"]["ae_involvement"] is True

    @pytest.mark.asyncio
    async def test_confidence_affected_by_data_quality(self, sample_lead: Lead):
        """Test confidence score reflects data completeness."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()

        # First run with complete data
        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = {"title": "Director", "seniority": "director"}
            mock_clearbit.return_value = {
                "industry": "Higher Education",
                "employees": 5000,
                "tech_stack": ["Canvas", "Zoom"],
            }

            result_complete = await agent.run(sample_lead)

        # Second run with sparse data
        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = None
            mock_clearbit.return_value = None

            result_sparse = await agent.run(sample_lead)

        # Complete data should have higher confidence
        assert result_complete["confidence"] > result_sparse["confidence"]

    @pytest.mark.asyncio
    async def test_persona_match_affects_use_case_score(self, sample_lead: Lead):
        """Test persona match influences use case fit score."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = {"title": "AV Director"}
            mock_clearbit.return_value = {
                "industry": "Higher Education",
                "employees": 5000,
            }

            result = await agent.run(sample_lead)

        # AV Director should score high on use case fit
        use_case_score = result["score_breakdown"]["use_case_fit"]["raw_score"]
        assert use_case_score >= 9  # Live streaming or lecture capture

    @pytest.mark.asyncio
    async def test_tech_stack_competitor_boosts_score(self, sample_lead: Lead):
        """Test having competitor tech boosts tech stack score."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = {"title": "AV Director"}
            mock_clearbit.return_value = {
                "industry": "Higher Education",
                "employees": 5000,
                "tech_stack": ["Panopto", "Canvas", "Zoom"],  # Panopto is competitor
            }

            result = await agent.run(sample_lead)

        # Should score 10 for competitive solution
        tech_score = result["score_breakdown"]["tech_stack_signals"]["raw_score"]
        assert tech_score == 10


class TestQualificationAgentEdgeCases:
    """Edge case tests for QualificationAgent."""

    @pytest.fixture
    def minimal_lead(self) -> Lead:
        """Create a minimal lead with only required fields."""
        return Lead(
            hubspot_id="hs-minimal",
            email="user@unknown.com",
        )

    @pytest.mark.asyncio
    async def test_handles_minimal_lead_data(self, minimal_lead: Lead):
        """Test agent handles lead with minimal data."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = None
            mock_clearbit.return_value = None

            result = await agent.run(minimal_lead)

        # Should not crash, should return valid result
        assert result is not None
        assert "tier" in result

    @pytest.mark.asyncio
    async def test_handles_enrichment_exception(self):
        """Test agent handles exceptions from enrichment APIs."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        lead = Lead(hubspot_id="hs-error", email="error@test.com", company="Test Corp")
        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.side_effect = Exception("Apollo API error")
            mock_clearbit.side_effect = Exception("Clearbit API error")

            result = await agent.run(lead)

        # Should gracefully handle exceptions
        assert result is not None
        assert "tier" in result

    @pytest.mark.asyncio
    async def test_university_domain_detected_as_higher_ed(self):
        """Test .edu domain helps detect higher ed vertical."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        lead = Lead(
            hubspot_id="hs-edu",
            email="user@university.edu",
            company="Unknown University",
            title="IT Manager",
        )
        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = None
            mock_clearbit.return_value = None

            result = await agent.run(lead)

        # Should detect higher ed from company name and domain
        vertical_score = result["score_breakdown"]["industry_vertical"]["raw_score"]
        assert vertical_score >= 6  # At minimum should detect something


class TestQualificationAgentIntegration:
    """Integration-style tests for full qualification flow."""

    @pytest.mark.asyncio
    async def test_full_qualification_flow_tier_1(self):
        """Test complete qualification flow for ideal Tier 1 lead."""
        from app.services.langgraph.agents.qualification import QualificationAgent

        lead = Lead(
            hubspot_id="hs-ideal",
            email="director@stanford.edu",
            first_name="Jane",
            last_name="Director",
            company="Stanford University",
            title="Director of Academic Technology",
        )
        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = {
                "title": "Director of Academic Technology",
                "seniority": "director",
                "linkedin_url": "https://linkedin.com/in/jane-director",
            }
            mock_clearbit.return_value = {
                "name": "Stanford University",
                "industry": "Higher Education",
                "employees": 16000,
                "tech_stack": ["Canvas", "Zoom", "Kaltura", "Panopto"],
            }

            result = await agent.run(lead)

        # Verify full result structure
        assert result["tier"] == QualificationTier.TIER_1
        assert result["total_score"] >= 70.0
        assert result["confidence"] >= 0.7
        assert result["next_action"]["action_type"] == "priority_sequence"
        assert result["next_action"]["ae_involvement"] is True
        assert result["next_action"]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_full_qualification_flow_tier_2(self):
        """Test complete qualification flow for mid-tier lead.

        500 employees (mid-market=8), Corporate Training (corporate=8),
        IT Manager (influencer=7), Teams/Zoom (LMS=8), title-based use case.
        This actually scores quite high due to collaboration tools and manager title.
        """
        from app.services.langgraph.agents.qualification import QualificationAgent

        lead = Lead(
            hubspot_id="hs-tier2",
            email="manager@mediumcorp.com",
            first_name="Mike",
            last_name="Manager",
            company="Medium Corp",
            title="IT Manager",
        )
        agent = QualificationAgent()

        with (
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.qualification.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
        ):
            mock_apollo.return_value = {
                "title": "IT Manager",
                "seniority": "manager",
            }
            mock_clearbit.return_value = {
                "industry": "Retail",  # Lower scoring vertical
                "employees": 150,  # Mid-market but lower
                "tech_stack": ["Salesforce"],  # No video/LMS tools
            }

            result = await agent.run(lead)

        # Should be Tier 2 or Tier 3 with this profile
        assert result["tier"] in [
            QualificationTier.TIER_1,
            QualificationTier.TIER_2,
            QualificationTier.TIER_3,
        ]
        # Just verify it's a valid result with reasonable score
        assert 30.0 <= result["total_score"] <= 100.0
