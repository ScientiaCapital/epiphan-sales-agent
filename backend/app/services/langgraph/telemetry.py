"""Agent Telemetry for Observability.

Provides metrics collection and tracking for LangGraph agents.
Enables monitoring of:
- Agent execution timing
- Phase duration breakdowns
- Error rates and patterns
- Resource usage (API calls, credits)
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PhaseMetrics:
    """Metrics for a single agent phase."""

    phase_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "pending"  # "pending" | "running" | "success" | "error"
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        """Mark phase as started."""
        self.start_time = time.time()
        self.status = "running"

    def complete(self, metadata: dict[str, Any] | None = None) -> None:
        """Mark phase as completed successfully."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = "success"
        if metadata:
            self.metadata.update(metadata)

    def fail(self, error: str, metadata: dict[str, Any] | None = None) -> None:
        """Mark phase as failed."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = "error"
        self.error_message = error
        if metadata:
            self.metadata.update(metadata)


@dataclass
class ExecutionTrace:
    """Complete execution trace for an agent run."""

    trace_id: str
    agent_name: str
    lead_id: str | None = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    phases: list[PhaseMetrics] = field(default_factory=list)
    total_duration_ms: float = 0.0
    status: str = "running"
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_phase(self, phase_name: str) -> PhaseMetrics:
        """Add a new phase to the trace."""
        phase = PhaseMetrics(phase_name=phase_name)
        self.phases.append(phase)
        return phase

    def complete(self, metadata: dict[str, Any] | None = None) -> None:
        """Mark execution as complete."""
        self.end_time = datetime.now(timezone.utc)
        self.total_duration_ms = sum(p.duration_ms for p in self.phases)
        self.status = "success" if all(p.status == "success" for p in self.phases) else "partial"
        if metadata:
            self.metadata.update(metadata)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "lead_id": self.lead_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_ms": self.total_duration_ms,
            "status": self.status,
            "phases": [
                {
                    "phase_name": p.phase_name,
                    "duration_ms": p.duration_ms,
                    "status": p.status,
                    "error": p.error_message,
                    "metadata": p.metadata,
                }
                for p in self.phases
            ],
            "metadata": self.metadata,
        }


class AgentTelemetry:
    """
    Centralized telemetry collector for all LangGraph agents.

    Tracks:
    - Execution traces with phase-level timing
    - Aggregated metrics (avg duration, error rates)
    - Resource usage (API calls, credits)

    Usage:
        telemetry = AgentTelemetry()
        trace = telemetry.start_trace("orchestrator", lead_id="hs-123")
        phase = trace.add_phase("research")
        phase.start()
        # ... do work ...
        phase.complete({"api_calls": 2})
        trace.complete()
    """

    def __init__(self, max_traces: int = 1000) -> None:
        """
        Initialize telemetry collector.

        Args:
            max_traces: Maximum traces to keep in memory (FIFO)
        """
        self._traces: list[ExecutionTrace] = []
        self._max_traces = max_traces
        self._trace_counter = 0

        # Aggregated metrics
        self._phase_durations: dict[str, list[float]] = defaultdict(list)
        self._phase_errors: dict[str, int] = defaultdict(int)
        self._agent_executions: dict[str, int] = defaultdict(int)
        self._api_calls: dict[str, int] = defaultdict(int)

    def start_trace(
        self,
        agent_name: str,
        lead_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionTrace:
        """
        Start a new execution trace.

        Args:
            agent_name: Name of the agent being traced
            lead_id: Optional lead ID being processed
            metadata: Optional initial metadata

        Returns:
            ExecutionTrace for tracking phases
        """
        self._trace_counter += 1
        trace_id = f"{agent_name}-{self._trace_counter}-{int(time.time() * 1000)}"

        trace = ExecutionTrace(
            trace_id=trace_id,
            agent_name=agent_name,
            lead_id=lead_id,
            metadata=metadata or {},
        )

        self._traces.append(trace)
        self._agent_executions[agent_name] += 1

        # Enforce max traces (FIFO)
        while len(self._traces) > self._max_traces:
            self._traces.pop(0)

        return trace

    def record_phase_completion(
        self,
        agent_name: str,
        phase_name: str,
        duration_ms: float,
        success: bool = True,
    ) -> None:
        """
        Record a phase completion for aggregated metrics.

        Args:
            agent_name: Agent that completed the phase
            phase_name: Name of the completed phase
            duration_ms: Duration in milliseconds
            success: Whether the phase succeeded
        """
        key = f"{agent_name}:{phase_name}"
        self._phase_durations[key].append(duration_ms)

        if not success:
            self._phase_errors[key] += 1

        # Keep only last 100 durations per phase
        if len(self._phase_durations[key]) > 100:
            self._phase_durations[key] = self._phase_durations[key][-100:]

    def record_api_call(self, provider: str, count: int = 1) -> None:
        """
        Record API calls for resource tracking.

        Args:
            provider: API provider (e.g., "apollo", "openai")
            count: Number of calls
        """
        self._api_calls[provider] += count

    def get_metrics(self) -> dict[str, Any]:
        """
        Get aggregated metrics.

        Returns:
            Dict with execution counts, durations, error rates
        """
        phase_stats = {}
        for key, durations in self._phase_durations.items():
            if durations:
                phase_stats[key] = {
                    "avg_duration_ms": sum(durations) / len(durations),
                    "min_duration_ms": min(durations),
                    "max_duration_ms": max(durations),
                    "count": len(durations),
                    "errors": self._phase_errors.get(key, 0),
                    "error_rate": self._phase_errors.get(key, 0) / len(durations) if durations else 0,
                }

        return {
            "agent_executions": dict(self._agent_executions),
            "api_calls": dict(self._api_calls),
            "phase_stats": phase_stats,
            "total_traces": len(self._traces),
        }

    def get_recent_traces(
        self,
        agent_name: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get recent execution traces.

        Args:
            agent_name: Optional filter by agent name
            limit: Maximum traces to return

        Returns:
            List of trace dictionaries
        """
        traces = self._traces
        if agent_name:
            traces = [t for t in traces if t.agent_name == agent_name]

        return [t.to_dict() for t in traces[-limit:]]

    def get_error_summary(self) -> dict[str, Any]:
        """
        Get summary of errors across all phases.

        Returns:
            Dict with error counts and rates by phase
        """
        errors = {}
        for key, count in self._phase_errors.items():
            total = len(self._phase_durations.get(key, []))
            if count > 0:
                errors[key] = {
                    "error_count": count,
                    "total_executions": total,
                    "error_rate": count / total if total > 0 else 0,
                }
        return errors

    def reset(self) -> None:
        """Reset all metrics and traces."""
        self._traces.clear()
        self._phase_durations.clear()
        self._phase_errors.clear()
        self._agent_executions.clear()
        self._api_calls.clear()
        self._trace_counter = 0


# Global telemetry instance
agent_telemetry = AgentTelemetry()
