"""University account scoring and management endpoints.

Endpoints for building target university account lists, scoring them,
and identifying gaps (A/B accounts with no decision-maker contacts).

Supports the weekly workflow:
- Monday: Import Carnegie classification data as target accounts
- Tuesday: Score and tier all accounts
- Wednesday: Create views by tier, share with leadership
- Thursday: Identify A-tier gaps, research decision-makers
- Friday: Add contacts, prepare outreach sequences
"""

import json
import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.data.university_schemas import (
    AccountTier,
    UniversityAccount,
    UniversityAccountCreate,
    UniversityAccountListResponse,
    UniversityAccountResponse,
    UniversityBatchImportRequest,
    UniversityBatchImportResponse,
    UniversityBatchImportResult,
    UniversityGapAnalysis,
)
from app.middleware.auth import require_auth
from app.services.database.supabase_client import supabase_client
from app.services.scoring.university_scorer import university_scorer

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/university-accounts",
    tags=["university-accounts"],
    dependencies=[Depends(require_auth)],
)


# =============================================================================
# Score a Single Account
# =============================================================================


@router.post("", response_model=UniversityAccountResponse)
async def create_and_score_account(
    account: UniversityAccountCreate,
) -> UniversityAccountResponse:
    """
    Create or update a university account and score it.

    Scores the account across 5 dimensions:
    - Carnegie Classification (25%)
    - Enrollment Size (20%)
    - Technology Signals (20%)
    - Engagement Level (15%)
    - Strategic Fit (15%)

    Returns the scored account with tier assignment and recommended next action.
    """
    total_score, tier, breakdown, missing_data = university_scorer.score_account(account)
    next_action = university_scorer.determine_next_action(tier, missing_data, account)

    # Build record for persistence
    now = datetime.now(timezone.utc).isoformat()
    record: dict[str, Any] = {
        "name": account.name,
        "domain": account.domain,
        "ipeds_unitid": account.ipeds_unitid,
        "hubspot_company_id": account.hubspot_company_id,
        "carnegie_classification": account.carnegie_classification.value if account.carnegie_classification else None,
        "institution_type": account.institution_type.value if account.institution_type else None,
        "enrollment": account.enrollment,
        "faculty_count": account.faculty_count,
        "employee_count": account.employee_count,
        "city": account.city,
        "state": account.state,
        "zip_code": account.zip_code,
        "lms_platform": account.lms_platform,
        "video_platform": account.video_platform,
        "av_system": account.av_system,
        "tech_stack": json.dumps(account.tech_stack),
        "athletic_division": account.athletic_division.value if account.athletic_division else None,
        "is_existing_customer": account.is_existing_customer,
        "has_active_opportunity": account.has_active_opportunity,
        "contact_count": account.contact_count,
        "decision_maker_count": account.decision_maker_count,
        "total_score": total_score,
        "account_tier": tier.value,
        "score_breakdown": json.dumps(breakdown.model_dump()),
        "scored_at": now,
        "updated_at": now,
    }

    # Persist to Supabase
    try:
        saved = supabase_client.upsert_university_account(record)
        record_id = saved.get("id")
    except Exception as e:
        logger.warning(f"Failed to persist university account: {e}")
        record_id = None

    university = UniversityAccount(
        id=record_id,
        name=account.name,
        domain=account.domain,
        ipeds_unitid=account.ipeds_unitid,
        hubspot_company_id=account.hubspot_company_id,
        carnegie_classification=account.carnegie_classification,
        institution_type=account.institution_type,
        enrollment=account.enrollment,
        faculty_count=account.faculty_count,
        employee_count=account.employee_count,
        city=account.city,
        state=account.state,
        zip_code=account.zip_code,
        lms_platform=account.lms_platform,
        video_platform=account.video_platform,
        av_system=account.av_system,
        tech_stack=account.tech_stack,
        athletic_division=account.athletic_division,
        is_existing_customer=account.is_existing_customer,
        has_active_opportunity=account.has_active_opportunity,
        contact_count=account.contact_count,
        decision_maker_count=account.decision_maker_count,
        total_score=total_score,
        account_tier=tier,
        score_breakdown=breakdown,
        scored_at=now,
    )

    return UniversityAccountResponse(
        account=university,
        next_action=next_action,
        missing_data=missing_data,
    )


# =============================================================================
# Batch Import (Carnegie CSV → Scored Accounts)
# =============================================================================


@router.post("/batch", response_model=UniversityBatchImportResponse)
async def batch_import_accounts(
    request: UniversityBatchImportRequest,
) -> UniversityBatchImportResponse:
    """
    Batch import and score university accounts.

    Designed for importing Carnegie Classification exports:
    1. Filter R1/R2 universities from https://carnegieclassifications.acenet.edu/
    2. Export to CSV, map columns to UniversityAccountCreate fields
    3. POST the batch here for scoring and persistence

    Returns tier distribution and per-account results.
    """
    results: list[UniversityBatchImportResult] = []
    tier_distribution: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0}
    scored = 0
    failed = 0

    records_to_upsert: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()

    for account in request.accounts:
        try:
            total_score, tier, breakdown, _missing = university_scorer.score_account(account)

            record: dict[str, Any] = {
                "name": account.name,
                "domain": account.domain,
                "ipeds_unitid": account.ipeds_unitid,
                "hubspot_company_id": account.hubspot_company_id,
                "carnegie_classification": account.carnegie_classification.value if account.carnegie_classification else None,
                "institution_type": account.institution_type.value if account.institution_type else None,
                "enrollment": account.enrollment,
                "faculty_count": account.faculty_count,
                "employee_count": account.employee_count,
                "city": account.city,
                "state": account.state,
                "zip_code": account.zip_code,
                "lms_platform": account.lms_platform,
                "video_platform": account.video_platform,
                "av_system": account.av_system,
                "tech_stack": json.dumps(account.tech_stack),
                "athletic_division": account.athletic_division.value if account.athletic_division else None,
                "is_existing_customer": account.is_existing_customer,
                "has_active_opportunity": account.has_active_opportunity,
                "contact_count": account.contact_count,
                "decision_maker_count": account.decision_maker_count,
                "total_score": total_score,
                "account_tier": tier.value,
                "score_breakdown": json.dumps(breakdown.model_dump()),
                "scored_at": now,
                "updated_at": now,
            }
            records_to_upsert.append(record)

            tier_distribution[tier.value] += 1
            scored += 1

            results.append(UniversityBatchImportResult(
                name=account.name,
                total_score=total_score,
                account_tier=tier,
            ))

        except Exception as e:
            failed += 1
            results.append(UniversityBatchImportResult(
                name=account.name,
                total_score=0.0,
                account_tier=AccountTier.D,
                error=str(e),
            ))

    # Batch persist
    if records_to_upsert:
        try:
            supabase_client.upsert_university_accounts_batch(records_to_upsert)
        except Exception as e:
            logger.error(f"Batch persist failed: {e}")

    logger.info(
        "University batch import completed",
        extra={
            "source": request.source,
            "total": len(request.accounts),
            "scored": scored,
            "failed": failed,
            "tier_distribution": tier_distribution,
        },
    )

    return UniversityBatchImportResponse(
        total=len(request.accounts),
        scored=scored,
        failed=failed,
        tier_distribution=tier_distribution,
        results=results,
    )


# =============================================================================
# List & Filter Accounts
# =============================================================================


@router.get("", response_model=UniversityAccountListResponse)
async def list_university_accounts(
    tier: Annotated[str | None, Query(description="Filter by tier: A, B, C, D")] = None,
    state: Annotated[str | None, Query(description="Filter by US state (2-letter)")] = None,
    carnegie: Annotated[str | None, Query(description="Filter by Carnegie classification")] = None,
    max_contacts: Annotated[int | None, Query(description="Only accounts with <= N contacts")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UniversityAccountListResponse:
    """
    List university accounts with optional filters.

    Supports the 3 HubSpot views:
    - View 1 (A-tier, no contacts): ?tier=A&max_contacts=0
    - View 2 (B-tier, few contacts): ?tier=B&max_contacts=2
    - View 3 (A/B no decision-maker): Use /gap-analysis endpoint instead
    """
    accounts_data = supabase_client.get_university_accounts_filtered(
        tier=tier,
        state=state,
        carnegie=carnegie,
        max_contacts=max_contacts,
        limit=limit,
        offset=offset,
    )

    accounts = [_dict_to_account(a) for a in accounts_data]

    return UniversityAccountListResponse(
        accounts=accounts,
        total_count=len(accounts),
        filters_applied={
            "tier": tier,
            "state": state,
            "carnegie": carnegie,
            "max_contacts": max_contacts,
            "limit": limit,
            "offset": offset,
        },
    )


# =============================================================================
# Gap Analysis
# =============================================================================


class GapAnalysisResponse(BaseModel):
    """Response for gap analysis endpoint."""

    gaps: list[UniversityGapAnalysis]
    total_gaps: int
    summary: dict[str, int] = Field(description="Count by gap type")


@router.get("/gap-analysis", response_model=GapAnalysisResponse)
async def get_gap_analysis(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> GapAnalysisResponse:
    """
    Identify A/B-tier accounts that need contact research.

    This is the weekly review endpoint:
    - Which high-value accounts have zero contacts?
    - Which have contacts but no decision-maker?

    Gap types:
    - 'no_contacts': Zero contacts on file (research needed)
    - 'no_decision_maker': Has contacts but no Director/VP/Chief
    - 'ready': Has decision-maker, ready for outreach
    """
    # Get all A/B accounts
    a_accounts = supabase_client.get_university_accounts_by_tier("A", limit=200)
    b_accounts = supabase_client.get_university_accounts_by_tier("B", limit=200)
    all_accounts = a_accounts + b_accounts

    gaps: list[UniversityGapAnalysis] = []
    summary: dict[str, int] = {"no_contacts": 0, "no_decision_maker": 0, "ready": 0}

    for acct in all_accounts:
        contact_count = acct.get("contact_count", 0)
        dm_count = acct.get("decision_maker_count", 0)

        if contact_count == 0:
            gap_type = "no_contacts"
            action = (
                "Use LinkedIn Sales Navigator to find 'Director AV' OR "
                "'Director IT' OR 'Manager Technology Services'. Add to HubSpot."
            )
        elif dm_count == 0:
            gap_type = "no_decision_maker"
            action = (
                f"Has {contact_count} contact(s) but no decision-maker. "
                "Research existing contacts for budget authority or find Director/VP-level."
            )
        else:
            gap_type = "ready"
            action = "Has decision-maker on file. Generate call brief and begin outreach."

        summary[gap_type] += 1

        gaps.append(UniversityGapAnalysis(
            account_id=acct.get("id", ""),
            name=acct.get("name", ""),
            account_tier=AccountTier(acct.get("account_tier", "D")),
            total_score=float(acct.get("total_score", 0)),
            contact_count=contact_count,
            decision_maker_count=dm_count,
            gap_type=gap_type,
            recommended_action=action,
        ))

    # Sort: no_contacts first, then no_decision_maker, then ready
    gap_order = {"no_contacts": 0, "no_decision_maker": 1, "ready": 2}
    gaps.sort(key=lambda g: (gap_order.get(g.gap_type, 3), -g.total_score))

    # Apply limit
    gaps = gaps[:limit]

    return GapAnalysisResponse(
        gaps=gaps,
        total_gaps=len(gaps),
        summary=summary,
    )


# =============================================================================
# Tier Summary
# =============================================================================


class TierSummaryResponse(BaseModel):
    """Summary of account distribution across tiers."""

    tier_counts: dict[str, int]
    total_accounts: int
    a_tier_no_contacts: int = Field(description="A-tier accounts needing research")
    b_tier_no_contacts: int = Field(description="B-tier accounts needing research")


@router.get("/summary", response_model=TierSummaryResponse)
async def get_tier_summary() -> TierSummaryResponse:
    """
    Get summary of university account tier distribution.

    Quick overview for leadership:
    - How many accounts in each tier?
    - How many high-value accounts still need contacts?
    """
    tier_counts = supabase_client.get_university_account_tier_counts()
    gap_accounts = supabase_client.get_university_gap_accounts(limit=500)

    a_no_contacts = sum(
        1 for a in gap_accounts if a.get("account_tier") == "A"
    )
    b_no_contacts = sum(
        1 for a in gap_accounts if a.get("account_tier") == "B"
    )

    return TierSummaryResponse(
        tier_counts=tier_counts,
        total_accounts=sum(tier_counts.values()),
        a_tier_no_contacts=a_no_contacts,
        b_tier_no_contacts=b_no_contacts,
    )


# =============================================================================
# Single Account Operations
# =============================================================================


@router.get("/{account_id}", response_model=UniversityAccountResponse)
async def get_university_account(account_id: str) -> UniversityAccountResponse:
    """Get a single university account by ID with full score breakdown."""
    data = supabase_client.get_university_account(account_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    account = _dict_to_account(data)

    # Determine next action based on current state
    tier = account.account_tier
    missing: list[str] = []
    if not account.carnegie_classification:
        missing.append("carnegie_classification")
    if not account.enrollment:
        missing.append("enrollment")
    if account.contact_count == 0:
        missing.append("contacts")

    create_data = UniversityAccountCreate(
        name=account.name,
        contact_count=account.contact_count,
        decision_maker_count=account.decision_maker_count,
    )
    next_action = university_scorer.determine_next_action(tier, missing, create_data)

    return UniversityAccountResponse(
        account=account,
        next_action=next_action,
        missing_data=missing,
    )


@router.patch("/{account_id}/contacts")
async def update_account_contacts(
    account_id: str,
    contact_count: int,
    decision_maker_count: int = 0,
) -> dict[str, Any]:
    """
    Update contact counts for a university account.

    Call this after enriching contacts (e.g., Clay batch or LinkedIn research).
    Triggers re-scoring since engagement_level dimension changes.
    """
    existing = supabase_client.get_university_account(account_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    # Update contacts
    supabase_client.update_university_account_contacts(
        account_id=account_id,
        contact_count=contact_count,
        decision_maker_count=decision_maker_count,
    )

    # Re-score with updated contact data
    account_create = UniversityAccountCreate(
        name=existing.get("name", ""),
        domain=existing.get("domain"),
        carnegie_classification=existing.get("carnegie_classification"),
        institution_type=existing.get("institution_type"),
        enrollment=existing.get("enrollment"),
        lms_platform=existing.get("lms_platform"),
        video_platform=existing.get("video_platform"),
        av_system=existing.get("av_system"),
        athletic_division=existing.get("athletic_division"),
        is_existing_customer=existing.get("is_existing_customer", False),
        has_active_opportunity=existing.get("has_active_opportunity", False),
        contact_count=contact_count,
        decision_maker_count=decision_maker_count,
    )

    total_score, tier, breakdown, _missing = university_scorer.score_account(account_create)

    # Update score in DB
    now = datetime.now(timezone.utc).isoformat()
    supabase_client.upsert_university_account({
        "id": account_id,
        "name": existing.get("name", ""),
        "state": existing.get("state"),
        "contact_count": contact_count,
        "decision_maker_count": decision_maker_count,
        "total_score": total_score,
        "account_tier": tier.value,
        "score_breakdown": json.dumps(breakdown.model_dump()),
        "scored_at": now,
        "updated_at": now,
    })

    return {
        "account_id": account_id,
        "contact_count": contact_count,
        "decision_maker_count": decision_maker_count,
        "new_score": total_score,
        "new_tier": tier.value,
    }


# =============================================================================
# Helpers
# =============================================================================


def _dict_to_account(data: dict[str, Any]) -> UniversityAccount:
    """Convert a Supabase row dict to a UniversityAccount model."""
    # Parse score_breakdown from JSON string or dict
    breakdown_raw = data.get("score_breakdown")
    breakdown = None
    if breakdown_raw:
        if isinstance(breakdown_raw, str):
            import json as json_mod
            breakdown_raw = json_mod.loads(breakdown_raw)
        if isinstance(breakdown_raw, dict):
            from app.data.university_schemas import AccountScoreBreakdown
            try:
                breakdown = AccountScoreBreakdown(**breakdown_raw)
            except Exception:
                breakdown = None

    # Parse tech_stack from JSON string or list
    tech_stack_raw = data.get("tech_stack", [])
    if isinstance(tech_stack_raw, str):
        import json as json_mod
        try:
            tech_stack_raw = json_mod.loads(tech_stack_raw)
        except Exception:
            tech_stack_raw = []

    return UniversityAccount(
        id=data.get("id"),
        name=data.get("name", ""),
        domain=data.get("domain"),
        ipeds_unitid=data.get("ipeds_unitid"),
        hubspot_company_id=data.get("hubspot_company_id"),
        carnegie_classification=data.get("carnegie_classification"),
        institution_type=data.get("institution_type"),
        enrollment=data.get("enrollment"),
        faculty_count=data.get("faculty_count"),
        employee_count=data.get("employee_count"),
        city=data.get("city"),
        state=data.get("state"),
        zip_code=data.get("zip_code"),
        lms_platform=data.get("lms_platform"),
        video_platform=data.get("video_platform"),
        av_system=data.get("av_system"),
        tech_stack=tech_stack_raw if isinstance(tech_stack_raw, list) else [],
        athletic_division=data.get("athletic_division"),
        is_existing_customer=data.get("is_existing_customer", False),
        has_active_opportunity=data.get("has_active_opportunity", False),
        contact_count=data.get("contact_count", 0),
        decision_maker_count=data.get("decision_maker_count", 0),
        total_score=float(data.get("total_score", 0)),
        account_tier=AccountTier(data.get("account_tier", "D")),
        score_breakdown=breakdown,
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        scored_at=data.get("scored_at"),
    )
