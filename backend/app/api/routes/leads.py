"""Leads API routes for lead management and scoring.

Endpoints:
- POST /api/leads/sync - Trigger HubSpot sync
- POST /api/leads/score - Score unscored leads
- POST /api/leads/ingest - Ingest leads from Lead Harvester (with tiered enrichment)
- GET /api/leads/prioritized - Get leads by tier/persona
- GET /api/leads/{id} - Get single lead

IMPORTANT: Phone numbers are GOLD for BDR outreach.
Uses tiered enrichment to save credits while prioritizing ATL decision-makers.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.data.lead_schemas import (
    Lead,
)
from app.services.database.supabase_client import supabase_client
from app.services.enrichment.apollo import TieredEnrichmentResult, apollo_client
from app.services.hubspot.sync import hubspot_sync_service
from app.services.langgraph.agents import QualificationAgent
from app.services.langgraph.states import QualificationTier
from app.services.langgraph.tools.harvester_mapper import (
    enrich_phone_numbers,
    get_best_phone,
    map_harvester_to_lead,
)
from app.services.scoring.atl_detector import is_atl_decision_maker
from app.services.scoring.lead_scorer import lead_scorer

# Configure logger for audit trails
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])

# Singleton agent instance for ingest endpoint
_qualification_agent = QualificationAgent()


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
# Lead Harvester Ingest Models
# =============================================================================


class HarvesterLeadInput(BaseModel):
    """
    Single lead from Lead Harvester export.

    IMPORTANT: Phone numbers are GOLD for BDR outreach.
    Always prioritize phone enrichment - more phones = more dials = more deals.
    """

    external_id: str = Field(description="Unique source ID (IPEDS UNITID, permit #, etc.)")
    source: str = Field(description="Source: ipeds_higher_ed, cms_hospitals, etc.")
    company_name: str = Field(description="Organization/company name")
    industry: str | None = Field(default=None, description="Vertical from Harvester")
    employees: int | None = Field(default=None, description="Employee count (may need enrichment)")
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    website: str | None = None

    # Harvester scoring (A/B/C/D → 0-100)
    harvester_score: float | None = Field(default=None, description="0-100 from Harvester's scoring")
    harvester_tier: str | None = Field(default=None, description="A/B/C/D tier from Harvester")

    # Contact info (CRITICAL for BDR outreach)
    contact_name: str | None = Field(default=None, description="Contact full name")
    contact_title: str | None = Field(default=None, description="Job title for buying authority")
    contact_email: str | None = Field(default=None, description="Email address")

    # PHONE NUMBERS - Priority enrichment target (phones are GOLD!)
    direct_phone: str | None = Field(default=None, description="Direct dial (best)")
    work_phone: str | None = Field(default=None, description="Office line")
    mobile_phone: str | None = Field(default=None, description="Cell phone")
    company_phone: str | None = Field(default=None, description="Main switchboard (fallback)")

    tech_stack: list[str] | None = Field(default=None, description="Known technologies")

    # Raw data passthrough
    raw_data: dict[str, Any] | None = Field(default=None, description="Original Harvester data")


class LeadIngestRequest(BaseModel):
    """
    Batch ingest request from Lead Harvester.

    Uses tiered enrichment by default to save Apollo credits:
    - Phase 1 (1 credit): Verify company + identify persona
    - Phase 2 (8 credits): Phone enrichment ONLY for ATL decision-makers

    PHONES ARE GOLD - but only for people Tim will actually call.
    """

    source: str = Field(default="lead_harvester", description="Data source identifier")
    batch_id: str | None = Field(default=None, description="For tracking batch operations")
    leads: list[HarvesterLeadInput] = Field(description="Leads to ingest and qualify")

    # Enrichment controls
    enrich: bool = Field(
        default=True,
        description="Call Apollo for full enrichment",
    )
    enrich_phones: bool = Field(
        default=True,
        description="ALWAYS TRUE by default - phones are GOLD for BDR outreach",
    )
    tiered_enrichment: bool = Field(
        default=True,
        description="Use smart tiered enrichment (1 credit basic, +8 for ATL phones only). "
        "Saves ~67% on credits by only revealing phones for ATL decision-makers.",
    )
    concurrency: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Max concurrent lead processing",
    )


class DimensionScoreResponse(BaseModel):
    """Score breakdown for a single ICP dimension."""

    category: str
    raw_score: int
    weighted_score: float
    reason: str
    confidence: float


class ScoreBreakdownResponse(BaseModel):
    """Complete ICP score breakdown for ingest response."""

    company_size: DimensionScoreResponse
    industry_vertical: DimensionScoreResponse
    use_case_fit: DimensionScoreResponse
    tech_stack_signals: DimensionScoreResponse
    buying_authority: DimensionScoreResponse


class NextActionResponse(BaseModel):
    """Recommended next action."""

    action_type: str
    description: str
    priority: str
    ae_involvement: bool
    missing_info: list[str]


class LeadIngestResult(BaseModel):
    """
    Single lead qualification result.

    PHONE NUMBERS are prioritized output for BDR calling - but only for ATLs.
    Tiered enrichment saves credits by only revealing phones for decision-makers.
    """

    external_id: str
    email: str | None
    total_score: float = Field(description="Weighted ICP score (0-100)")
    tier: QualificationTier = Field(description="Qualification tier")
    score_breakdown: ScoreBreakdownResponse | None = None
    confidence: float = Field(default=0.0, description="Scoring confidence (0.0-1.0)")
    next_action: NextActionResponse | None = None
    persona_match: str | None = Field(default=None, description="Matched persona if detected")
    missing_info: list[str] = Field(default_factory=list, description="Data gaps identified")
    error: str | None = Field(default=None, description="Error message if processing failed")

    # ATL Decision-Maker Detection (for tiered enrichment)
    is_atl: bool = Field(default=False, description="ATL decision-maker worth calling")
    atl_persona: str | None = Field(default=None, description="Matched ATL persona (e.g., av_director)")
    atl_confidence: float = Field(default=0.0, description="Confidence in ATL determination")
    atl_reason: str | None = Field(default=None, description="Why this is/isn't ATL")

    # Credit tracking (for ROI analysis)
    credits_used: int = Field(default=0, description="Apollo credits consumed for this lead")

    # PHONE NUMBERS - Priority output for BDR calling (phones are GOLD!)
    direct_phone: str | None = Field(default=None, description="Best: direct dial")
    work_phone: str | None = Field(default=None, description="Office line")
    mobile_phone: str | None = Field(default=None, description="Cell phone")
    company_phone: str | None = Field(default=None, description="Switchboard fallback")
    phone_source: str | None = Field(default=None, description="Where we got the phone (apollo, harvester)")
    best_phone: str | None = Field(default=None, description="Best available phone for dialing")


class LeadIngestSummary(BaseModel):
    """
    Batch summary statistics.

    Tracks ATL detection and credit usage for ROI analysis.
    PHONES ARE GOLD - but only for ATL decision-makers Tim will call.
    """

    total: int = Field(description="Total leads processed")
    qualified: int = Field(description="Successfully qualified")
    failed: int = Field(description="Processing failures")
    tier_1: int = Field(default=0, description="High-priority leads (70+)")
    tier_2: int = Field(default=0, description="Standard sequence (50-69)")
    tier_3: int = Field(default=0, description="Marketing nurture (30-49)")
    not_icp: int = Field(default=0, description="Disqualified (<30)")
    enrichment_needed: int = Field(default=0, description="Leads needing more data")

    # ATL Decision-Maker metrics
    atl_leads: int = Field(default=0, description="ATL decision-makers found (worth calling)")
    non_atl_leads: int = Field(default=0, description="Non-ATL contacts (saved credits)")

    # Credit tracking (for ROI analysis)
    total_credits_used: int = Field(default=0, description="Total Apollo credits consumed")
    credits_saved: int = Field(
        default=0,
        description="Credits saved by tiered approach (vs 8 credits per lead)",
    )

    # Phone metrics (PHONES ARE GOLD!)
    leads_with_direct_phone: int = Field(default=0, description="Gold - direct dial available")
    leads_with_any_phone: int = Field(default=0, description="Silver - some phone available")
    leads_needing_phone_research: int = Field(default=0, description="Manual research needed")


class LeadIngestResponse(BaseModel):
    """Full batch response from lead ingest."""

    batch_id: str = Field(description="Batch identifier for tracking")
    results: list[LeadIngestResult] = Field(description="Per-lead qualification results")
    summary: LeadIngestSummary = Field(description="Batch statistics")


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


@router.post("/ingest", response_model=LeadIngestResponse)
async def ingest_leads(request: LeadIngestRequest) -> LeadIngestResponse:
    """
    Ingest and qualify leads from Lead Harvester exports.

    Uses TIERED ENRICHMENT to save Apollo credits:
    - Phase 1 (1 credit): Verify company + identify ATL decision-makers
    - Phase 2 (8 credits): Phone enrichment ONLY for ATL decision-makers

    Credit Economics (typical 1,000 lead batch):
    - Old approach: 8 credits × 1,000 = 8,000 credits
    - Tiered (15-25% ATL): 1,000 + (8 × 200) = 2,600 credits (~67% savings)

    PHONES ARE GOLD - but only for people Tim will actually call.

    Args:
        request: LeadIngestRequest with leads and enrichment options

    Returns:
        LeadIngestResponse with qualification results, ATL status, and credit tracking
    """
    batch_id = request.batch_id or f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    semaphore = asyncio.Semaphore(request.concurrency)
    started_at = datetime.now(timezone.utc)

    # Audit log: batch start
    logger.info(
        "Lead ingest batch started",
        extra={
            "batch_id": batch_id,
            "lead_count": len(request.leads),
            "tiered_enrichment": request.tiered_enrichment,
            "enrich": request.enrich,
            "enrich_phones": request.enrich_phones,
        },
    )

    async def process_single(harvester_lead: HarvesterLeadInput) -> LeadIngestResult:
        """Process a single lead with tiered enrichment for credit optimization."""
        async with semaphore:
            try:
                # Map Harvester data to Lead model
                lead = map_harvester_to_lead(
                    external_id=harvester_lead.external_id,
                    source=harvester_lead.source,
                    company_name=harvester_lead.company_name,
                    contact_email=harvester_lead.contact_email,
                    contact_name=harvester_lead.contact_name,
                    contact_title=harvester_lead.contact_title,
                    industry=harvester_lead.industry,
                    employees=harvester_lead.employees,
                    city=harvester_lead.city,
                    state=harvester_lead.state,
                    website=harvester_lead.website,
                    direct_phone=harvester_lead.direct_phone,
                    mobile_phone=harvester_lead.mobile_phone,
                    work_phone=harvester_lead.work_phone,
                    company_phone=harvester_lead.company_phone,
                )

                # Initialize tracking variables
                phone_data: dict[str, Any] = {}
                apollo_data: dict[str, Any] | None = None
                tiered_result: TieredEnrichmentResult | None = None
                is_atl = False
                atl_persona: str | None = None
                atl_confidence = 0.0
                atl_reason: str | None = None
                credits_used = 0

                # Enrichment logic
                if request.enrich_phones or request.enrich:
                    has_valid_email = lead.email and "@placeholder" not in lead.email

                    if has_valid_email:
                        if request.tiered_enrichment:
                            # TIERED ENRICHMENT: Smart credit allocation
                            # Phase 1 (1 credit): Basic enrichment to identify ATL
                            # Phase 2 (8 credits): Phone reveal ONLY for ATL
                            try:
                                tiered_result = await apollo_client.tiered_enrich(
                                    email=lead.email,
                                    title=harvester_lead.contact_title,
                                )
                                apollo_data = tiered_result.data
                                credits_used = tiered_result.credits_used
                                is_atl = tiered_result.is_atl
                                atl_persona = tiered_result.persona_match

                                if tiered_result.atl_match:
                                    atl_confidence = tiered_result.atl_match.confidence
                                    atl_reason = tiered_result.atl_match.reason

                                # Audit log: enrichment result
                                logger.debug(
                                    "Tiered enrichment completed",
                                    extra={
                                        "batch_id": batch_id,
                                        "external_id": harvester_lead.external_id,
                                        "email": lead.email,
                                        "is_atl": is_atl,
                                        "atl_persona": atl_persona,
                                        "phone_revealed": tiered_result.phone_revealed,
                                        "credits_used": credits_used,
                                    },
                                )
                            except Exception as e:
                                # Log rate limit errors specially
                                error_msg = str(e)
                                if "rate limit" in error_msg.lower():
                                    logger.warning(
                                        "Apollo rate limit hit",
                                        extra={
                                            "batch_id": batch_id,
                                            "external_id": harvester_lead.external_id,
                                            "error": error_msg,
                                        },
                                    )
                                else:
                                    logger.error(
                                        "Tiered enrichment failed",
                                        extra={
                                            "batch_id": batch_id,
                                            "external_id": harvester_lead.external_id,
                                            "error": error_msg,
                                        },
                                    )
                                # Fall back to Harvester phones
                                apollo_data = None
                        else:
                            # LEGACY MODE: Always reveal phones (8 credits per lead)
                            try:
                                apollo_data = await apollo_client.enrich_contact(
                                    lead.email, reveal_phone=True
                                )
                                credits_used = 8  # Phone reveal cost

                                # Still do ATL detection for reporting
                                atl_match = is_atl_decision_maker(
                                    title=apollo_data.get("title") if apollo_data else harvester_lead.contact_title,
                                    seniority=apollo_data.get("seniority") if apollo_data else None,
                                )
                                is_atl = atl_match.is_atl
                                atl_persona = atl_match.persona_id
                                atl_confidence = atl_match.confidence
                                atl_reason = atl_match.reason
                            except Exception as e:
                                logger.error(
                                    "Legacy enrichment failed",
                                    extra={
                                        "batch_id": batch_id,
                                        "external_id": harvester_lead.external_id,
                                        "error": str(e),
                                    },
                                )
                                apollo_data = None
                    else:
                        # No valid email - use title for ATL detection without API call
                        atl_match = is_atl_decision_maker(
                            title=harvester_lead.contact_title,
                            seniority=None,
                        )
                        is_atl = atl_match.is_atl
                        atl_persona = atl_match.persona_id
                        atl_confidence = atl_match.confidence
                        atl_reason = atl_match.reason

                    # Extract and prioritize phone numbers
                    phone_data = enrich_phone_numbers(
                        apollo_data=apollo_data,
                        harvester_direct=harvester_lead.direct_phone,
                        harvester_mobile=harvester_lead.mobile_phone,
                        harvester_work=harvester_lead.work_phone,
                        harvester_company=harvester_lead.company_phone,
                    )

                # Run qualification agent
                enrichment_data = None
                if request.enrich and apollo_data:
                    enrichment_data = {"apollo": apollo_data}
                    if harvester_lead.tech_stack:
                        enrichment_data["tech_stack"] = harvester_lead.tech_stack

                result = await _qualification_agent.run(
                    lead=lead,
                    enrichment_data=enrichment_data,
                    skip_enrichment=not request.enrich,
                )

                # Build score breakdown response
                breakdown = result.get("score_breakdown", {})
                score_breakdown = None
                if breakdown:
                    score_breakdown = ScoreBreakdownResponse(
                        company_size=DimensionScoreResponse(**breakdown.get("company_size", {})),
                        industry_vertical=DimensionScoreResponse(**breakdown.get("industry_vertical", {})),
                        use_case_fit=DimensionScoreResponse(**breakdown.get("use_case_fit", {})),
                        tech_stack_signals=DimensionScoreResponse(**breakdown.get("tech_stack_signals", {})),
                        buying_authority=DimensionScoreResponse(**breakdown.get("buying_authority", {})),
                    )

                # Build next action response
                action = result.get("next_action", {})
                next_action = None
                if action:
                    next_action = NextActionResponse(
                        action_type=action.get("action_type", ""),
                        description=action.get("description", ""),
                        priority=action.get("priority", "low"),
                        ae_involvement=action.get("ae_involvement", False),
                        missing_info=action.get("missing_info", []),
                    )

                return LeadIngestResult(
                    external_id=harvester_lead.external_id,
                    email=lead.email if "@placeholder" not in lead.email else None,
                    total_score=result.get("total_score", 0.0),
                    tier=result.get("tier", QualificationTier.NOT_ICP),
                    score_breakdown=score_breakdown,
                    confidence=result.get("confidence", 0.0),
                    next_action=next_action,
                    persona_match=result.get("persona_match"),
                    missing_info=result.get("missing_info", []),
                    # ATL Decision-Maker Detection
                    is_atl=is_atl,
                    atl_persona=atl_persona,
                    atl_confidence=atl_confidence,
                    atl_reason=atl_reason,
                    # Credit tracking
                    credits_used=credits_used,
                    # PHONE NUMBERS - Priority output (phones are GOLD!)
                    direct_phone=phone_data.get("direct_phone"),
                    mobile_phone=phone_data.get("mobile_phone"),
                    work_phone=phone_data.get("work_phone"),
                    company_phone=phone_data.get("company_phone"),
                    phone_source=phone_data.get("phone_source"),
                    best_phone=phone_data.get("best_phone"),
                )

            except Exception as e:
                logger.error(
                    "Lead processing failed",
                    extra={
                        "batch_id": batch_id,
                        "external_id": harvester_lead.external_id,
                        "error": str(e),
                    },
                )
                # Return error result but don't fail batch
                return LeadIngestResult(
                    external_id=harvester_lead.external_id,
                    email=harvester_lead.contact_email,
                    total_score=0.0,
                    tier=QualificationTier.NOT_ICP,
                    error=str(e),
                    # Still include any available phone data from Harvester
                    direct_phone=harvester_lead.direct_phone,
                    mobile_phone=harvester_lead.mobile_phone,
                    work_phone=harvester_lead.work_phone,
                    company_phone=harvester_lead.company_phone,
                    phone_source="harvester" if any([
                        harvester_lead.direct_phone,
                        harvester_lead.mobile_phone,
                        harvester_lead.work_phone,
                        harvester_lead.company_phone,
                    ]) else None,
                    best_phone=get_best_phone(
                        harvester_lead.direct_phone,
                        harvester_lead.mobile_phone,
                        harvester_lead.work_phone,
                        harvester_lead.company_phone,
                    ),
                )

    # Process all leads concurrently
    tasks = [process_single(lead) for lead in request.leads]
    results = await asyncio.gather(*tasks)

    # Calculate summary statistics
    qualified = sum(1 for r in results if r.error is None)
    failed = len(results) - qualified

    tier_counts = {
        QualificationTier.TIER_1: 0,
        QualificationTier.TIER_2: 0,
        QualificationTier.TIER_3: 0,
        QualificationTier.NOT_ICP: 0,
    }
    for r in results:
        if r.error is None:
            tier_counts[r.tier] += 1

    # ATL metrics
    atl_leads = sum(1 for r in results if r.is_atl)
    non_atl_leads = len(results) - atl_leads

    # Credit metrics
    total_credits_used = sum(r.credits_used for r in results)
    # Credits saved = what we would have spent (8 per lead) minus what we actually spent
    legacy_cost = 8 * len(results)
    credits_saved = legacy_cost - total_credits_used if request.tiered_enrichment else 0

    # Phone metrics (PHONES ARE GOLD!)
    leads_with_direct = sum(1 for r in results if r.direct_phone)
    leads_with_any_phone = sum(1 for r in results if r.best_phone)
    leads_needing_phones = len(results) - leads_with_any_phone

    # Count leads needing enrichment
    enrichment_needed = sum(1 for r in results if r.missing_info)

    completed_at = datetime.now(timezone.utc)
    duration_seconds = (completed_at - started_at).total_seconds()

    summary = LeadIngestSummary(
        total=len(results),
        qualified=qualified,
        failed=failed,
        tier_1=tier_counts[QualificationTier.TIER_1],
        tier_2=tier_counts[QualificationTier.TIER_2],
        tier_3=tier_counts[QualificationTier.TIER_3],
        not_icp=tier_counts[QualificationTier.NOT_ICP],
        enrichment_needed=enrichment_needed,
        # ATL metrics
        atl_leads=atl_leads,
        non_atl_leads=non_atl_leads,
        # Credit metrics
        total_credits_used=total_credits_used,
        credits_saved=credits_saved,
        # Phone metrics (PHONES ARE GOLD!)
        leads_with_direct_phone=leads_with_direct,
        leads_with_any_phone=leads_with_any_phone,
        leads_needing_phone_research=leads_needing_phones,
    )

    # Audit log: batch complete
    logger.info(
        "Lead ingest batch completed",
        extra={
            "batch_id": batch_id,
            "total": len(results),
            "qualified": qualified,
            "failed": failed,
            "atl_leads": atl_leads,
            "non_atl_leads": non_atl_leads,
            "total_credits_used": total_credits_used,
            "credits_saved": credits_saved,
            "leads_with_direct_phone": leads_with_direct,
            "leads_with_any_phone": leads_with_any_phone,
            "duration_seconds": duration_seconds,
            "tiered_enrichment": request.tiered_enrichment,
        },
    )

    return LeadIngestResponse(
        batch_id=batch_id,
        results=list(results),
        summary=summary,
    )


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
