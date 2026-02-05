"""Tests for semantic memory activation in orchestrator.

Tests cover:
- Querying similar patterns during research phase
- Storing successful patterns after sync
- Memory integration with orchestrator
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.data.lead_schemas import Lead
from app.services.langgraph.states import QualificationTier


class TestSemanticMemoryIntegration:
    """Tests for semantic memory integration with orchestrator."""

    @pytest.fixture
    def sample_lead(self) -> Lead:
        """Create a sample lead for testing."""
        return Lead(
            hubspot_id="memory-test-123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            company="Test Company",
            title="AV Director",
            industry="Higher Education",
        )

    @pytest.mark.asyncio
    async def test_orchestrator_has_memory_attribute(self) -> None:
        """Test that orchestrator initializes with memory."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent

        orchestrator = MasterOrchestratorAgent()

        assert hasattr(orchestrator, "_memory")
        assert orchestrator._memory is not None

    @pytest.mark.asyncio
    async def test_parallel_research_queries_similar_patterns(
        self, sample_lead: Lead
    ) -> None:
        """Test that parallel_research node queries semantic memory."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent
        from app.services.langgraph.states import OrchestratorState

        orchestrator = MasterOrchestratorAgent()

        # Mock the memory's find_similar_patterns
        mock_patterns = [
            {"tier": "TIER_1", "persona": "AV Director", "score_breakdown": {}},
        ]
        orchestrator._memory = MagicMock()
        orchestrator._memory.find_similar_patterns = AsyncMock(return_value=mock_patterns)

        # Mock the sub-agents
        orchestrator._research_agent = MagicMock()
        orchestrator._research_agent.run = AsyncMock(return_value={
            "research_brief": {"company_overview": "Test company"},
            "enrichment_data": {},
        })
        orchestrator._qualification_agent = MagicMock()
        orchestrator._qualification_agent.run = AsyncMock(return_value={
            "tier": QualificationTier.TIER_1,
            "score_breakdown": {},
        })

        state: OrchestratorState = {
            "lead": sample_lead,
            "process_config": {},
            "research_brief": None,
            "qualification_result": None,
            "enrichment_data": None,
            "synthesis": None,
            "gate_1_decision": None,
            "script_result": None,
            "email_result": None,
            "competitor_intel": None,
            "gate_2_decision": None,
            "hubspot_sync_result": None,
            "current_phase": "research",
            "phase_results": [],
            "total_duration_ms": 0.0,
            "errors": [],
            "tier": None,
            "has_phone": False,
            "is_atl": False,
        }

        result = await orchestrator._parallel_research_node(state)

        # Verify memory was queried
        orchestrator._memory.find_similar_patterns.assert_called_once()
        call_args = orchestrator._memory.find_similar_patterns.call_args
        assert "Test Company" in call_args.kwargs.get("query", "")
        assert "AV Director" in call_args.kwargs.get("query", "")
        assert call_args.kwargs.get("limit") == 3

        # Phase data should include similar_patterns_found
        phase_result = result["phase_results"][0]
        assert phase_result["data"]["similar_patterns_found"] == 1

    @pytest.mark.asyncio
    async def test_parallel_research_handles_memory_failure(
        self, sample_lead: Lead
    ) -> None:
        """Test that research continues if memory query fails."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent
        from app.services.langgraph.states import OrchestratorState

        orchestrator = MasterOrchestratorAgent()

        # Mock memory to raise exception
        orchestrator._memory = MagicMock()
        orchestrator._memory.find_similar_patterns = AsyncMock(
            side_effect=Exception("Memory unavailable")
        )

        # Mock the sub-agents
        orchestrator._research_agent = MagicMock()
        orchestrator._research_agent.run = AsyncMock(return_value={
            "research_brief": {"company_overview": "Test"},
        })
        orchestrator._qualification_agent = MagicMock()
        orchestrator._qualification_agent.run = AsyncMock(return_value={
            "tier": QualificationTier.TIER_2,
        })

        state: OrchestratorState = {
            "lead": sample_lead,
            "process_config": {},
            "research_brief": None,
            "qualification_result": None,
            "enrichment_data": None,
            "synthesis": None,
            "gate_1_decision": None,
            "script_result": None,
            "email_result": None,
            "competitor_intel": None,
            "gate_2_decision": None,
            "hubspot_sync_result": None,
            "current_phase": "research",
            "phase_results": [],
            "total_duration_ms": 0.0,
            "errors": [],
            "tier": None,
            "has_phone": False,
            "is_atl": False,
        }

        # Should not raise, memory failure is non-fatal
        result = await orchestrator._parallel_research_node(state)

        # Research should still complete
        assert result["research_brief"] is not None
        # similar_patterns_found should be 0 due to failure
        phase_result = result["phase_results"][0]
        assert phase_result["data"]["similar_patterns_found"] == 0


class TestSyncNodeMemorySave:
    """Tests for saving patterns in sync node."""

    @pytest.fixture
    def sample_lead(self) -> Lead:
        """Create a sample lead for testing."""
        return Lead(
            hubspot_id="sync-test-123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            company="Test Company",
        )

    @pytest.mark.asyncio
    async def test_sync_saves_tier_1_pattern(self, sample_lead: Lead) -> None:
        """Test that sync node saves Tier 1 patterns to memory."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent
        from app.services.langgraph.states import OrchestratorState

        orchestrator = MasterOrchestratorAgent()

        # Mock the memory
        orchestrator._memory = MagicMock()
        orchestrator._memory.save_qualification_pattern = AsyncMock()

        state: OrchestratorState = {
            "lead": sample_lead,
            "process_config": {},
            "research_brief": {"company_overview": "Test"},
            "qualification_result": {
                "tier": QualificationTier.TIER_1,
                "score_breakdown": {"company_size": {"raw_score": 10}},
                "persona_match": "AV Director",
            },
            "enrichment_data": None,
            "synthesis": None,
            "gate_1_decision": {"proceed": True},
            "script_result": {"personalized_script": "Test script"},
            "email_result": {"subject_line": "Test subject"},
            "competitor_intel": None,
            "gate_2_decision": {"proceed": True},
            "hubspot_sync_result": None,
            "current_phase": "sync",
            "phase_results": [],
            "total_duration_ms": 0.0,
            "errors": [],
            "tier": QualificationTier.TIER_1,
            "has_phone": True,
            "is_atl": True,
        }

        await orchestrator._sync_node(state)

        # Verify pattern was saved
        orchestrator._memory.save_qualification_pattern.assert_called_once()
        call_args = orchestrator._memory.save_qualification_pattern.call_args

        assert call_args.kwargs["tier"] == "tier_1"
        assert call_args.kwargs["persona"] == "AV Director"
        assert "has_phone" in call_args.kwargs["success_indicators"]
        assert "is_atl_decision_maker" in call_args.kwargs["success_indicators"]
        assert "email_generated" in call_args.kwargs["success_indicators"]
        assert "script_generated" in call_args.kwargs["success_indicators"]

    @pytest.mark.asyncio
    async def test_sync_saves_tier_2_pattern(self, sample_lead: Lead) -> None:
        """Test that sync node saves Tier 2 patterns to memory."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent
        from app.services.langgraph.states import OrchestratorState

        orchestrator = MasterOrchestratorAgent()
        orchestrator._memory = MagicMock()
        orchestrator._memory.save_qualification_pattern = AsyncMock()

        state: OrchestratorState = {
            "lead": sample_lead,
            "process_config": {},
            "research_brief": None,
            "qualification_result": {
                "tier": QualificationTier.TIER_2,
                "score_breakdown": {},
                "persona_match": "L&D Director",
            },
            "enrichment_data": None,
            "synthesis": None,
            "gate_1_decision": {"proceed": True},
            "script_result": None,
            "email_result": None,
            "competitor_intel": None,
            "gate_2_decision": {"proceed": True},
            "hubspot_sync_result": None,
            "current_phase": "sync",
            "phase_results": [],
            "total_duration_ms": 0.0,
            "errors": [],
            "tier": QualificationTier.TIER_2,
            "has_phone": False,
            "is_atl": False,
        }

        await orchestrator._sync_node(state)

        # Verify pattern was saved for Tier 2
        orchestrator._memory.save_qualification_pattern.assert_called_once()
        call_args = orchestrator._memory.save_qualification_pattern.call_args
        assert call_args.kwargs["tier"] == "tier_2"

    @pytest.mark.asyncio
    async def test_sync_does_not_save_tier_3_pattern(self, sample_lead: Lead) -> None:
        """Test that sync node does NOT save Tier 3 patterns."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent
        from app.services.langgraph.states import OrchestratorState

        orchestrator = MasterOrchestratorAgent()
        orchestrator._memory = MagicMock()
        orchestrator._memory.save_qualification_pattern = AsyncMock()

        state: OrchestratorState = {
            "lead": sample_lead,
            "process_config": {},
            "research_brief": None,
            "qualification_result": {"tier": QualificationTier.TIER_3},
            "enrichment_data": None,
            "synthesis": None,
            "gate_1_decision": {"proceed": True},
            "script_result": None,
            "email_result": None,
            "competitor_intel": None,
            "gate_2_decision": {"proceed": True},
            "hubspot_sync_result": None,
            "current_phase": "sync",
            "phase_results": [],
            "total_duration_ms": 0.0,
            "errors": [],
            "tier": QualificationTier.TIER_3,
            "has_phone": False,
            "is_atl": False,
        }

        await orchestrator._sync_node(state)

        # Tier 3 should NOT be saved
        orchestrator._memory.save_qualification_pattern.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_does_not_save_not_icp_pattern(self, sample_lead: Lead) -> None:
        """Test that sync node does NOT save NOT_ICP patterns."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent
        from app.services.langgraph.states import OrchestratorState

        orchestrator = MasterOrchestratorAgent()
        orchestrator._memory = MagicMock()
        orchestrator._memory.save_qualification_pattern = AsyncMock()

        state: OrchestratorState = {
            "lead": sample_lead,
            "process_config": {},
            "research_brief": None,
            "qualification_result": {"tier": QualificationTier.NOT_ICP},
            "enrichment_data": None,
            "synthesis": None,
            "gate_1_decision": {"proceed": False},
            "script_result": None,
            "email_result": None,
            "competitor_intel": None,
            "gate_2_decision": None,
            "hubspot_sync_result": None,
            "current_phase": "sync",
            "phase_results": [],
            "total_duration_ms": 0.0,
            "errors": [],
            "tier": QualificationTier.NOT_ICP,
            "has_phone": False,
            "is_atl": False,
        }

        await orchestrator._sync_node(state)

        # NOT_ICP should NOT be saved
        orchestrator._memory.save_qualification_pattern.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_handles_memory_save_failure(self, sample_lead: Lead) -> None:
        """Test that sync continues if memory save fails."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent
        from app.services.langgraph.states import OrchestratorState

        orchestrator = MasterOrchestratorAgent()
        orchestrator._memory = MagicMock()
        orchestrator._memory.save_qualification_pattern = AsyncMock(
            side_effect=Exception("Memory save failed")
        )

        state: OrchestratorState = {
            "lead": sample_lead,
            "process_config": {},
            "research_brief": None,
            "qualification_result": {"tier": QualificationTier.TIER_1},
            "enrichment_data": None,
            "synthesis": None,
            "gate_1_decision": {"proceed": True},
            "script_result": None,
            "email_result": None,
            "competitor_intel": None,
            "gate_2_decision": {"proceed": True},
            "hubspot_sync_result": None,
            "current_phase": "sync",
            "phase_results": [],
            "total_duration_ms": 0.0,
            "errors": [],
            "tier": QualificationTier.TIER_1,
            "has_phone": False,
            "is_atl": False,
        }

        # Should not raise - memory failure is non-fatal
        result = await orchestrator._sync_node(state)

        # Sync should still complete
        assert result["hubspot_sync_result"] is not None
        assert result["hubspot_sync_result"]["status"] == "ready_for_sync"


class TestSemanticMemoryUnit:
    """Unit tests for SemanticMemory class."""

    @pytest.mark.asyncio
    async def test_put_and_get_in_memory_fallback(self) -> None:
        """Test put and get with in-memory fallback."""
        from app.services.langgraph.memory.semantic_store import SemanticMemory

        memory = SemanticMemory()
        memory._use_postgres = False  # Force in-memory mode

        await memory.put(
            namespace=("test", "patterns"),
            key="test-key",
            value={"data": "test-value"},
        )

        result = await memory.get(
            namespace=("test", "patterns"),
            key="test-key",
        )

        assert result is not None
        assert result["data"] == "test-value"

    @pytest.mark.asyncio
    async def test_search_returns_entries(self) -> None:
        """Test search returns stored entries."""
        from app.services.langgraph.memory.semantic_store import SemanticMemory

        memory = SemanticMemory()
        memory._use_postgres = False

        await memory.put(
            namespace=("search", "test"),
            key="entry-1",
            value={"name": "First Entry"},
        )
        await memory.put(
            namespace=("search", "test"),
            key="entry-2",
            value={"name": "Second Entry"},
        )

        results = await memory.search(
            namespace=("search", "test"),
            limit=5,
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_delete_removes_entry(self) -> None:
        """Test delete removes stored entry."""
        from app.services.langgraph.memory.semantic_store import SemanticMemory

        memory = SemanticMemory()
        memory._use_postgres = False

        await memory.put(
            namespace=("delete", "test"),
            key="to-delete",
            value={"data": "delete me"},
        )

        deleted = await memory.delete(
            namespace=("delete", "test"),
            key="to-delete",
        )

        assert deleted is True

        result = await memory.get(
            namespace=("delete", "test"),
            key="to-delete",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_save_qualification_pattern(self) -> None:
        """Test save_qualification_pattern convenience method."""
        from app.services.langgraph.memory.semantic_store import SemanticMemory

        memory = SemanticMemory()
        memory._use_postgres = False

        await memory.save_qualification_pattern(
            tier="TIER_1",
            persona="AV Director",
            score_breakdown={"company_size": 10},
            success_indicators=["has_phone", "is_atl"],
        )

        results = await memory.search(
            namespace=("qualification", "patterns"),
            limit=1,
        )

        assert len(results) == 1
        assert results[0]["tier"] == "TIER_1"
        assert results[0]["persona"] == "AV Director"
        assert "has_phone" in results[0]["success_indicators"]

    @pytest.mark.asyncio
    async def test_save_email_success(self) -> None:
        """Test save_email_success convenience method."""
        from app.services.langgraph.memory.semantic_store import SemanticMemory

        memory = SemanticMemory()
        memory._use_postgres = False

        await memory.save_email_success(
            persona="AV Director",
            email_type="pattern_interrupt",
            subject_line="Quick question about video",
            opening_hook="I noticed your recent webinar...",
            response_rate=0.15,
        )

        results = await memory.search(
            namespace=("email", "successes"),
            limit=1,
        )

        assert len(results) == 1
        assert results[0]["persona"] == "AV Director"
        assert results[0]["email_type"] == "pattern_interrupt"
        assert results[0]["response_rate"] == 0.15


class TestMemoryTimestamps:
    """Tests for timezone-aware timestamps in memory."""

    @pytest.mark.asyncio
    async def test_memory_uses_utc_timestamps(self) -> None:
        """Test that memory entries use UTC timestamps."""
        from app.services.langgraph.memory.semantic_store import SemanticMemory

        memory = SemanticMemory()
        memory._use_postgres = False

        await memory.put(
            namespace=("timestamp", "test"),
            key="entry",
            value={"data": "test"},
        )

        # Access internal store to check timestamp
        entry = memory._memory_store[("timestamp", "test")]["entry"]
        timestamp = entry["created_at"]

        # Verify it's an ISO timestamp
        assert "T" in timestamp
        # Parse to verify format
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
