"""Pydantic schemas for lead intelligence and scoring."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LeadTier(str, Enum):
    """Lead quality tier based on total score."""

    HOT = "hot"  # 85+ points - immediate outreach
    WARM = "warm"  # 70-84 points - this week
    NURTURE = "nurture"  # 50-69 points - sequence
    COLD = "cold"  # <50 points - long nurture


class Lead(BaseModel):
    """Lead model matching Supabase schema."""

    id: str | None = None
    hubspot_id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    title: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    industry: str | None = None

    # Scoring fields
    persona_match: str | None = None
    persona_confidence: float = 0.0
    vertical: str | None = None
    persona_score: int = 0
    vertical_score: int = 0
    company_score: int = 0
    engagement_score: int = 0
    total_score: int = 0
    tier: LeadTier = LeadTier.COLD

    # HubSpot metadata
    hubspot_owner_id: str | None = None
    lifecycle_stage: str | None = None
    lead_status: str | None = None
    last_activity_date: datetime | None = None
    contact_count: int = 0
    last_contacted: datetime | None = None

    # Timestamps
    synced_at: datetime | None = None
    scored_at: datetime | None = None
    hubspot_created_at: datetime | None = None
    hubspot_updated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LeadCreate(BaseModel):
    """Lead creation from HubSpot sync."""

    hubspot_id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    title: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    industry: str | None = None

    # HubSpot metadata
    hubspot_owner_id: str | None = None
    lifecycle_stage: str | None = None
    lead_status: str | None = None
    last_activity_date: datetime | None = None
    contact_count: int = 0
    last_contacted: datetime | None = None
    hubspot_created_at: datetime | None = None
    hubspot_updated_at: datetime | None = None


class LeadScore(BaseModel):
    """Lead score breakdown."""

    lead_id: str
    persona_match: str | None = None
    persona_confidence: float = Field(ge=0.0, le=1.0)
    vertical: str | None = None
    persona_score: int = Field(ge=0, le=25)
    vertical_score: int = Field(ge=0, le=25)
    company_score: int = Field(ge=0, le=25)
    engagement_score: int = Field(ge=0, le=25)
    total_score: int = Field(ge=0, le=100)
    tier: LeadTier


class SyncResult(BaseModel):
    """Result of a HubSpot sync operation."""

    success: bool
    contacts_fetched: int
    contacts_synced: int
    contacts_skipped: int
    errors: list[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime
    duration_seconds: float

    @property
    def has_errors(self) -> bool:
        """Check if sync had errors."""
        return len(self.errors) > 0


class ScoringResult(BaseModel):
    """Result of a lead scoring operation."""

    success: bool
    leads_scored: int
    leads_skipped: int
    tier_distribution: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float


class LeadPrioritizedQuery(BaseModel):
    """Query parameters for prioritized leads."""

    tier: LeadTier | None = None
    persona: str | None = None
    vertical: str | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class LeadPrioritizedResponse(BaseModel):
    """Response for prioritized leads query."""

    leads: list[Lead]
    total_count: int
    tier_counts: dict[str, int] = Field(default_factory=dict)
    query: LeadPrioritizedQuery
