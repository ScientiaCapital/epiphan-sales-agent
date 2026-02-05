"""Tests for Master Orchestrator Agent.

Tests the multi-agent coordination, parallel execution, and review gates.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.types import Command

from app.data.lead_schemas import Lead
from app.services.langgraph.agents.orchestrator import (
    MasterOrchestratorAgent,
    master_orchestrator_agent,
)
from app.services.langgraph.states import QualificationTier


@pytest.fixture
def sample_lead() -> Lead:
    """Create a sample lead for testing."""
    return Lead(
        hubspot_id="hs-test-123",
        email="sarah.johnson@stateuniversity.edu",
        first_name="Sarah",
        last_name="Johnson",
        company="State University",
        title="AV Director",
    )


@pytest.fixture
def mock_research_result() -> dict:
    """Mock research agent result."""
    return {
        "research_brief": {
            "company_overview": "State University is a higher education institution",
            "recent_news": [],
            "talking_points": ["Higher ed focus", "Large organization"],
            "risk_factors": [],
            "linkedin_summary": None,
        },
        "enrichment_data": {
            "phone": "+1-555-0123",
            "title": "AV Director",
            "seniority": "director",
        },
        "talking_points": ["Education vertical"],
        "risk_factors": [],
    }


@pytest.fixture
def mock_qualification_result() -> dict:
    """Mock qualification agent result."""
    return {
        "tier": QualificationTier.TIER_1,
        "is_atl": True,
        "persona_match": "AV Director",
        "total_score": 85,
        "score_breakdown": {},
    }


@pytest.fixture
def mock_script_result() -> dict:
    """Mock script selection result."""
    return {
        "personalized_script": "Hi Sarah, I noticed State University...",
        "talking_points": ["Education tech"],
        "objection_responses": [],
    }


@pytest.fixture
def mock_email_result() -> dict:
    """Mock email personalization result."""
    return {
        "subject_line": "Quick question about AV at State University",
        "email_body": "Hi Sarah...",
        "follow_up_note": None,
    }


class TestMasterOrchestratorAgentInit:
    """Tests for orchestrator initialization."""

    def test_orchestrator_initializes(self) -> None:
        """Test orchestrator initializes without errors."""
        agent = MasterOrchestratorAgent()
        assert agent is not None
        assert agent._graph is None  # Graph built lazily

    def test_singleton_exists(self) -> None:
        """Test singleton instance is available."""
        assert master_orchestrator_agent is not None
        assert isinstance(master_orchestrator_agent, MasterOrchestratorAgent)


class TestParallelResearchPhase:
    """Tests for the parallel research phase."""

    @pytest.mark.asyncio
    async def test_parallel_research_runs_both_agents(
        self, sample_lead: Lead, mock_research_result: dict, mock_qualification_result: dict
    ) -> None:
        """Test that research and qualification run in parallel."""
        agent = MasterOrchestratorAgent()

        with (
            patch.object(
                agent._research_agent, "run", new_callable=AsyncMock
            ) as mock_research,
            patch.object(
                agent._qualification_agent, "run", new_callable=AsyncMock
            ) as mock_qual,
        ):
            mock_research.return_value = mock_research_result
            mock_qual.return_value = mock_qualification_result

            # Build the initial state
            state = {
                "lead": sample_lead,
                "process_config": {},
            }

            # Call the parallel research node directly
            result = await agent._parallel_research_node(state)

            # Verify both agents were called
            mock_research.assert_called_once_with(sample_lead, research_depth="deep")
            mock_qual.assert_called_once_with(sample_lead)

            # Verify result structure
            assert result["research_brief"] is not None
            assert result["qualification_result"] is not None
            assert result["tier"] == QualificationTier.TIER_1
            assert result["has_phone"] is True
            assert result["is_atl"] is True

    @pytest.mark.asyncio
    async def test_parallel_research_handles_research_failure(
        self, sample_lead: Lead, mock_qualification_result: dict
    ) -> None:
        """Test graceful handling when research agent fails."""
        agent = MasterOrchestratorAgent()

        with (
            patch.object(
                agent._research_agent, "run", new_callable=AsyncMock
            ) as mock_research,
            patch.object(
                agent._qualification_agent, "run", new_callable=AsyncMock
            ) as mock_qual,
        ):
            mock_research.side_effect = Exception("API timeout")
            mock_qual.return_value = mock_qualification_result

            state = {"lead": sample_lead, "process_config": {}}
            result = await agent._parallel_research_node(state)

            # Research failed but qualification succeeded
            assert result["research_brief"] is None
            assert result["qualification_result"] is not None
            assert "Research failed" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_parallel_research_handles_qualification_failure(
        self, sample_lead: Lead, mock_research_result: dict
    ) -> None:
        """Test graceful handling when qualification agent fails."""
        agent = MasterOrchestratorAgent()

        with (
            patch.object(
                agent._research_agent, "run", new_callable=AsyncMock
            ) as mock_research,
            patch.object(
                agent._qualification_agent, "run", new_callable=AsyncMock
            ) as mock_qual,
        ):
            mock_research.return_value = mock_research_result
            mock_qual.side_effect = Exception("Scoring error")

            state = {"lead": sample_lead, "process_config": {}}
            result = await agent._parallel_research_node(state)

            # Qualification failed but research succeeded
            assert result["research_brief"] is not None
            assert result["qualification_result"] is None
            assert "Qualification failed" in result["errors"][0]


class TestReviewGate1:
    """Tests for review gate 1 (data quality)."""

    @pytest.mark.asyncio
    async def test_gate_1_passes_with_complete_data(
        self, sample_lead: Lead, mock_qualification_result: dict
    ) -> None:
        """Test gate passes when data is complete."""
        agent = MasterOrchestratorAgent()

        state = {
            "lead": sample_lead,
            "qualification_result": mock_qualification_result,
            "research_brief": {"company_overview": "Test"},
            "enrichment_data": {"phone": "123"},
            "has_phone": True,
            "tier": QualificationTier.TIER_1,
        }

        result = await agent._review_gate_1_node(state)

        # Result is now a Command object with explicit routing
        assert isinstance(result, Command)
        decision = result.update["gate_1_decision"]

        assert decision["proceed"] is True
        assert "qualification_completed" in decision["passed_checks"]
        assert "research_data_available" in decision["passed_checks"]
        # Verify Command routing goes to outreach for Tier 1
        assert result.goto == "parallel_outreach"

    @pytest.mark.asyncio
    async def test_gate_1_fails_without_qualification(
        self, sample_lead: Lead
    ) -> None:
        """Test gate fails when qualification is missing."""
        agent = MasterOrchestratorAgent()

        state = {
            "lead": sample_lead,
            "qualification_result": None,
            "research_brief": {"company_overview": "Test"},
            "enrichment_data": None,
            "has_phone": False,
            "tier": None,
        }

        result = await agent._review_gate_1_node(state)

        # Result is now a Command object with explicit routing
        assert isinstance(result, Command)
        decision = result.update["gate_1_decision"]

        assert decision["proceed"] is False
        assert "qualification_missing" in decision["failed_checks"]
        # Failed gate routes to archive
        assert result.goto == "archive"

    @pytest.mark.asyncio
    async def test_gate_1_routes_not_icp_to_archive(
        self, sample_lead: Lead
    ) -> None:
        """Test not ICP leads get routed to archive."""
        agent = MasterOrchestratorAgent()

        state = {
            "lead": sample_lead,
            "qualification_result": {"tier": QualificationTier.NOT_ICP},
            "research_brief": {"company_overview": "Test"},
            "enrichment_data": None,
            "has_phone": False,
            "tier": QualificationTier.NOT_ICP,
        }

        result = await agent._review_gate_1_node(state)

        # Result is now a Command object with explicit routing
        assert isinstance(result, Command)
        decision = result.update["gate_1_decision"]

        assert decision["proceed"] is True
        assert decision["next_phase"] == "archive"
        # Command explicitly routes to archive for not ICP
        assert result.goto == "archive"


class TestTierRouting:
    """Tests for tier-based routing."""

    def test_route_tier_1_to_outreach(self) -> None:
        """Test Tier 1 leads go to outreach."""
        agent = MasterOrchestratorAgent()

        state = {
            "gate_1_decision": {"proceed": True},
            "tier": QualificationTier.TIER_1,
        }

        result = agent._route_by_tier(state)
        assert result == "tier_1"

    def test_route_tier_2_to_outreach(self) -> None:
        """Test Tier 2 leads go to outreach."""
        agent = MasterOrchestratorAgent()

        state = {
            "gate_1_decision": {"proceed": True},
            "tier": QualificationTier.TIER_2,
        }

        result = agent._route_by_tier(state)
        assert result == "tier_2"

    def test_route_not_icp_to_archive(self) -> None:
        """Test not ICP leads go to archive."""
        agent = MasterOrchestratorAgent()

        state = {
            "gate_1_decision": {"proceed": True},
            "tier": QualificationTier.NOT_ICP,
        }

        result = agent._route_by_tier(state)
        assert result == "not_icp"

    def test_route_with_failed_gate_defaults_to_not_icp(self) -> None:
        """Test failed gate routes to not ICP."""
        agent = MasterOrchestratorAgent()

        state = {
            "gate_1_decision": {"proceed": False},
            "tier": QualificationTier.TIER_1,
        }

        result = agent._route_by_tier(state)
        assert result == "not_icp"


class TestParallelOutreachPhase:
    """Tests for the parallel outreach phase."""

    @pytest.mark.asyncio
    async def test_parallel_outreach_runs_all_agents(
        self,
        sample_lead: Lead,
        mock_script_result: dict,
        mock_email_result: dict,
        mock_qualification_result: dict,
    ) -> None:
        """Test that script, email, and competitor agents run in parallel."""
        agent = MasterOrchestratorAgent()

        with (
            patch.object(
                agent._script_agent, "run", new_callable=AsyncMock
            ) as mock_script,
            patch.object(
                agent._email_agent, "run", new_callable=AsyncMock
            ) as mock_email,
        ):
            mock_script.return_value = mock_script_result
            mock_email.return_value = mock_email_result

            state = {
                "lead": sample_lead,
                "research_brief": {
                    "company_overview": "Test",
                    "recent_news": [],
                    "talking_points": [],
                    "risk_factors": [],
                    "linkedin_summary": None,
                },
                "qualification_result": mock_qualification_result,
                "phase_results": [],
                "errors": [],
            }

            result = await agent._parallel_outreach_node(state)

            # Verify script and email agents were called
            mock_script.assert_called_once()
            mock_email.assert_called_once()

            # Verify results
            assert result["script_result"] is not None
            assert result["email_result"] is not None

    @pytest.mark.asyncio
    async def test_parallel_outreach_handles_partial_failure(
        self,
        sample_lead: Lead,
        mock_script_result: dict,
        mock_qualification_result: dict,
    ) -> None:
        """Test graceful handling when some outreach agents fail."""
        agent = MasterOrchestratorAgent()

        with (
            patch.object(
                agent._script_agent, "run", new_callable=AsyncMock
            ) as mock_script,
            patch.object(
                agent._email_agent, "run", new_callable=AsyncMock
            ) as mock_email,
        ):
            mock_script.return_value = mock_script_result
            mock_email.side_effect = Exception("LLM error")

            state = {
                "lead": sample_lead,
                "research_brief": {
                    "company_overview": "Test",
                    "recent_news": [],
                    "talking_points": [],
                    "risk_factors": [],
                    "linkedin_summary": None,
                },
                "qualification_result": mock_qualification_result,
                "phase_results": [],
                "errors": [],
            }

            result = await agent._parallel_outreach_node(state)

            # Script succeeded, email failed
            assert result["script_result"] is not None
            assert result["email_result"] is None
            assert "Email generation failed" in result["errors"][0]


class TestReviewGate2:
    """Tests for review gate 2 (output quality)."""

    @pytest.mark.asyncio
    async def test_gate_2_passes_with_script(
        self, sample_lead: Lead, mock_script_result: dict
    ) -> None:
        """Test gate passes when script is generated."""
        agent = MasterOrchestratorAgent()

        state = {
            "lead": sample_lead,
            "script_result": mock_script_result,
            "email_result": None,
        }

        result = await agent._review_gate_2_node(state)

        # Result is now a Command object with explicit routing
        assert isinstance(result, Command)
        decision = result.update["gate_2_decision"]

        assert decision["proceed"] is True
        assert "script_generated" in decision["passed_checks"]
        # Command routes to sync when gate passes
        assert result.goto == "sync_to_hubspot"

    @pytest.mark.asyncio
    async def test_gate_2_passes_with_email(
        self, sample_lead: Lead, mock_email_result: dict
    ) -> None:
        """Test gate passes when email is generated."""
        agent = MasterOrchestratorAgent()

        state = {
            "lead": sample_lead,
            "script_result": None,
            "email_result": mock_email_result,
        }

        result = await agent._review_gate_2_node(state)

        # Result is now a Command object with explicit routing
        assert isinstance(result, Command)
        decision = result.update["gate_2_decision"]

        assert decision["proceed"] is True
        assert "email_generated" in decision["passed_checks"]
        # Command routes to sync when gate passes
        assert result.goto == "sync_to_hubspot"

    @pytest.mark.asyncio
    async def test_gate_2_fails_without_content(
        self, sample_lead: Lead
    ) -> None:
        """Test gate fails when no content is generated."""
        agent = MasterOrchestratorAgent()

        state = {
            "lead": sample_lead,
            "script_result": None,
            "email_result": None,
        }

        result = await agent._review_gate_2_node(state)

        # Result is now a Command object with explicit routing
        assert isinstance(result, Command)
        decision = result.update["gate_2_decision"]

        assert decision["proceed"] is False
        assert "script_missing" in decision["failed_checks"]
        assert "email_missing" in decision["failed_checks"]
        # Command routes to END when gate fails
        assert result.goto == "__end__"


class TestHelperMethods:
    """Tests for helper methods."""

    def test_extract_tier_from_enum(self) -> None:
        """Test extracting tier when it's already an enum."""
        agent = MasterOrchestratorAgent()
        result = agent._extract_tier({"tier": QualificationTier.TIER_1})
        assert result == QualificationTier.TIER_1

    def test_extract_tier_from_string(self) -> None:
        """Test extracting tier from string value."""
        agent = MasterOrchestratorAgent()
        result = agent._extract_tier({"tier": "tier_1"})
        assert result == QualificationTier.TIER_1

    def test_extract_tier_none_when_missing(self) -> None:
        """Test extracting tier returns None when missing."""
        agent = MasterOrchestratorAgent()
        result = agent._extract_tier(None)
        assert result is None

    def test_check_has_phone_true(self) -> None:
        """Test phone detection returns True when phone exists."""
        agent = MasterOrchestratorAgent()
        result = agent._check_has_phone({"enrichment_data": {"phone": "123-456"}})
        assert result is True

    def test_check_has_phone_mobile(self) -> None:
        """Test phone detection with mobile phone."""
        agent = MasterOrchestratorAgent()
        result = agent._check_has_phone({"enrichment_data": {"mobile_phone": "123-456"}})
        assert result is True

    def test_check_has_phone_false(self) -> None:
        """Test phone detection returns False when no phone."""
        agent = MasterOrchestratorAgent()
        result = agent._check_has_phone({"enrichment_data": {}})
        assert result is False

    def test_check_is_atl_true(self) -> None:
        """Test ATL detection returns True when is_atl is set."""
        agent = MasterOrchestratorAgent()
        result = agent._check_is_atl({"is_atl": True})
        assert result is True

    def test_check_is_atl_false(self) -> None:
        """Test ATL detection returns False when is_atl is not set."""
        agent = MasterOrchestratorAgent()
        result = agent._check_is_atl({})
        assert result is False

    def test_extract_persona(self) -> None:
        """Test persona extraction from qualification result."""
        agent = MasterOrchestratorAgent()
        result = agent._extract_persona({"persona_match": "AV Director"})
        assert result == "AV Director"




class TestSynthesisNode:
    """Tests for the synthesis node."""

    @pytest.fixture
    def agent(self) -> MasterOrchestratorAgent:
        """Create agent instance."""
        return MasterOrchestratorAgent()

    @pytest.mark.asyncio
    async def test_synthesis_identifies_gaps_missing_phone(
        self, agent: MasterOrchestratorAgent, sample_lead: Lead
    ) -> None:
        """Test that synthesis identifies missing phone as critical gap."""
        state = {
            "lead": sample_lead,
            "research_brief": {"company_overview": "Test company", "talking_points": []},
            "qualification_result": {"persona_match": "AV Director", "tier": "tier_1"},
            "enrichment_data": {"title": "AV Director"},
            "tier": QualificationTier.TIER_1,
            "has_phone": False,
            "phase_results": [],
        }

        result = await agent._synthesis_node(state)

        assert "synthesis" in result
        assert "missing_phone_critical" in result["synthesis"]["intelligence_gaps"]
        # Should recommend phone lookup
        actions = result["synthesis"]["recommended_actions"]
        assert any("phone" in a.lower() for a in actions)

    @pytest.mark.asyncio
    async def test_synthesis_calculates_contact_quality_high(
        self, agent: MasterOrchestratorAgent, sample_lead: Lead
    ) -> None:
        """Test high contact quality calculation."""
        state = {
            "lead": sample_lead,
            "research_brief": {"company_overview": "Test", "talking_points": ["Point 1"]},
            "qualification_result": {"persona_match": "AV Director", "tier": "tier_1"},
            "enrichment_data": {
                "title": "AV Director",
                "linkedin_url": "https://linkedin.com/in/test",
                "company": "State University",
            },
            "tier": QualificationTier.TIER_1,
            "has_phone": True,
            "phase_results": [],
        }

        result = await agent._synthesis_node(state)

        assert result["synthesis"]["contact_quality"] == "high"

    @pytest.mark.asyncio
    async def test_synthesis_calculates_contact_quality_low(
        self, agent: MasterOrchestratorAgent, sample_lead: Lead
    ) -> None:
        """Test low contact quality calculation."""
        state = {
            "lead": sample_lead,
            "research_brief": None,
            "qualification_result": None,
            "enrichment_data": None,
            "tier": None,
            "has_phone": False,
            "phase_results": [],
        }

        result = await agent._synthesis_node(state)

        assert result["synthesis"]["contact_quality"] == "low"

    @pytest.mark.asyncio
    async def test_synthesis_identifies_multiple_gaps(
        self, agent: MasterOrchestratorAgent, sample_lead: Lead
    ) -> None:
        """Test identifying multiple intelligence gaps."""
        state = {
            "lead": sample_lead,
            "research_brief": None,
            "qualification_result": None,
            "enrichment_data": {"company": "Test"},  # Missing title and industry
            "tier": None,
            "has_phone": False,
            "phase_results": [],
        }

        result = await agent._synthesis_node(state)

        gaps = result["synthesis"]["intelligence_gaps"]
        assert "missing_research_brief" in gaps
        assert "missing_qualification" in gaps
        assert "missing_phone_critical" in gaps
        assert "missing_title" in gaps
        assert "missing_industry" in gaps

    @pytest.mark.asyncio
    async def test_synthesis_confidence_score_calculation(
        self, agent: MasterOrchestratorAgent, sample_lead: Lead
    ) -> None:
        """Test confidence score calculation."""
        # High data quality should yield higher confidence
        high_quality_state = {
            "lead": sample_lead,
            "research_brief": {"company_overview": "Test", "talking_points": ["Point"]},
            "qualification_result": {"persona_match": "AV Director"},
            "enrichment_data": {"title": "AV Director"},
            "tier": QualificationTier.TIER_1,
            "has_phone": True,
            "phase_results": [],
        }

        # Low data quality should yield lower confidence
        low_quality_state = {
            "lead": sample_lead,
            "research_brief": None,
            "qualification_result": None,
            "enrichment_data": None,
            "tier": None,
            "has_phone": False,
            "phase_results": [],
        }

        high_result = await agent._synthesis_node(high_quality_state)
        low_result = await agent._synthesis_node(low_quality_state)

        assert high_result["synthesis"]["confidence_score"] > low_result["synthesis"]["confidence_score"]

    @pytest.mark.asyncio
    async def test_synthesis_tier_1_priority_action(
        self, agent: MasterOrchestratorAgent, sample_lead: Lead
    ) -> None:
        """Test that Tier 1 leads get priority action recommendation."""
        state = {
            "lead": sample_lead,
            "research_brief": {"company_overview": "Test"},
            "qualification_result": {"persona_match": "AV Director"},
            "enrichment_data": {"title": "AV Director"},
            "tier": QualificationTier.TIER_1,
            "has_phone": True,
            "phase_results": [],
        }

        result = await agent._synthesis_node(state)

        actions = result["synthesis"]["recommended_actions"]
        # First action should be priority for Tier 1
        assert "PRIORITY" in actions[0] or "priority" in actions[0].lower()

    @pytest.mark.asyncio
    async def test_synthesis_not_icp_archive_action(
        self, agent: MasterOrchestratorAgent, sample_lead: Lead
    ) -> None:
        """Test that NOT_ICP leads get archive recommendation."""
        state = {
            "lead": sample_lead,
            "research_brief": {"company_overview": "Test"},
            "qualification_result": {},
            "enrichment_data": {},
            "tier": QualificationTier.NOT_ICP,
            "has_phone": False,
            "phase_results": [],
        }

        result = await agent._synthesis_node(state)

        actions = result["synthesis"]["recommended_actions"]
        assert any("archive" in a.lower() for a in actions)

    @pytest.mark.asyncio
    async def test_synthesis_adds_phase_result(
        self, agent: MasterOrchestratorAgent, sample_lead: Lead
    ) -> None:
        """Test that synthesis adds phase result to tracking."""
        state = {
            "lead": sample_lead,
            "research_brief": {},
            "qualification_result": {},
            "enrichment_data": {},
            "tier": QualificationTier.TIER_2,
            "has_phone": False,
            "phase_results": [],
        }

        result = await agent._synthesis_node(state)

        assert len(result["phase_results"]) == 1
        assert result["phase_results"][0]["phase_name"] == "synthesis"
        assert result["phase_results"][0]["status"] == "success"

class TestCompetitorCheck:
    """Tests for competitor signal detection."""

    @pytest.mark.asyncio
    async def test_detects_zoom_competitor(self) -> None:
        """Test detection of Zoom competitor signal."""
        agent = MasterOrchestratorAgent()

        mock_lead = MagicMock()
        research_brief = {
            "company_overview": "Test",
            "recent_news": [],
            "talking_points": ["Currently using Zoom for meetings"],
            "risk_factors": [],
            "linkedin_summary": None,
        }

        result = await agent._run_competitor_check(mock_lead, research_brief)

        assert result is not None
        assert result["has_competitor"] is True
        assert len(result["signals"]) > 0

    @pytest.mark.asyncio
    async def test_no_competitor_when_no_signals(self) -> None:
        """Test returns None when no competitor signals."""
        agent = MasterOrchestratorAgent()

        mock_lead = MagicMock()
        research_brief = {
            "company_overview": "Test",
            "recent_news": [],
            "talking_points": ["Enterprise customer"],
            "risk_factors": [],
            "linkedin_summary": None,
        }

        result = await agent._run_competitor_check(mock_lead, research_brief)
        assert result is None


class TestFullOrchestration:
    """Integration tests for full orchestration flow."""

    @pytest.mark.asyncio
    async def test_full_flow_tier_1_lead(
        self,
        sample_lead: Lead,
        mock_research_result: dict,
        mock_qualification_result: dict,
        mock_script_result: dict,
        mock_email_result: dict,
    ) -> None:
        """Test complete orchestration flow for a Tier 1 lead."""
        agent = MasterOrchestratorAgent()

        with (
            patch.object(
                agent._research_agent, "run", new_callable=AsyncMock
            ) as mock_research,
            patch.object(
                agent._qualification_agent, "run", new_callable=AsyncMock
            ) as mock_qual,
            patch.object(
                agent._script_agent, "run", new_callable=AsyncMock
            ) as mock_script,
            patch.object(
                agent._email_agent, "run", new_callable=AsyncMock
            ) as mock_email,
        ):
            mock_research.return_value = mock_research_result
            mock_qual.return_value = mock_qualification_result
            mock_script.return_value = mock_script_result
            mock_email.return_value = mock_email_result

            result = await agent.run(sample_lead)

            # Verify all phases completed
            assert result["lead_id"] == sample_lead.hubspot_id
            assert result["tier"] == "tier_1"
            assert result["is_atl"] is True
            assert result["research_brief"] is not None
            assert result["script_result"] is not None
            assert result["email_result"] is not None

            # Verify gates passed
            assert result["gate_decisions"]["gate_1"]["proceed"] is True
            assert result["gate_decisions"]["gate_2"]["proceed"] is True

    @pytest.mark.asyncio
    async def test_full_flow_not_icp_skips_outreach(
        self,
        sample_lead: Lead,
        mock_research_result: dict,
    ) -> None:
        """Test not ICP leads skip outreach phase."""
        agent = MasterOrchestratorAgent()

        not_icp_qualification = {
            "tier": QualificationTier.NOT_ICP,
            "is_atl": False,
            "persona_match": None,
            "total_score": 20,
        }

        with (
            patch.object(
                agent._research_agent, "run", new_callable=AsyncMock
            ) as mock_research,
            patch.object(
                agent._qualification_agent, "run", new_callable=AsyncMock
            ) as mock_qual,
            patch.object(
                agent._script_agent, "run", new_callable=AsyncMock
            ) as mock_script,
            patch.object(
                agent._email_agent, "run", new_callable=AsyncMock
            ) as mock_email,
        ):
            mock_research.return_value = mock_research_result
            mock_qual.return_value = not_icp_qualification

            result = await agent.run(sample_lead)

            # Verify archived
            assert result["tier"] == "not_icp"
            assert result["hubspot_sync_result"]["status"] == "archived"

            # Verify outreach agents NOT called
            mock_script.assert_not_called()
            mock_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_flow_tracks_duration(
        self,
        sample_lead: Lead,
        mock_research_result: dict,
        mock_qualification_result: dict,
        mock_script_result: dict,
        mock_email_result: dict,
    ) -> None:
        """Test that duration is tracked across phases."""
        agent = MasterOrchestratorAgent()

        with (
            patch.object(
                agent._research_agent, "run", new_callable=AsyncMock
            ) as mock_research,
            patch.object(
                agent._qualification_agent, "run", new_callable=AsyncMock
            ) as mock_qual,
            patch.object(
                agent._script_agent, "run", new_callable=AsyncMock
            ) as mock_script,
            patch.object(
                agent._email_agent, "run", new_callable=AsyncMock
            ) as mock_email,
        ):
            mock_research.return_value = mock_research_result
            mock_qual.return_value = mock_qualification_result
            mock_script.return_value = mock_script_result
            mock_email.return_value = mock_email_result

            result = await agent.run(sample_lead)

            # Verify timing is tracked
            assert result["total_duration_ms"] > 0
            assert len(result["phase_results"]) >= 2  # At least research and outreach
            for phase in result["phase_results"]:
                assert phase["duration_ms"] >= 0
