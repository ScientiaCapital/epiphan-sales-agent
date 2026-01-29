"""LangGraph state schemas for all agents.

State schemas use TypedDict to define the structure of state
that flows through each agent's graph nodes.
"""

from enum import Enum
from typing import Any, TypedDict

from app.data.lead_schemas import Lead


class QualificationTier(str, Enum):
    """ICP qualification tier based on weighted score.

    Tier thresholds (0-100 weighted scale):
    - Tier 1 (70+): Priority sequence, AE involvement early
    - Tier 2 (50-69): Standard sequence
    - Tier 3 (30-49): Light touch, marketing nurture
    - Not ICP (<30): Disqualify
    """

    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    NOT_ICP = "not_icp"


class DimensionScore(TypedDict):
    """Score breakdown for a single ICP dimension."""

    category: str  # Classification category (e.g., "Enterprise", "Higher Ed")
    raw_score: int  # 0-10 score
    weighted_score: float  # After applying weight
    reason: str  # Explanation for the score
    confidence: float  # 0.0-1.0 confidence in classification


class ICPScoreBreakdown(TypedDict):
    """Complete breakdown of ICP scoring across all 5 dimensions."""

    company_size: DimensionScore  # Weight: 25%
    industry_vertical: DimensionScore  # Weight: 20%
    use_case_fit: DimensionScore  # Weight: 25%
    tech_stack_signals: DimensionScore  # Weight: 15%
    buying_authority: DimensionScore  # Weight: 15%


class NextAction(TypedDict):
    """Recommended next action based on qualification tier."""

    action_type: str  # "priority_sequence", "standard_sequence", "nurture", "disqualify"
    description: str  # Human-readable action description
    priority: str  # "high", "medium", "low"
    ae_involvement: bool  # Whether to involve AE early
    missing_info: list[str]  # Information gaps to fill


class CompetitorIntelState(TypedDict):
    """State for Competitor Intelligence Agent.

    Flow: lookup_battlecard → match_context → generate_response
    """

    # Inputs
    competitor_name: str
    context: str
    query_type: str  # "claim" | "objection" | "comparison"

    # Intermediate
    battlecard: dict[str, Any] | None
    relevant_differentiators: list[dict[str, str]]

    # Output
    response: str
    proof_points: list[str]
    follow_up_question: str | None


class ScriptSelectionState(TypedDict):
    """State for Script Selection Agent.

    Flow: load_script → extract_context → personalize
    """

    # Inputs
    lead: Lead
    persona_match: str | None
    trigger: str | None
    call_type: str  # "warm" | "cold"

    # Intermediate
    base_script: dict[str, Any] | None
    lead_context: str | None
    persona_profile: dict[str, Any] | None

    # Output
    personalized_script: str
    talking_points: list[str]
    objection_responses: list[dict[str, str]]


class ResearchBrief(TypedDict):
    """Synthesized research output from Lead Research Agent."""

    company_overview: str
    recent_news: list[dict[str, Any]]
    talking_points: list[str]
    risk_factors: list[str]
    linkedin_summary: str | None


class LeadResearchState(TypedDict):
    """State for Lead Research Agent.

    Flow: enrich_apis → scrape_web → synthesize → format_brief
    """

    # Inputs
    lead: Lead
    research_depth: str  # "quick" | "deep"

    # Tool outputs
    apollo_data: dict[str, Any] | None
    news_articles: list[dict[str, Any]]
    linkedin_context: str | None

    # Output
    research_brief: ResearchBrief | None
    talking_points: list[str]
    risk_factors: list[str]


class EmailPersonalizationState(TypedDict):
    """State for Email Personalization Agent.

    Flow: gather_context → select_template → personalize → generate_subject
    """

    # Inputs
    lead: Lead
    research_brief: ResearchBrief | None
    persona: dict[str, Any] | None
    sequence_step: int  # 1-4
    email_type: str  # pattern_interrupt, pain_point, breakup, nurture

    # Intermediate
    pain_points: list[str]
    personalization_hooks: list[str]

    # Output
    subject_line: str
    email_body: str
    follow_up_note: str | None


class QualificationState(TypedDict):
    """State for Qualification Agent.

    Flow: gather_data → score_dimensions → calculate_final → recommend_action

    Scores leads against Tim's 5-dimension weighted ICP criteria:
    - Company Size (25%)
    - Industry Vertical (20%)
    - Use Case Fit (25%)
    - Tech Stack Signals (15%)
    - Buying Authority (15%)
    """

    # Inputs
    lead: Lead
    skip_enrichment: bool  # If True, use provided enrichment_data only

    # Enrichment data (from research agent or provided)
    apollo_data: dict[str, Any] | None
    persona_match: str | None

    # Inference results (when data is missing)
    inferred_company_size: int | None  # Employee count estimate
    inferred_vertical: str | None
    inferred_use_case: str | None

    # Scoring outputs
    score_breakdown: ICPScoreBreakdown | None
    total_score: float  # 0-100 weighted score
    tier: QualificationTier | None
    confidence: float  # 0.0-1.0 overall confidence

    # Action recommendation
    next_action: NextAction | None
    missing_info: list[str]  # Information gaps identified
