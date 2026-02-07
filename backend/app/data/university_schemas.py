"""Pydantic schemas for university account scoring and management.

University accounts are scored at the institution level (not contact level)
using 5 dimensions tailored to higher education AV/video needs:

1. Carnegie Classification (25%) - Research intensity = tech budget proxy
2. Enrollment Size (25%) - More students = more rooms = more AV need
3. Technology Signals (20%) - Existing AV/LMS = readiness to buy
4. Engagement Level (15%) - Existing contacts and interactions
5. Strategic Fit (15%) - Public/private, athletics, closed-won history

Account Tiers:
- A (75+): Priority outreach, find decision-makers immediately
- B (50-74): Standard outreach, batch enrich contacts
- C (30-49): Marketing nurture
- D (<30): Low priority
"""

from enum import Enum

from pydantic import BaseModel, Field


class CarnegieClassification(str, Enum):
    """Carnegie Classification of Institutions of Higher Education."""

    R1 = "r1"  # Doctoral Universities - Very High Research Activity
    R2 = "r2"  # Doctoral Universities - High Research Activity
    D_PU = "d_pu"  # Doctoral/Professional Universities
    M1 = "m1"  # Master's Colleges & Universities - Larger Programs
    M2 = "m2"  # Master's Colleges & Universities - Medium Programs
    M3 = "m3"  # Master's Colleges & Universities - Smaller Programs
    BACCALAUREATE = "baccalaureate"  # Baccalaureate Colleges
    ASSOCIATE = "associate"  # Associate's Colleges
    SPECIAL_FOCUS = "special_focus"  # Special Focus Institutions
    TRIBAL = "tribal"  # Tribal Colleges
    OTHER = "other"


class AccountTier(str, Enum):
    """University account priority tier."""

    A = "A"  # 75+: Immediate outreach, find decision-makers
    B = "B"  # 50-74: Standard outreach, batch enrich
    C = "C"  # 30-49: Marketing nurture
    D = "D"  # <30: Low priority


class InstitutionType(str, Enum):
    """Public vs private classification."""

    PUBLIC = "public"
    PRIVATE_NONPROFIT = "private_nonprofit"
    PRIVATE_FOR_PROFIT = "private_for_profit"


class AthleticDivision(str, Enum):
    """NCAA athletic division (streaming needs proxy)."""

    NCAA_D1 = "ncaa_d1"  # Division I - highest streaming demand
    NCAA_D2 = "ncaa_d2"  # Division II
    NCAA_D3 = "ncaa_d3"  # Division III
    NAIA = "naia"
    NJCAA = "njcaa"
    NONE = "none"


# ============================================================================
# Scoring Models
# ============================================================================


class AccountDimensionScore(BaseModel):
    """Score for a single university account dimension."""

    category: str = Field(description="Classification (e.g., 'R1', 'Large')")
    raw_score: int = Field(ge=0, le=10, description="Raw score 0-10")
    weighted_score: float = Field(ge=0.0, description="After applying weight")
    reason: str = Field(description="Human-readable explanation")


class AccountScoreBreakdown(BaseModel):
    """Complete score breakdown across all 5 dimensions."""

    carnegie_classification: AccountDimensionScore = Field(description="25% weight")
    enrollment_size: AccountDimensionScore = Field(description="25% weight")
    technology_signals: AccountDimensionScore = Field(description="20% weight")
    engagement_level: AccountDimensionScore = Field(description="15% weight")
    strategic_fit: AccountDimensionScore = Field(description="15% weight")


# ============================================================================
# University Account Models
# ============================================================================


class UniversityAccountCreate(BaseModel):
    """Input for creating/importing a university account."""

    name: str = Field(description="Institution name")
    domain: str | None = Field(default=None, description="Primary .edu domain")
    ipeds_unitid: str | None = Field(default=None, description="IPEDS UNITID (federal ID)")
    hubspot_company_id: str | None = Field(default=None, description="HubSpot company record ID")

    # Carnegie data
    carnegie_classification: CarnegieClassification | None = None
    institution_type: InstitutionType | None = None

    # Size
    enrollment: int | None = Field(default=None, description="Total student enrollment")
    faculty_count: int | None = None
    employee_count: int | None = None

    # Location
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None

    # Technology
    lms_platform: str | None = Field(default=None, description="Canvas, Blackboard, Moodle, etc.")
    video_platform: str | None = Field(default=None, description="Panopto, Kaltura, YuJa, etc.")
    av_system: str | None = Field(default=None, description="Crestron, Extron, QSC, etc.")
    tech_stack: list[str] = Field(default_factory=list, description="Known technologies")

    # Athletics (streaming needs proxy)
    athletic_division: AthleticDivision | None = None

    # Relationship
    is_existing_customer: bool = False
    has_active_opportunity: bool = False
    contact_count: int = 0
    decision_maker_count: int = 0


class UniversityAccount(BaseModel):
    """Full university account with scores."""

    id: str | None = None
    name: str
    domain: str | None = None
    ipeds_unitid: str | None = None
    hubspot_company_id: str | None = None

    # Carnegie data
    carnegie_classification: CarnegieClassification | None = None
    institution_type: InstitutionType | None = None

    # Size
    enrollment: int | None = None
    faculty_count: int | None = None
    employee_count: int | None = None

    # Location
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None

    # Technology
    lms_platform: str | None = None
    video_platform: str | None = None
    av_system: str | None = None
    tech_stack: list[str] = Field(default_factory=list)

    # Athletics
    athletic_division: AthleticDivision | None = None

    # Relationship
    is_existing_customer: bool = False
    has_active_opportunity: bool = False
    contact_count: int = 0
    decision_maker_count: int = 0

    # Scoring
    total_score: float = 0.0
    account_tier: AccountTier = AccountTier.D
    score_breakdown: AccountScoreBreakdown | None = None

    # Timestamps
    created_at: str | None = None
    updated_at: str | None = None
    scored_at: str | None = None


# ============================================================================
# API Request/Response Models
# ============================================================================


class UniversityAccountResponse(BaseModel):
    """Response for a single university account."""

    account: UniversityAccount
    next_action: str = Field(description="Recommended next step for this account")
    missing_data: list[str] = Field(
        default_factory=list, description="Data gaps that would improve scoring"
    )


class UniversityBatchImportRequest(BaseModel):
    """Batch import of university accounts (e.g., from Carnegie CSV)."""

    source: str = Field(default="carnegie_classification", description="Data source")
    accounts: list[UniversityAccountCreate] = Field(description="Accounts to import and score")


class UniversityBatchImportResult(BaseModel):
    """Result for a single account in a batch import."""

    name: str
    total_score: float
    account_tier: AccountTier
    error: str | None = None


class UniversityBatchImportResponse(BaseModel):
    """Response for batch import."""

    total: int
    scored: int
    failed: int
    tier_distribution: dict[str, int] = Field(
        default_factory=dict, description="Count per tier: A, B, C, D"
    )
    results: list[UniversityBatchImportResult]


class UniversityAccountListResponse(BaseModel):
    """Response for listing university accounts with filters."""

    accounts: list[UniversityAccount]
    total_count: int
    filters_applied: dict[str, str | int | None]


class UniversityGapAnalysis(BaseModel):
    """Gap analysis: which A/B accounts need contacts."""

    account_id: str
    name: str
    account_tier: AccountTier
    total_score: float
    contact_count: int
    decision_maker_count: int
    gap_type: str = Field(
        description="'no_contacts', 'no_decision_maker', or 'ready'"
    )
    recommended_action: str
