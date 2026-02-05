"""Tests for Agent Telemetry.

Tests the metrics collection and observability features.
"""

import pytest

from app.services.langgraph.telemetry import (
    AgentTelemetry,
    ExecutionTrace,
    PhaseMetrics,
    agent_telemetry,
)


class TestPhaseMetrics:
    """Tests for PhaseMetrics dataclass."""

    def test_phase_metrics_defaults(self) -> None:
        """Test PhaseMetrics has correct defaults."""
        phase = PhaseMetrics(phase_name="test")
        assert phase.status == "pending"
        assert phase.duration_ms == 0.0
        assert phase.error_message is None

    def test_phase_start(self) -> None:
        """Test marking phase as started."""
        phase = PhaseMetrics(phase_name="test")
        phase.start()
        assert phase.status == "running"
        assert phase.start_time > 0

    def test_phase_complete(self) -> None:
        """Test marking phase as completed."""
        phase = PhaseMetrics(phase_name="test")
        phase.start()
        phase.complete({"api_calls": 2})

        assert phase.status == "success"
        assert phase.duration_ms >= 0
        assert phase.metadata["api_calls"] == 2

    def test_phase_fail(self) -> None:
        """Test marking phase as failed."""
        phase = PhaseMetrics(phase_name="test")
        phase.start()
        phase.fail("Connection timeout", {"retry_count": 3})

        assert phase.status == "error"
        assert phase.error_message == "Connection timeout"
        assert phase.metadata["retry_count"] == 3


class TestExecutionTrace:
    """Tests for ExecutionTrace dataclass."""

    def test_trace_creation(self) -> None:
        """Test creating an execution trace."""
        trace = ExecutionTrace(
            trace_id="test-001",
            agent_name="orchestrator",
            lead_id="hs-123",
        )

        assert trace.trace_id == "test-001"
        assert trace.agent_name == "orchestrator"
        assert trace.lead_id == "hs-123"
        assert trace.status == "running"
        assert len(trace.phases) == 0

    def test_add_phase(self) -> None:
        """Test adding phases to trace."""
        trace = ExecutionTrace(
            trace_id="test-001",
            agent_name="orchestrator",
        )

        phase = trace.add_phase("research")
        phase.start()
        phase.complete()

        assert len(trace.phases) == 1
        assert trace.phases[0].phase_name == "research"

    def test_trace_complete(self) -> None:
        """Test completing a trace."""
        trace = ExecutionTrace(
            trace_id="test-001",
            agent_name="orchestrator",
        )

        phase1 = trace.add_phase("research")
        phase1.start()
        phase1.complete()

        phase2 = trace.add_phase("outreach")
        phase2.start()
        phase2.complete()

        trace.complete({"lead_tier": "tier_1"})

        assert trace.status == "success"
        assert trace.end_time is not None
        assert trace.total_duration_ms >= 0
        assert trace.metadata["lead_tier"] == "tier_1"

    def test_trace_partial_status(self) -> None:
        """Test trace with mixed phase results."""
        trace = ExecutionTrace(
            trace_id="test-001",
            agent_name="orchestrator",
        )

        phase1 = trace.add_phase("research")
        phase1.start()
        phase1.complete()

        phase2 = trace.add_phase("outreach")
        phase2.start()
        phase2.fail("LLM error")

        trace.complete()

        assert trace.status == "partial"

    def test_trace_to_dict(self) -> None:
        """Test serializing trace to dict."""
        trace = ExecutionTrace(
            trace_id="test-001",
            agent_name="orchestrator",
            lead_id="hs-123",
        )

        phase = trace.add_phase("research")
        phase.start()
        phase.complete()
        trace.complete()

        data = trace.to_dict()

        assert data["trace_id"] == "test-001"
        assert data["agent_name"] == "orchestrator"
        assert data["lead_id"] == "hs-123"
        assert len(data["phases"]) == 1
        assert data["phases"][0]["phase_name"] == "research"


class TestAgentTelemetry:
    """Tests for AgentTelemetry collector."""

    @pytest.fixture
    def telemetry(self) -> AgentTelemetry:
        """Create a fresh telemetry instance."""
        return AgentTelemetry(max_traces=100)

    def test_start_trace(self, telemetry: AgentTelemetry) -> None:
        """Test starting a new trace."""
        trace = telemetry.start_trace(
            agent_name="orchestrator",
            lead_id="hs-123",
            metadata={"source": "webhook"},
        )

        assert trace.agent_name == "orchestrator"
        assert trace.lead_id == "hs-123"
        assert trace.metadata["source"] == "webhook"

    def test_trace_counter_increments(self, telemetry: AgentTelemetry) -> None:
        """Test trace IDs are unique."""
        trace1 = telemetry.start_trace("orchestrator")
        trace2 = telemetry.start_trace("orchestrator")

        assert trace1.trace_id != trace2.trace_id

    def test_max_traces_enforced(self) -> None:
        """Test that max traces limit is enforced (FIFO)."""
        telemetry = AgentTelemetry(max_traces=5)

        for i in range(10):
            telemetry.start_trace("orchestrator", lead_id=f"lead-{i}")

        # Only last 5 should remain
        traces = telemetry.get_recent_traces(limit=100)
        assert len(traces) == 5
        assert traces[0]["lead_id"] == "lead-5"

    def test_record_phase_completion(self, telemetry: AgentTelemetry) -> None:
        """Test recording phase completion metrics."""
        telemetry.record_phase_completion(
            agent_name="orchestrator",
            phase_name="research",
            duration_ms=150.5,
            success=True,
        )
        telemetry.record_phase_completion(
            agent_name="orchestrator",
            phase_name="research",
            duration_ms=200.0,
            success=True,
        )

        metrics = telemetry.get_metrics()
        stats = metrics["phase_stats"]["orchestrator:research"]

        assert stats["count"] == 2
        assert stats["avg_duration_ms"] == 175.25
        assert stats["min_duration_ms"] == 150.5
        assert stats["max_duration_ms"] == 200.0
        assert stats["errors"] == 0

    def test_record_phase_errors(self, telemetry: AgentTelemetry) -> None:
        """Test recording phase errors."""
        telemetry.record_phase_completion(
            agent_name="orchestrator",
            phase_name="research",
            duration_ms=100,
            success=True,
        )
        telemetry.record_phase_completion(
            agent_name="orchestrator",
            phase_name="research",
            duration_ms=50,
            success=False,
        )

        metrics = telemetry.get_metrics()
        stats = metrics["phase_stats"]["orchestrator:research"]

        assert stats["errors"] == 1
        assert stats["error_rate"] == 0.5

    def test_record_api_calls(self, telemetry: AgentTelemetry) -> None:
        """Test recording API calls."""
        telemetry.record_api_call("apollo", 5)
        telemetry.record_api_call("openai", 3)
        telemetry.record_api_call("apollo", 2)

        metrics = telemetry.get_metrics()
        assert metrics["api_calls"]["apollo"] == 7
        assert metrics["api_calls"]["openai"] == 3

    def test_get_metrics(self, telemetry: AgentTelemetry) -> None:
        """Test getting aggregated metrics."""
        telemetry.start_trace("orchestrator")
        telemetry.start_trace("research_agent")
        telemetry.record_api_call("apollo", 3)

        metrics = telemetry.get_metrics()

        assert metrics["agent_executions"]["orchestrator"] == 1
        assert metrics["agent_executions"]["research_agent"] == 1
        assert metrics["api_calls"]["apollo"] == 3
        assert metrics["total_traces"] == 2

    def test_get_recent_traces(self, telemetry: AgentTelemetry) -> None:
        """Test getting recent traces."""
        telemetry.start_trace("orchestrator", lead_id="lead-1")
        telemetry.start_trace("research_agent", lead_id="lead-2")
        telemetry.start_trace("orchestrator", lead_id="lead-3")

        # Get all traces
        all_traces = telemetry.get_recent_traces(limit=10)
        assert len(all_traces) == 3

        # Filter by agent
        orchestrator_traces = telemetry.get_recent_traces(agent_name="orchestrator")
        assert len(orchestrator_traces) == 2

    def test_get_error_summary(self, telemetry: AgentTelemetry) -> None:
        """Test getting error summary."""
        # Record some successes and failures
        for _ in range(8):
            telemetry.record_phase_completion("orchestrator", "research", 100, success=True)
        for _ in range(2):
            telemetry.record_phase_completion("orchestrator", "research", 100, success=False)

        errors = telemetry.get_error_summary()

        assert "orchestrator:research" in errors
        assert errors["orchestrator:research"]["error_count"] == 2
        assert errors["orchestrator:research"]["total_executions"] == 10
        assert errors["orchestrator:research"]["error_rate"] == 0.2

    def test_reset(self, telemetry: AgentTelemetry) -> None:
        """Test resetting telemetry."""
        telemetry.start_trace("orchestrator")
        telemetry.record_api_call("apollo", 5)
        telemetry.record_phase_completion("orchestrator", "research", 100, success=True)

        telemetry.reset()

        metrics = telemetry.get_metrics()
        assert metrics["agent_executions"] == {}
        assert metrics["api_calls"] == {}
        assert metrics["phase_stats"] == {}
        assert metrics["total_traces"] == 0


class TestGlobalTelemetry:
    """Tests for global telemetry instance."""

    def test_global_instance_exists(self) -> None:
        """Test global telemetry instance is available."""
        assert agent_telemetry is not None
        assert isinstance(agent_telemetry, AgentTelemetry)

    def test_global_instance_can_record(self) -> None:
        """Test global instance can record metrics."""
        initial_metrics = agent_telemetry.get_metrics()
        initial_traces = initial_metrics["total_traces"]

        trace = agent_telemetry.start_trace("test_agent")
        phase = trace.add_phase("test_phase")
        phase.start()
        phase.complete()
        trace.complete()

        metrics = agent_telemetry.get_metrics()
        # Should have at least one more trace than before
        assert metrics["total_traces"] >= initial_traces + 1
