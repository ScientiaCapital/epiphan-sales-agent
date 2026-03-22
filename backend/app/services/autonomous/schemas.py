"""Pydantic models for the autonomous BDR pipeline."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Pipeline Configuration
# =============================================================================


class LeadSource(str, Enum):
    """Where a prospect was sourced from."""

    APOLLO = "apollo"
    HUBSPOT = "hubspot"
    CLAY = "clay"


class QueueStatus(str, Enum):
    """Outreach queue item status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    FAILED = "failed"


class RunStatus(str, Enum):
    """Autonomous run status."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunConfig(BaseModel):
    """Configuration for a pipeline run."""

    sources: list[LeadSource] = Field(
        default=[LeadSource.APOLLO, LeadSource.HUBSPOT],
        description="Which lead sources to use",
    )
    prospect_limit: int = Field(default=25, ge=1, le=200)
    credit_budget: int = Field(default=250, description="Max Apollo credits per run")
    verticals: list[str] = Field(
        default_factory=list,
        description="Target verticals (empty = all)",
    )
    personas: list[str] = Field(
        default_factory=list,
        description="Target personas (empty = all ATL)",
    )


# =============================================================================
# Lead Models
# =============================================================================


class RawLead(BaseModel):
    """Lead from any source before enrichment."""

    email: str
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    title: str | None = None
    company: str | None = None
    industry: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    source: LeadSource
    source_id: str | None = Field(default=None, description="ID in source system")
    raw_data: dict[str, Any] = Field(default_factory=dict)


class DraftEmail(BaseModel):
    """Drafted outreach email using Challenger Sale methodology."""

    subject: str
    body: str
    pain_point: str = Field(description="Primary pain point identified")
    methodology: str = Field(default="challenger", description="Sales methodology used")


# =============================================================================
# Queue & Run Models
# =============================================================================


class QueueItem(BaseModel):
    """Single outreach item in the approval queue."""

    id: str | None = None
    run_id: str
    status: QueueStatus = QueueStatus.PENDING

    # Lead
    lead_email: str
    lead_name: str | None = None
    lead_title: str | None = None
    lead_company: str | None = None
    lead_industry: str | None = None
    lead_phone: str | None = None
    lead_source: LeadSource
    lead_data: dict[str, Any] = Field(default_factory=dict)

    # Qualification
    qualification_tier: str | None = None
    qualification_score: float = 0.0
    qualification_confidence: float = 0.0
    persona_match: str | None = None
    is_atl: bool = False

    # Outreach draft
    email_subject: str | None = None
    email_body: str | None = None
    email_pain_point: str | None = None
    email_methodology: str = "challenger"
    call_brief: dict[str, Any] = Field(default_factory=dict)

    # Approval
    rejection_reason: str | None = None
    reviewer_notes: str | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    sent_at: datetime | None = None

    # Learning signals
    email_opened: bool | None = None
    email_replied: bool | None = None
    meeting_booked: bool | None = None

    created_at: datetime | None = None


class RunSummary(BaseModel):
    """Summary of a pipeline run."""

    run_id: str
    status: RunStatus
    started_at: datetime
    completed_at: datetime | None = None
    total_sourced: int = 0
    total_after_dedup: int = 0
    total_processed: int = 0
    tier_1: int = 0
    tier_2: int = 0
    tier_3: int = 0
    not_icp: int = 0
    credits_used: int = 0
    phones_found: int = 0
    errors: list[str] = Field(default_factory=list)
    config: RunConfig = Field(default_factory=RunConfig)


# =============================================================================
# Approval Workflow
# =============================================================================


class ApproveRequest(BaseModel):
    """Request to approve an outreach item."""

    reviewer_notes: str | None = None


class RejectRequest(BaseModel):
    """Request to reject an outreach item."""

    rejection_reason: str


class EditDraftRequest(BaseModel):
    """Request to edit an outreach draft before approving."""

    email_subject: str | None = None
    email_body: str | None = None
    reviewer_notes: str | None = None


class BulkActionRequest(BaseModel):
    """Request for bulk approve/reject."""

    item_ids: list[str] = Field(default_factory=list, description="Specific IDs")
    filter_tier: str | None = Field(default=None, description="Apply to all items of this tier")
    filter_source: LeadSource | None = None
    rejection_reason: str | None = None


class QueueFilter(BaseModel):
    """Filter for querying the outreach queue."""

    status: QueueStatus | None = None
    tier: str | None = None
    source: LeadSource | None = None
    run_id: str | None = None
    is_atl: bool | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


# =============================================================================
# Learning Patterns
# =============================================================================


class ApprovalPattern(BaseModel):
    """Learned approval pattern from Tim's decisions."""

    pattern_type: str
    pattern_key: str
    approved_count: int = 0
    rejected_count: int = 0
    approval_rate: float = 0.0
    last_updated: datetime | None = None


class PipelineStats(BaseModel):
    """Dashboard stats for the autonomous pipeline."""

    total_runs: int = 0
    total_processed: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    approval_rate: float = 0.0
    top_approved_industries: list[ApprovalPattern] = Field(default_factory=list)
    top_rejected_reasons: list[str] = Field(default_factory=list)
    avg_processing_time_ms: float = 0.0
    credits_used_last_7d: int = 0
