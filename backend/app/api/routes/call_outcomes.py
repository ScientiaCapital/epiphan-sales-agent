"""API routes for call outcome tracking.

POST /api/call-outcomes         — Log a call outcome
POST /api/call-outcomes/batch   — Batch log (end-of-day catch-up)
GET  /api/call-outcomes/stats   — Daily stats dashboard
GET  /api/call-outcomes/stats/range — Stats over a date range
GET  /api/call-outcomes/follow-ups  — Pending follow-ups
GET  /api/call-outcomes/lead/{lead_id} — Full call history for a lead
POST /api/call-outcomes/{outcome_id}/hubspot-sync — Manual HubSpot sync
"""

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.data.call_outcome_schemas import (
    CallOutcomeBatchCreate,
    CallOutcomeCreate,
    CallOutcomeLogResult,
    DailyCallStats,
    LeadCallHistory,
    PendingFollowUpsResponse,
)
from app.middleware.auth import require_auth
from app.services.call_outcomes.service import call_outcome_service
from app.services.database.supabase_client import supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/call-outcomes", tags=["call-outcomes"], dependencies=[Depends(require_auth)])


@router.post("", response_model=CallOutcomeLogResult)
async def log_call_outcome(outcome: CallOutcomeCreate) -> CallOutcomeLogResult:
    """Log a single call outcome.

    After Tim finishes a call, this endpoint:
    1. Records the call outcome
    2. Updates the lead (last_contacted, contact_count, status)
    3. Schedules a default follow-up if Tim didn't specify one
    """
    # Verify lead exists
    lead = supabase_client.get_lead_by_id(outcome.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {outcome.lead_id} not found")

    result = call_outcome_service.log_outcome(outcome)

    logger.info(
        "Call outcome logged",
        extra={
            "lead_id": outcome.lead_id,
            "disposition": outcome.disposition.value,
            "result": outcome.result.value,
            "follow_up_scheduled": result.follow_up_scheduled,
        },
    )

    return result


@router.post("/batch")
async def log_batch_outcomes(
    batch: CallOutcomeBatchCreate,
) -> dict[str, Any]:
    """Log multiple call outcomes at once (end-of-day catch-up).

    Returns individual results for each outcome. Partial failures
    are reported per-outcome without rolling back successful inserts.
    """
    results: list[dict[str, Any]] = []
    success_count = 0
    failure_count = 0

    for outcome in batch.outcomes:
        try:
            lead = supabase_client.get_lead_by_id(outcome.lead_id)
            if not lead:
                results.append({
                    "lead_id": outcome.lead_id,
                    "success": False,
                    "error": f"Lead {outcome.lead_id} not found",
                })
                failure_count += 1
                continue

            result = call_outcome_service.log_outcome(outcome)
            results.append({
                "lead_id": outcome.lead_id,
                "success": True,
                "outcome_id": result.outcome.id,
            })
            success_count += 1
        except Exception as e:
            logger.exception(
                "Failed to log outcome for lead %s", outcome.lead_id
            )
            results.append({
                "lead_id": outcome.lead_id,
                "success": False,
                "error": str(e),
            })
            failure_count += 1

    return {
        "total": len(batch.outcomes),
        "success_count": success_count,
        "failure_count": failure_count,
        "results": results,
    }


@router.get("/stats", response_model=DailyCallStats)
async def get_daily_stats(
    stats_date: str = Query(
        default=None,
        alias="date",
        description="Date in YYYY-MM-DD format (default: today)",
    ),
) -> DailyCallStats:
    """Get Tim's daily call performance stats.

    Returns connection rates, meeting rates, phone type breakdown,
    and average call duration for the specified date.
    """
    target_date = stats_date or date.today().isoformat()
    return call_outcome_service.get_daily_stats(target_date)


@router.get("/stats/range")
async def get_stats_range(
    start: str = Query(description="Start date YYYY-MM-DD"),
    end: str = Query(description="End date YYYY-MM-DD"),
) -> list[DailyCallStats]:
    """Get daily call stats for a date range."""
    return call_outcome_service.get_stats_for_range(start, end)


@router.get("/follow-ups", response_model=PendingFollowUpsResponse)
async def get_pending_follow_ups(
    follow_up_date: str = Query(
        default=None,
        alias="date",
        description="Check follow-ups up to this date (default: today)",
    ),
    include_overdue: bool = Query(
        default=True,
        description="Include past-due follow-ups",
    ),
) -> PendingFollowUpsResponse:
    """Get pending follow-ups — what needs doing today.

    Returns follow-ups sorted with overdue items first.
    """
    target = date.fromisoformat(follow_up_date) if follow_up_date else None
    return call_outcome_service.get_pending_follow_ups(
        target_date=target,
        include_overdue=include_overdue,
    )


@router.get("/lead/{lead_id}", response_model=LeadCallHistory)
async def get_lead_call_history(lead_id: str) -> LeadCallHistory:
    """Get full call history for a specific lead."""
    lead = supabase_client.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    return call_outcome_service.get_lead_history(lead_id)


@router.post("/{outcome_id}/hubspot-sync")
async def sync_outcome_to_hubspot(outcome_id: str) -> dict[str, Any]:
    """Manually sync a call outcome to HubSpot as a CALL engagement."""
    try:
        result = await call_outcome_service.sync_to_hubspot(outcome_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("HubSpot sync failed for outcome %s", outcome_id)
        raise HTTPException(
            status_code=502,
            detail=f"HubSpot sync failed: {e}",
        ) from e
