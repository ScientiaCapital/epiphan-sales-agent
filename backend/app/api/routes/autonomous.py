"""API routes for the autonomous BDR pipeline.

Endpoints for triggering pipeline runs, reviewing the outreach queue,
approving/rejecting items, and viewing learned approval patterns.

Rate limited: AGENT for run trigger (LLM), WRITE for approvals, READ for queries.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from postgrest.types import CountMethod
from pydantic import BaseModel

from app.core.rate_limit import AGENT_RATE_LIMIT, READ_RATE_LIMIT, WRITE_RATE_LIMIT, limiter
from app.middleware.auth import require_auth
from app.services.autonomous.schemas import (
    ApproveRequest,
    BulkActionRequest,
    EditDraftRequest,
    RejectRequest,
    RunConfig,
)

router = APIRouter(
    prefix="/api/autonomous",
    tags=["autonomous"],
    dependencies=[Depends(require_auth)],
)


# =============================================================================
# Pipeline Run Endpoints
# =============================================================================


class TriggerRunResponse(BaseModel):
    """Response when triggering a pipeline run."""

    run_id: str
    status: str = "started"
    message: str = "Pipeline run started in background"


@router.post("/run", response_model=TriggerRunResponse)
@limiter.limit(AGENT_RATE_LIMIT)
async def trigger_run(
    request: Request,
    body: RunConfig | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> TriggerRunResponse:
    """Trigger an autonomous pipeline run.

    Starts the pipeline in the background. Track progress via
    GET /api/autonomous/runs/{run_id}.
    """
    from app.services.autonomous.runner import autonomous_runner

    config = body or RunConfig()

    # Run in background so the API responds immediately
    import uuid
    run_id = str(uuid.uuid4())

    async def _run_pipeline() -> None:
        await autonomous_runner.run(config)

    background_tasks.add_task(asyncio.ensure_future, _run_pipeline())

    return TriggerRunResponse(
        run_id=run_id,
        status="started",
        message=f"Pipeline run started: {config.prospect_limit} prospects from {[s.value for s in config.sources]}",
    )


@router.get("/runs")
@limiter.limit(READ_RATE_LIMIT)
async def list_runs(
    request: Request,
    limit: int = 20,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """List past pipeline runs with summaries."""
    from app.services.database.supabase_client import supabase_client

    query = (
        supabase_client.client.table("autonomous_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    return cast(list[dict[str, Any]], result.data) if result.data else []


@router.get("/runs/{run_id}")
@limiter.limit(READ_RATE_LIMIT)
async def get_run(request: Request, run_id: str) -> dict[str, Any]:
    """Get details for a specific pipeline run."""
    from app.services.database.supabase_client import supabase_client

    result = (
        supabase_client.client.table("autonomous_runs")
        .select("*")
        .eq("id", run_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Run not found")

    return cast(dict[str, Any], result.data[0])


# =============================================================================
# Queue Review Endpoints
# =============================================================================


@router.get("/queue")
@limiter.limit(READ_RATE_LIMIT)
async def get_queue(
    request: Request,
    status: str | None = "pending",
    tier: str | None = None,
    source: str | None = None,
    run_id: str | None = None,
    is_atl: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Get outreach queue items with optional filtering.

    Default: show pending items for morning review.
    """
    from app.services.database.supabase_client import supabase_client

    query = (
        supabase_client.client.table("outreach_queue")
        .select("*")
        .order("qualification_score", desc=True)
        .range(offset, offset + limit - 1)
    )

    if status:
        query = query.eq("status", status)
    if tier:
        query = query.eq("qualification_tier", tier)
    if source:
        query = query.eq("lead_source", source)
    if run_id:
        query = query.eq("run_id", run_id)
    if is_atl is not None:
        query = query.eq("is_atl", is_atl)

    result = query.execute()
    return cast(list[dict[str, Any]], result.data) if result.data else []


@router.post("/queue/{item_id}/approve")
@limiter.limit(WRITE_RATE_LIMIT)
async def approve_item(
    request: Request,
    item_id: str,
    body: ApproveRequest | None = None,
) -> dict[str, str]:
    """Approve an outreach item for sending."""
    from app.services.autonomous.learner import approval_learner

    await approval_learner.record_decision(
        queue_item_id=item_id,
        approved=True,
        reviewer_notes=body.reviewer_notes if body else None,
    )

    return {"status": "approved", "item_id": item_id}


@router.post("/queue/{item_id}/reject")
@limiter.limit(WRITE_RATE_LIMIT)
async def reject_item(
    request: Request,
    item_id: str,
    body: RejectRequest,
) -> dict[str, str]:
    """Reject an outreach item with reason."""
    from app.services.autonomous.learner import approval_learner

    await approval_learner.record_decision(
        queue_item_id=item_id,
        approved=False,
        rejection_reason=body.rejection_reason,
    )

    return {"status": "rejected", "item_id": item_id}


@router.put("/queue/{item_id}/edit")
@limiter.limit(WRITE_RATE_LIMIT)
async def edit_draft(
    request: Request,
    item_id: str,
    body: EditDraftRequest,
) -> dict[str, str]:
    """Edit an outreach draft before approving."""
    from app.services.database.supabase_client import supabase_client

    update_data: dict[str, Any] = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.email_subject is not None:
        update_data["email_subject"] = body.email_subject
    if body.email_body is not None:
        update_data["email_body"] = body.email_body
    if body.reviewer_notes is not None:
        update_data["reviewer_notes"] = body.reviewer_notes

    supabase_client.client.table("outreach_queue").update(
        update_data
    ).eq("id", item_id).execute()

    return {"status": "updated", "item_id": item_id}


@router.post("/queue/bulk-approve")
@limiter.limit(WRITE_RATE_LIMIT)
async def bulk_approve(
    request: Request,
    body: BulkActionRequest,
) -> dict[str, Any]:
    """Approve multiple outreach items at once."""
    from app.services.autonomous.learner import approval_learner
    from app.services.database.supabase_client import supabase_client

    item_ids = body.item_ids

    # If filter provided instead of IDs, fetch matching items
    if not item_ids and body.filter_tier:
        result = (
            supabase_client.client.table("outreach_queue")
            .select("id")
            .eq("status", "pending")
            .eq("qualification_tier", body.filter_tier)
            .execute()
        )
        rows = cast(list[dict[str, Any]], result.data) if result.data else []
        item_ids = [row["id"] for row in rows]

    approved_count = 0
    for item_id in item_ids:
        await approval_learner.record_decision(
            queue_item_id=item_id,
            approved=True,
        )
        approved_count += 1

    return {"status": "bulk_approved", "count": approved_count}


@router.post("/queue/bulk-reject")
@limiter.limit(WRITE_RATE_LIMIT)
async def bulk_reject(
    request: Request,
    body: BulkActionRequest,
) -> dict[str, Any]:
    """Reject multiple outreach items at once."""
    from app.services.autonomous.learner import approval_learner
    from app.services.database.supabase_client import supabase_client

    item_ids = body.item_ids

    if not item_ids and body.filter_tier:
        result = (
            supabase_client.client.table("outreach_queue")
            .select("id")
            .eq("status", "pending")
            .eq("qualification_tier", body.filter_tier)
            .execute()
        )
        rows = cast(list[dict[str, Any]], result.data) if result.data else []
        item_ids = [row["id"] for row in rows]

    rejected_count = 0
    for item_id in item_ids:
        await approval_learner.record_decision(
            queue_item_id=item_id,
            approved=False,
            rejection_reason=body.rejection_reason or "bulk_rejected",
        )
        rejected_count += 1

    return {"status": "bulk_rejected", "count": rejected_count}


# =============================================================================
# Learning & Stats Endpoints
# =============================================================================


@router.get("/patterns")
@limiter.limit(READ_RATE_LIMIT)
async def get_patterns(
    request: Request,
    pattern_type: str | None = None,
    min_decisions: int = 5,
) -> list[dict[str, Any]]:
    """View learned approval patterns.

    Shows what Tim tends to approve vs reject by industry, title, etc.
    """
    from app.services.autonomous.learner import approval_learner

    patterns = await approval_learner.get_patterns(
        pattern_type=pattern_type,
        min_decisions=min_decisions,
    )

    return [p.model_dump() for p in patterns]


@router.get("/stats")
@limiter.limit(READ_RATE_LIMIT)
async def get_stats(request: Request) -> dict[str, Any]:
    """Dashboard stats for the autonomous pipeline."""
    from app.services.database.supabase_client import supabase_client

    # Total runs
    runs_result = (
        supabase_client.client.table("autonomous_runs")
        .select("id", count=CountMethod.exact)
        .execute()
    )
    total_runs = runs_result.count or 0

    # Queue stats
    queue_result = (
        supabase_client.client.table("outreach_queue")
        .select("status")
        .execute()
    )
    rows = cast(list[dict[str, Any]], queue_result.data) if queue_result.data else []

    total_processed = len(rows)
    total_approved = sum(1 for r in rows if r.get("status") == "approved")
    total_rejected = sum(1 for r in rows if r.get("status") == "rejected")
    total_pending = sum(1 for r in rows if r.get("status") == "pending")

    approval_rate = (
        total_approved / (total_approved + total_rejected)
        if (total_approved + total_rejected) > 0
        else 0.0
    )

    return {
        "total_runs": total_runs,
        "total_processed": total_processed,
        "total_pending": total_pending,
        "total_approved": total_approved,
        "total_rejected": total_rejected,
        "approval_rate": round(approval_rate, 3),
    }
