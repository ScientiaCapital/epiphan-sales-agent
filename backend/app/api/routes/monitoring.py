"""Observability endpoints for Apollo credit usage, rate limits, and batch status.

Provides visibility into:
- Credit usage and savings from tiered enrichment
- Rate limit health and backoff status
- In-progress batch tracking

PHONES ARE GOLD - but we need to track how much gold we're spending!
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.enrichment.audit import BatchAuditSummary, RateLimitStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


# =============================================================================
# In-memory batch tracking (for MVP; Supabase persistence in future)
# =============================================================================

# Thread-safe batch storage (batch_id -> BatchAuditSummary)
_active_batches: dict[str, BatchAuditSummary] = {}
_completed_batches: dict[str, BatchAuditSummary] = {}

# Global rate limit tracker (singleton per process)
_rate_limit_status = RateLimitStatus()


def register_batch(batch_id: str, total_leads: int) -> BatchAuditSummary:
    """Register a new batch for tracking."""
    summary = BatchAuditSummary(
        batch_id=batch_id,
        started_at=datetime.now(timezone.utc),
        total_leads=total_leads,
    )
    _active_batches[batch_id] = summary
    logger.info(f"Registered batch {batch_id} with {total_leads} leads")
    return summary


def get_batch(batch_id: str) -> BatchAuditSummary | None:
    """Get batch by ID from active or completed batches."""
    return _active_batches.get(batch_id) or _completed_batches.get(batch_id)


def complete_batch(batch_id: str) -> None:
    """Move batch from active to completed."""
    if batch_id in _active_batches:
        summary = _active_batches.pop(batch_id)
        summary.finalize()
        _completed_batches[batch_id] = summary
        # Keep only last 100 completed batches
        if len(_completed_batches) > 100:
            oldest = min(_completed_batches.keys())
            del _completed_batches[oldest]
        logger.info(f"Completed batch {batch_id}")


def get_rate_limit_tracker() -> RateLimitStatus:
    """Get the global rate limit tracker."""
    return _rate_limit_status


# =============================================================================
# Response Models
# =============================================================================


class CreditUsageResponse(BaseModel):
    """Credit usage statistics for monitoring Apollo spend."""

    total_credits_used: int = Field(description="Total Apollo credits consumed")
    phase1_credits: int = Field(description="1-credit basic enrichments")
    phase2_credits: int = Field(description="8-credit phone reveals (ATL only)")
    atl_leads: int = Field(description="Leads that qualified for phone reveal")
    non_atl_leads: int = Field(description="Leads skipped (credits saved)")
    credits_saved: int = Field(description="Estimated credits saved vs legacy approach")
    savings_percent: float = Field(description="Percentage saved (0.0-1.0)")
    period: str = Field(description="Time period: today | this_week | all_time")

    # Phone metrics (PHONES ARE GOLD!)
    phones_revealed: int = Field(default=0, description="Phone reveal attempts")
    direct_phones_found: int = Field(default=0, description="Direct dials discovered")
    mobile_phones_found: int = Field(default=0, description="Mobile phones discovered")
    phone_discovery_rate: float = Field(default=0.0, description="Success rate (0.0-1.0)")


class RateLimitStatusResponse(BaseModel):
    """Rate limit status for monitoring Apollo API health."""

    requests_this_minute: int = Field(description="Requests in current minute window")
    limit_per_minute: int = Field(default=50, description="Apollo rate limit")
    consecutive_rate_limits: int = Field(description="Consecutive 429 responses")
    total_rate_limits_today: int = Field(description="Total 429s today")
    current_backoff_seconds: float = Field(description="Current backoff delay")
    approaching_limit: bool = Field(description="True if > 80% of limit used")
    health: str = Field(description="healthy | warning | critical")


class BatchStatusResponse(BaseModel):
    """Batch processing status for tracking long-running jobs."""

    batch_id: str = Field(description="Unique batch identifier")
    status: str = Field(description="processing | completed | failed")
    total_leads: int = Field(description="Total leads in batch")
    processed: int = Field(description="Leads processed so far")
    succeeded: int = Field(description="Successfully processed")
    failed: int = Field(description="Processing failures")
    progress_percent: float = Field(description="Completion percentage (0-100)")
    started_at: str = Field(description="ISO timestamp when batch started")
    completed_at: str | None = Field(default=None, description="ISO timestamp when completed")
    credits_used: int = Field(description="Apollo credits consumed so far")

    # ATL metrics
    atl_leads: int = Field(default=0, description="ATL decision-makers found")
    non_atl_leads: int = Field(default=0, description="Non-ATL contacts")

    # Phone metrics (PHONES ARE GOLD!)
    phones_revealed: int = Field(default=0, description="Phone reveal attempts")
    direct_phones_found: int = Field(default=0, description="Direct dials discovered")
    any_phones_found: int = Field(default=0, description="Leads with any phone")


class AllBatchesResponse(BaseModel):
    """Summary of all tracked batches."""

    active_count: int = Field(description="Currently processing batches")
    completed_count: int = Field(description="Recently completed batches")
    active_batches: list[dict[str, Any]] = Field(description="Active batch summaries")
    recent_completed: list[dict[str, Any]] = Field(description="Last 10 completed batches")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/credits", response_model=CreditUsageResponse)
async def get_credit_usage(period: str = "all_time") -> CreditUsageResponse:
    """
    Get Apollo credit usage statistics.

    Tracks credits spent on tiered enrichment and calculates savings vs legacy approach.
    PHONES ARE GOLD - but we need to track how much gold we're spending!

    Args:
        period: Time period - "today", "this_week", or "all_time"

    Returns:
        Credit usage breakdown with savings analysis
    """
    # Aggregate from all completed batches (and active)
    all_batches = list(_completed_batches.values()) + list(_active_batches.values())

    total_credits = sum(b.total_credits_used for b in all_batches)
    phase1 = sum(b.phase1_credits for b in all_batches)
    phase2 = sum(b.phase2_credits for b in all_batches)
    atl = sum(b.atl_leads for b in all_batches)
    non_atl = sum(b.non_atl_leads for b in all_batches)
    phones_revealed = sum(b.phones_revealed for b in all_batches)
    direct_found = sum(b.direct_phones_found for b in all_batches)
    mobile_found = sum(b.mobile_phones_found for b in all_batches)
    any_phones = sum(b.any_phones_found for b in all_batches)

    # Calculate savings
    total_leads = atl + non_atl
    legacy_cost = total_leads * 8  # Legacy: 8 credits per lead
    credits_saved = legacy_cost - total_credits
    savings_percent = credits_saved / legacy_cost if legacy_cost > 0 else 0.0

    # Phone discovery rate
    phone_rate = any_phones / phones_revealed if phones_revealed > 0 else 0.0

    return CreditUsageResponse(
        total_credits_used=total_credits,
        phase1_credits=phase1,
        phase2_credits=phase2,
        atl_leads=atl,
        non_atl_leads=non_atl,
        credits_saved=max(0, credits_saved),
        savings_percent=max(0.0, savings_percent),
        period=period,
        phones_revealed=phones_revealed,
        direct_phones_found=direct_found,
        mobile_phones_found=mobile_found,
        phone_discovery_rate=phone_rate,
    )


@router.get("/rate-limits", response_model=RateLimitStatusResponse)
async def get_rate_limit_status() -> RateLimitStatusResponse:
    """
    Get Apollo API rate limit status.

    Monitors request volume and backoff state to prevent throttling.
    Apollo limits: 50 requests/minute for basic plans.

    Returns:
        Rate limit health status with backoff recommendations
    """
    status = get_rate_limit_tracker()

    # Determine health status
    usage_percent = status.requests_this_minute / 50
    if status.consecutive_rate_limits > 0:
        health = "critical"
    elif usage_percent > 0.8:
        health = "warning"
    else:
        health = "healthy"

    return RateLimitStatusResponse(
        requests_this_minute=status.requests_this_minute,
        limit_per_minute=50,
        consecutive_rate_limits=status.consecutive_rate_limits,
        total_rate_limits_today=status.rate_limit_hits_today,
        current_backoff_seconds=status.get_backoff_seconds(),
        approaching_limit=usage_percent > 0.8,
        health=health,
    )


@router.get("/batches", response_model=AllBatchesResponse)
async def list_batches() -> AllBatchesResponse:
    """
    List all tracked batches (active and recent completed).

    Use this to get an overview of processing activity.

    Returns:
        Summary of active and completed batches
    """
    active = [
        {
            "batch_id": b.batch_id,
            "status": "processing",
            "total_leads": b.total_leads,
            "processed": b.processed,
            "progress_percent": round(b.processed / b.total_leads * 100, 1) if b.total_leads > 0 else 0,
            "started_at": b.started_at.isoformat(),
        }
        for b in _active_batches.values()
    ]

    # Sort completed by started_at descending, take last 10
    completed = sorted(
        _completed_batches.values(),
        key=lambda b: b.started_at,
        reverse=True,
    )[:10]
    recent = [
        {
            "batch_id": b.batch_id,
            "status": "completed",
            "total_leads": b.total_leads,
            "processed": b.processed,
            "credits_used": b.total_credits_used,
            "started_at": b.started_at.isoformat(),
            "completed_at": b.completed_at.isoformat() if b.completed_at else None,
        }
        for b in completed
    ]

    return AllBatchesResponse(
        active_count=len(_active_batches),
        completed_count=len(_completed_batches),
        active_batches=active,
        recent_completed=recent,
    )


@router.get("/batches/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str) -> BatchStatusResponse:
    """
    Get detailed status for a specific batch.

    Track progress of long-running lead processing jobs.

    Args:
        batch_id: Unique batch identifier (from ingest response)

    Returns:
        Detailed batch status with credit and phone metrics
    """
    batch = get_batch(batch_id)

    if not batch:
        raise HTTPException(
            status_code=404,
            detail=f"Batch {batch_id} not found. It may have expired or never existed.",
        )

    # Determine status
    if batch_id in _active_batches:
        status = "processing"
    elif batch.failed > 0 and batch.failed == batch.total_leads:
        status = "failed"
    else:
        status = "completed"

    progress = (batch.processed / batch.total_leads * 100) if batch.total_leads > 0 else 0

    return BatchStatusResponse(
        batch_id=batch.batch_id,
        status=status,
        total_leads=batch.total_leads,
        processed=batch.processed,
        succeeded=batch.processed - batch.failed,
        failed=batch.failed,
        progress_percent=round(progress, 1),
        started_at=batch.started_at.isoformat(),
        completed_at=batch.completed_at.isoformat() if batch.completed_at else None,
        credits_used=batch.total_credits_used,
        atl_leads=batch.atl_leads,
        non_atl_leads=batch.non_atl_leads,
        phones_revealed=batch.phones_revealed,
        direct_phones_found=batch.direct_phones_found,
        any_phones_found=batch.any_phones_found,
    )


# =============================================================================
# Agent Telemetry Endpoints
# =============================================================================


class TelemetryMetricsResponse(BaseModel):
    """Response for agent telemetry metrics."""

    agent_executions: dict[str, int] = Field(
        description="Execution counts by agent"
    )
    api_calls: dict[str, int] = Field(
        description="API call counts by provider"
    )
    phase_stats: dict[str, dict[str, Any]] = Field(
        description="Phase-level statistics"
    )
    total_traces: int = Field(description="Total traces in memory")


class ExecutionTraceResponse(BaseModel):
    """Response for execution trace."""

    trace_id: str
    agent_name: str
    lead_id: str | None
    start_time: str
    end_time: str | None
    total_duration_ms: float
    status: str
    phases: list[dict[str, Any]]
    metadata: dict[str, Any]


class TracesListResponse(BaseModel):
    """Response for list of traces."""

    traces: list[ExecutionTraceResponse]
    total: int


@router.get("/telemetry", response_model=TelemetryMetricsResponse)
async def get_telemetry_metrics() -> TelemetryMetricsResponse:
    """
    Get aggregated agent telemetry metrics.

    Provides visibility into:
    - Agent execution counts
    - API call volumes by provider
    - Phase-level timing statistics and error rates

    Returns:
        Aggregated metrics across all agent executions
    """
    from app.services.langgraph.telemetry import agent_telemetry

    metrics = agent_telemetry.get_metrics()

    return TelemetryMetricsResponse(
        agent_executions=metrics["agent_executions"],
        api_calls=metrics["api_calls"],
        phase_stats=metrics["phase_stats"],
        total_traces=metrics["total_traces"],
    )


@router.get("/telemetry/traces", response_model=TracesListResponse)
async def get_telemetry_traces(
    agent_name: str | None = None,
    limit: int = 10,
) -> TracesListResponse:
    """
    Get recent execution traces.

    Traces provide detailed phase-by-phase breakdown of agent executions.

    Args:
        agent_name: Optional filter by agent name
        limit: Maximum traces to return (default 10, max 100)

    Returns:
        List of recent traces with phase details
    """
    from app.services.langgraph.telemetry import agent_telemetry

    limit = min(limit, 100)
    traces = agent_telemetry.get_recent_traces(agent_name=agent_name, limit=limit)

    return TracesListResponse(
        traces=[ExecutionTraceResponse(**t) for t in traces],
        total=len(traces),
    )


@router.get("/telemetry/errors")
async def get_telemetry_errors() -> dict[str, Any]:
    """
    Get summary of errors across all agent phases.

    Use this to identify problematic phases and error patterns.

    Returns:
        Error counts and rates by agent:phase
    """
    from app.services.langgraph.telemetry import agent_telemetry

    return agent_telemetry.get_error_summary()
