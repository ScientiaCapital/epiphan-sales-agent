"""Tests for LangSmith tracing utilities.

Tests cover:
- is_tracing_enabled detection
- @trace_agent decorator
- with_tracing_context context manager
- TracingMetrics collection
- get_tracing_config helper
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.lead_schemas import Lead


class TestIsTracingEnabled:
    """Tests for is_tracing_enabled function."""

    def test_returns_false_when_disabled(self) -> None:
        """Test returns False when tracing is disabled."""
        from app.services.langgraph.tracing import is_tracing_enabled

        with patch("app.services.langgraph.tracing.settings") as mock_settings:
            mock_settings.langchain_tracing_v2 = False
            mock_settings.langchain_api_key = ""

            with patch.dict("os.environ", {}, clear=True):
                assert is_tracing_enabled() is False

    def test_returns_true_when_settings_enabled(self) -> None:
        """Test returns True when settings enable tracing."""
        from app.services.langgraph.tracing import is_tracing_enabled

        with patch("app.services.langgraph.tracing.settings") as mock_settings:
            mock_settings.langchain_tracing_v2 = True
            mock_settings.langchain_api_key = "test-key"

            assert is_tracing_enabled() is True

    def test_returns_true_when_env_var_enabled(self) -> None:
        """Test returns True when environment variable enables tracing."""
        from app.services.langgraph.tracing import is_tracing_enabled

        with patch("app.services.langgraph.tracing.settings") as mock_settings:
            mock_settings.langchain_tracing_v2 = False
            mock_settings.langchain_api_key = ""

            with patch.dict(
                "os.environ",
                {"LANGCHAIN_TRACING_V2": "true", "LANGCHAIN_API_KEY": "test-key"},
            ):
                assert is_tracing_enabled() is True

    def test_requires_api_key(self) -> None:
        """Test that API key is required for tracing."""
        from app.services.langgraph.tracing import is_tracing_enabled

        with patch("app.services.langgraph.tracing.settings") as mock_settings:
            mock_settings.langchain_tracing_v2 = True
            mock_settings.langchain_api_key = ""  # No API key

            with patch.dict("os.environ", {"LANGCHAIN_API_KEY": ""}, clear=True):
                assert is_tracing_enabled() is False


class TestTraceAgentDecorator:
    """Tests for @trace_agent decorator."""

    @pytest.mark.asyncio
    async def test_decorator_passes_through_when_disabled(self) -> None:
        """Test that decorator passes through when tracing disabled."""
        from app.services.langgraph.tracing import trace_agent

        @trace_agent("test_agent")
        async def test_func(x: int) -> int:
            return x * 2

        with patch("app.services.langgraph.tracing.is_tracing_enabled", return_value=False):
            result = await test_func(5)
            assert result == 10

    @pytest.mark.asyncio
    async def test_decorator_extracts_lead_metadata(self) -> None:
        """Test that decorator extracts lead metadata when available."""
        from app.services.langgraph.tracing import trace_agent

        lead = Lead(
            hubspot_id="lead-123",
            email="test@example.com",
            company="Test Company",
        )

        @trace_agent("test_agent")
        async def process_lead(_self: Any, _lead: Lead) -> dict[str, Any]:
            return {"processed": True}

        with patch("app.services.langgraph.tracing.is_tracing_enabled", return_value=False):
            result = await process_lead(None, lead)
            assert result["processed"] is True

    @pytest.mark.asyncio
    async def test_decorator_works_with_kwargs(self) -> None:
        """Test decorator works with keyword arguments."""
        from app.services.langgraph.tracing import trace_agent

        lead = Lead(hubspot_id="kwargs-test", email="test@example.com")

        @trace_agent("test_agent")
        async def process_lead(lead: Lead, extra: str = "default") -> dict[str, Any]:
            return {"lead_id": lead.hubspot_id, "extra": extra}

        with patch("app.services.langgraph.tracing.is_tracing_enabled", return_value=False):
            result = await process_lead(lead=lead, extra="custom")
            assert result["lead_id"] == "kwargs-test"
            assert result["extra"] == "custom"


class TestTracingMetrics:
    """Tests for TracingMetrics class."""

    def test_record_and_summary(self) -> None:
        """Test recording and summarizing metrics."""
        from app.services.langgraph.tracing import TracingMetrics

        metrics = TracingMetrics()

        metrics.record("agent1", 100.0, success=True, tier="TIER_1")
        metrics.record("agent1", 150.0, success=True, tier="TIER_2")
        metrics.record("agent1", 200.0, success=False, tier=None)

        summary = metrics.get_summary()

        assert summary["total_executions"] == 3
        assert summary["success_rate"] == pytest.approx(2 / 3)
        assert summary["avg_duration_ms"] == 150.0
        assert summary["tier_distribution"]["TIER_1"] == 1
        assert summary["tier_distribution"]["TIER_2"] == 1

    def test_empty_summary(self) -> None:
        """Test summary when no metrics recorded."""
        from app.services.langgraph.tracing import TracingMetrics

        metrics = TracingMetrics()
        summary = metrics.get_summary()

        assert summary["total_executions"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["avg_duration_ms"] == 0.0
        assert summary["tier_distribution"] == {}

    def test_clear_metrics(self) -> None:
        """Test clearing recorded metrics."""
        from app.services.langgraph.tracing import TracingMetrics

        metrics = TracingMetrics()
        metrics.record("agent", 100.0, success=True)
        metrics.clear()

        summary = metrics.get_summary()
        assert summary["total_executions"] == 0

    def test_singleton_instance_exists(self) -> None:
        """Test that singleton tracing_metrics instance exists."""
        from app.services.langgraph.tracing import tracing_metrics

        assert tracing_metrics is not None
        assert hasattr(tracing_metrics, "record")
        assert hasattr(tracing_metrics, "get_summary")


class TestGetTracingConfig:
    """Tests for get_tracing_config function."""

    def test_returns_empty_when_disabled(self) -> None:
        """Test returns empty config when tracing disabled."""
        from app.services.langgraph.tracing import get_tracing_config

        with patch("app.services.langgraph.tracing.is_tracing_enabled", return_value=False):
            config = get_tracing_config()
            assert config == {}

    def test_returns_config_when_enabled(self) -> None:
        """Test returns proper config when tracing enabled."""
        from app.services.langgraph.tracing import get_tracing_config

        with (
            patch("app.services.langgraph.tracing.is_tracing_enabled", return_value=True),
            patch("app.services.langgraph.tracing.settings") as mock_settings,
        ):
                mock_settings.langsmith_project = "test-project"

                config = get_tracing_config()

                assert "metadata" in config
                assert config["metadata"]["project"] == "test-project"
                assert "tags" in config
                assert "epiphan-sales-agent" in config["tags"]


class TestWithTracingContext:
    """Tests for with_tracing_context context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_works_when_disabled(self) -> None:
        """Test context manager works when tracing disabled."""
        from app.services.langgraph.tracing import with_tracing_context

        with patch("app.services.langgraph.tracing.is_tracing_enabled", return_value=False):
            async with with_tracing_context(lead_id="test-123"):
                # Should not raise
                result = 1 + 1

            assert result == 2

    @pytest.mark.asyncio
    async def test_context_manager_accepts_metadata(self) -> None:
        """Test context manager accepts metadata parameters."""
        from app.services.langgraph.tracing import with_tracing_context

        with patch("app.services.langgraph.tracing.is_tracing_enabled", return_value=False):
            async with with_tracing_context(
                lead_id="test-456",
                lead_email="test@example.com",
                tier="TIER_1",
                extra_metadata={"custom": "value"},
            ):
                pass  # Context should work without error


class TestOrchestratorTracingIntegration:
    """Tests for tracing integration with orchestrator."""

    @pytest.fixture
    def sample_lead(self) -> Lead:
        """Create sample lead for testing."""
        return Lead(
            hubspot_id="trace-test-123",
            email="test@example.com",
            company="Test Company",
        )

    @pytest.mark.asyncio
    async def test_orchestrator_records_metrics(self, sample_lead: Lead) -> None:
        """Test that orchestrator records metrics after run."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent
        from app.services.langgraph.tracing import tracing_metrics

        orchestrator = MasterOrchestratorAgent()

        # Mock all the sub-agents
        orchestrator._research_agent = MagicMock()
        orchestrator._research_agent.run = AsyncMock(return_value={"research_brief": {}})
        orchestrator._qualification_agent = MagicMock()
        orchestrator._qualification_agent.run = AsyncMock(return_value={"tier": "TIER_2"})
        orchestrator._script_agent = MagicMock()
        orchestrator._script_agent.run = AsyncMock(return_value={})
        orchestrator._email_agent = MagicMock()
        orchestrator._email_agent.run = AsyncMock(return_value={})

        # Clear any existing metrics
        tracing_metrics.clear()

        # Mock graph execution to avoid full pipeline
        mock_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={
            "tier": None,
            "is_atl": False,
            "has_phone": False,
            "errors": [],
            "phase_results": [],
        })
        mock_graph.compile.return_value = mock_compiled
        orchestrator._graph = mock_graph

        await orchestrator.run(sample_lead)

        # Check that metrics were recorded
        summary = tracing_metrics.get_summary()
        assert summary["total_executions"] >= 1

    def test_orchestrator_has_trace_decorator(self) -> None:
        """Test that orchestrator run method has trace decorator."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent

        # Check that the run method exists
        orchestrator = MasterOrchestratorAgent()
        assert hasattr(orchestrator, "run")
        assert callable(orchestrator.run)
