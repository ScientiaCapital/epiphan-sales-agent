"""LangSmith tracing utilities for LangGraph agents.

Provides decorators and utilities for tracing agent execution,
capturing metrics, and debugging agent behavior.

Features:
- @trace_agent decorator for automatic tracing
- Custom metadata attachment (lead IDs, tiers, etc.)
- Error capture and reporting
- Performance metrics (duration, token counts)

Usage:
    from app.services.langgraph.tracing import trace_agent, with_tracing_context

    @trace_agent("orchestrator")
    async def run(self, lead: Lead) -> dict:
        ...

    # Or add context to existing runs
    async with with_tracing_context(lead_id="123"):
        result = await agent.run(lead)

Environment Variables:
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=lsv2_...
    LANGSMITH_PROJECT=epiphan-sales-agent
"""

import functools
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is enabled."""
    # Check both settings and environment variable
    return (
        settings.langchain_tracing_v2
        or os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
    ) and bool(settings.langchain_api_key or os.getenv("LANGCHAIN_API_KEY"))


def trace_agent(
    name: str,
    metadata: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to trace agent execution in LangSmith.

    Automatically captures:
    - Execution time
    - Input/output data
    - Errors and exceptions
    - Custom metadata

    Args:
        name: Name of the agent (appears in LangSmith dashboard)
        metadata: Optional static metadata to attach to all traces

    Example:
        @trace_agent("qualification_agent", metadata={"version": "1.0"})
        async def run(self, lead: Lead) -> dict:
            ...
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not is_tracing_enabled():
                return await func(*args, **kwargs)

            try:
                from langsmith import traceable

                # Build metadata
                trace_metadata = {
                    "agent": name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "project": settings.langsmith_project,
                    **(metadata or {}),
                }

                # Extract lead info if available
                lead = kwargs.get("lead") or (args[1] if len(args) > 1 else None)
                if lead and hasattr(lead, "hubspot_id"):
                    trace_metadata["lead_id"] = lead.hubspot_id
                if lead and hasattr(lead, "email"):
                    trace_metadata["lead_email"] = lead.email
                if lead and hasattr(lead, "company"):
                    trace_metadata["lead_company"] = lead.company

                # Create traced version
                traced_func = traceable(
                    name=name,
                    project_name=settings.langsmith_project,
                    metadata=trace_metadata,
                )(func)

                return await traced_func(*args, **kwargs)

            except ImportError:
                # langsmith not installed
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not is_tracing_enabled():
                return func(*args, **kwargs)

            try:
                from langsmith import traceable

                trace_metadata = {
                    "agent": name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "project": settings.langsmith_project,
                    **(metadata or {}),
                }

                traced_func = traceable(
                    name=name,
                    project_name=settings.langsmith_project,
                    metadata=trace_metadata,
                )(func)

                return traced_func(*args, **kwargs)

            except ImportError:
                return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def asyncio_iscoroutinefunction(func: Any) -> bool:
    """Check if function is async."""
    import asyncio
    import inspect

    return asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func)


@asynccontextmanager
async def with_tracing_context(
    lead_id: str | None = None,
    lead_email: str | None = None,
    tier: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> AsyncIterator[None]:
    """
    Context manager to add tracing metadata to enclosed operations.

    Useful for adding context to operations that aren't directly decorated.

    Args:
        lead_id: Lead's HubSpot ID
        lead_email: Lead's email address
        tier: Qualification tier
        extra_metadata: Additional metadata to attach

    Example:
        async with with_tracing_context(lead_id="123", tier="TIER_1"):
            result = await agent.run(lead)
    """
    if not is_tracing_enabled():
        yield
        return

    try:
        from langsmith import trace

        metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(extra_metadata or {}),
        }
        if lead_id:
            metadata["lead_id"] = lead_id
        if lead_email:
            metadata["lead_email"] = lead_email
        if tier:
            metadata["tier"] = tier

        with trace(
            name="orchestration_context",
            project_name=settings.langsmith_project,
            metadata=metadata,
        ):
            yield

    except ImportError:
        yield


def log_agent_result(
    agent_name: str,
    lead_id: str,
    tier: str | None = None,
    duration_ms: float | None = None,
    success: bool = True,
    error: str | None = None,
) -> None:
    """
    Log an agent result to LangSmith as a custom run.

    Useful for tracking aggregate metrics and debugging.

    Args:
        agent_name: Name of the agent
        lead_id: Lead's HubSpot ID
        tier: Qualification tier result
        duration_ms: Execution duration in milliseconds
        success: Whether execution succeeded
        error: Error message if failed
    """
    if not is_tracing_enabled():
        return

    try:
        from langsmith import Client

        client = Client()
        client.create_run(
            name=f"{agent_name}_result",
            run_type="chain",
            inputs={"lead_id": lead_id},
            outputs={
                "tier": tier,
                "duration_ms": duration_ms,
                "success": success,
                "error": error,
            },
            project_name=settings.langsmith_project,
        )
    except (ImportError, Exception):
        # Silently fail if logging fails
        pass


def get_tracing_config() -> dict[str, Any]:
    """
    Get tracing configuration for LangGraph graphs.

    Returns configuration dict that can be passed to graph.invoke()
    or graph.astream() for automatic tracing.

    Example:
        config = get_tracing_config()
        result = await graph.ainvoke(state, config=config)
    """
    if not is_tracing_enabled():
        return {}

    return {
        "callbacks": [],  # LangSmith auto-detects from environment
        "metadata": {
            "project": settings.langsmith_project,
        },
        "tags": ["epiphan-sales-agent"],
    }


class TracingMetrics:
    """
    Utility class for collecting and reporting tracing metrics.

    Provides methods for tracking:
    - Agent execution counts
    - Success/failure rates
    - Average duration
    - Tier distribution
    """

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._executions: list[dict[str, Any]] = []

    def record(
        self,
        agent_name: str,
        duration_ms: float,
        success: bool,
        tier: str | None = None,
    ) -> None:
        """Record an execution."""
        self._executions.append({
            "agent": agent_name,
            "duration_ms": duration_ms,
            "success": success,
            "tier": tier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_summary(self) -> dict[str, Any]:
        """Get summary of recorded metrics."""
        if not self._executions:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "tier_distribution": {},
            }

        total = len(self._executions)
        successes = sum(1 for e in self._executions if e["success"])
        total_duration = sum(e["duration_ms"] for e in self._executions)

        tier_counts: dict[str, int] = {}
        for e in self._executions:
            if e["tier"]:
                tier_counts[e["tier"]] = tier_counts.get(e["tier"], 0) + 1

        return {
            "total_executions": total,
            "success_rate": successes / total if total > 0 else 0.0,
            "avg_duration_ms": total_duration / total if total > 0 else 0.0,
            "tier_distribution": tier_counts,
        }

    def clear(self) -> None:
        """Clear recorded metrics."""
        self._executions.clear()


# Singleton metrics instance
tracing_metrics = TracingMetrics()
