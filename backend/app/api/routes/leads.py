"""Leads API routes for lead management and scoring.

Endpoints:
- POST /api/leads/sync - Trigger HubSpot sync
- POST /api/leads/score - Score unscored leads
- GET /api/leads/prioritized - Get leads by tier/persona
- GET /api/leads/{id} - Get single lead
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.data.lead_schemas import (
    Lead,
)
from app.services.database.supabase_client import supabase_client
from app.services.hubspot.sync import hubspot_sync_service
from app.services.scoring.lead_scorer import lead_scorer

router = APIRouter(prefix="/leads", tags=["leads"])


# =============================================================================
# Request/Response Models
# =============================================================================


class SyncRequest(BaseModel):
    """Request body for sync endpoint."""

    since: datetime | None = Field(
        default=None,
        description="If provided, only sync contacts modified after this time (incremental sync)",
    )


class ScoreRequest(BaseModel):
    """Request body for score endpoint."""

    limit: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum number of leads to score",
    )


class LeadPrioritizedResponse(BaseModel):
    """Response for prioritized leads query."""

    leads: list[dict]
    total_count: int
    tier_counts: dict[str, int]
    query: dict


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/sync", response_model=dict)
async def sync_leads(request: SyncRequest | None = None) -> dict:
    """
    Trigger HubSpot to Supabase sync.

    - Without `since`: Full sync of all contacts
    - With `since`: Incremental sync of recently modified contacts

    Returns sync statistics including contacts fetched, synced, and any errors.
    """
    if request and request.since:
        # Incremental sync
        result = await hubspot_sync_service.incremental_sync(since=request.since)
    else:
        # Full sync
        result = await hubspot_sync_service.full_sync()

    return {
        "success": result.success,
        "contacts_fetched": result.contacts_fetched,
        "contacts_synced": result.contacts_synced,
        "contacts_skipped": result.contacts_skipped,
        "errors": result.errors,
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat(),
        "duration_seconds": result.duration_seconds,
    }


@router.post("/score", response_model=dict)
async def score_leads(request: ScoreRequest | None = None) -> dict:
    """
    Score all unscored leads.

    Applies the 4-dimension scoring algorithm:
    - Persona fit (0-25)
    - Vertical alignment (0-25)
    - Company signals (0-25)
    - Engagement data (0-25)

    Returns scoring statistics and tier distribution.
    """
    limit = request.limit if request else 1000
    started_at = datetime.now(timezone.utc)

    # Get unscored leads
    unscored_leads = supabase_client.get_unscored_leads(limit=limit)

    leads_scored = 0
    leads_skipped = 0
    errors: list[str] = []
    tier_distribution: dict[str, int] = {"hot": 0, "warm": 0, "nurture": 0, "cold": 0}

    for lead_data in unscored_leads:
        try:
            # Convert to Lead model
            lead = Lead(**lead_data)

            # Score the lead
            score_result = lead_scorer.score_lead(lead)

            # Update in database
            supabase_client.update_lead_scores(
                lead_id=lead_data["id"],
                persona_match=score_result.persona_match,
                persona_confidence=score_result.persona_confidence,
                vertical=score_result.vertical,
                persona_score=score_result.persona_score,
                vertical_score=score_result.vertical_score,
                company_score=score_result.company_score,
                engagement_score=score_result.engagement_score,
            )

            leads_scored += 1
            tier_distribution[score_result.tier.value] += 1

        except Exception as e:
            leads_skipped += 1
            errors.append(f"Error scoring lead {lead_data.get('id')}: {str(e)}")

    completed_at = datetime.now(timezone.utc)
    duration = (completed_at - started_at).total_seconds()

    return {
        "success": len(errors) == 0,
        "leads_scored": leads_scored,
        "leads_skipped": leads_skipped,
        "tier_distribution": tier_distribution,
        "errors": errors[:10],  # Limit errors in response
        "duration_seconds": duration,
    }


@router.get("/prioritized", response_model=LeadPrioritizedResponse)
async def get_prioritized_leads(
    tier: Annotated[str | None, Query(description="Filter by tier: hot, warm, nurture, cold")] = None,
    persona: Annotated[str | None, Query(description="Filter by persona match")] = None,
    vertical: Annotated[str | None, Query(description="Filter by vertical")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Results per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> LeadPrioritizedResponse:
    """
    Get leads prioritized by score.

    Returns leads ordered by total_score descending, with optional filters:
    - tier: Filter by tier (hot, warm, nurture, cold)
    - persona: Filter by matched persona
    - vertical: Filter by inferred vertical
    - limit/offset: Pagination

    Also returns total count and tier distribution for UI.
    """
    # Get prioritized leads
    leads = supabase_client.get_prioritized_leads(
        tier=tier,
        persona=persona,
        vertical=vertical,
        limit=limit,
        offset=offset,
    )

    # Get counts for context
    total_count = supabase_client.get_total_lead_count()
    tier_counts = supabase_client.get_lead_count_by_tier()

    return LeadPrioritizedResponse(
        leads=leads,
        total_count=total_count,
        tier_counts=tier_counts,
        query={
            "tier": tier,
            "persona": persona,
            "vertical": vertical,
            "limit": limit,
            "offset": offset,
        },
    )


@router.get("/{lead_id}", response_model=dict)
async def get_lead_by_id(lead_id: str) -> dict:
    """
    Get a single lead by ID.

    Returns full lead data including:
    - Contact info (email, name, company, title)
    - Score breakdown (persona, vertical, company, engagement)
    - Tier assignment
    - HubSpot metadata
    """
    lead = supabase_client.get_lead_by_id(lead_id)

    if not lead:
        raise HTTPException(
            status_code=404,
            detail=f"Lead with ID {lead_id} not found",
        )

    return lead
