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


# =============================================================================
# Master Orchestrator State
# =============================================================================


class GateDecision(TypedDict):
    """Decision from a review gate checkpoint."""

    proceed: bool  # Whether to proceed to next phase
    gate_name: str  # Name of the gate that made the decision
    passed_checks: list[str]  # Checks that passed
    failed_checks: list[str]  # Checks that failed
    remediation: str | None  # Suggested remediation if failed
    next_phase: str | None  # Next phase to proceed to if passed


class PhaseResult(TypedDict):
    """Result from a single orchestrator phase."""

    phase_name: str
    status: str  # "success" | "partial" | "failed"
    duration_ms: float
    errors: list[str]
    data: dict[str, Any]


class SynthesisResult(TypedDict):
    """Result from synthesis node after research phase.

    The synthesis node analyzes research findings and identifies:
    - Intelligence gaps that need filling
    - Contact quality assessment
    - Confidence in collected data
    """

    company_summary: str | None  # Condensed company overview
    qualification_tier: str | None  # Extracted tier
    contact_quality: str  # "high" | "medium" | "low"
    intelligence_gaps: list[str]  # Missing information
    confidence_score: float  # 0.0-1.0 overall confidence
    recommended_actions: list[str]  # Next steps based on gaps


class OrchestratorState(TypedDict):
    """State for Master Orchestrator Agent.

    The orchestrator coordinates all sub-agents through phases:
    1. Parallel Research Phase: research, qualification, enrichment (concurrent)
    2. Review Gate 1: Validate data completeness
    3. Parallel Outreach Phase: script, email, competitor intel (concurrent)
    4. Review Gate 2: Final quality check
    5. Sync Phase: Push to HubSpot

    Flow:
        parallel_research → review_gate_1 → parallel_outreach → review_gate_2 → sync

    Architecture based on:
    - Anthropic's two-agent system pattern
    - DeepAgents task delegation model
    - Claude 4 parallel tool execution best practices
    """

    # === Input ===
    lead: Lead
    process_config: dict[str, Any]  # Processing options

    # === Phase 1: Parallel Research Results ===
    research_brief: ResearchBrief | None
    qualification_result: dict[str, Any] | None  # ICP scoring result
    enrichment_data: dict[str, Any] | None  # Apollo + scraped data

    # === Synthesis Result (after research, before gate 1) ===
    synthesis: SynthesisResult | None

    # === Gate 1 Decision ===
    gate_1_decision: GateDecision | None

    # === Phase 2: Parallel Outreach Results ===
    script_result: dict[str, Any] | None  # Personalized call script
    email_result: dict[str, Any] | None  # Generated email
    competitor_intel: dict[str, Any] | None  # Battlecard responses

    # === Gate 2 Decision ===
    gate_2_decision: GateDecision | None

    # === Sync Phase Results ===
    hubspot_sync_result: dict[str, Any] | None

    # === Execution Tracking ===
    current_phase: str  # "research" | "gate_1" | "outreach" | "gate_2" | "sync" | "complete"
    phase_results: list[PhaseResult]
    total_duration_ms: float
    errors: list[str]

    # === Derived Fields ===
    tier: QualificationTier | None  # Extracted from qualification_result
    has_phone: bool  # Whether phone was enriched (CRITICAL for sales)
    is_atl: bool  # Above-the-line decision maker


class OrchestratorInput(TypedDict):
    """Input schema for Master Orchestrator Agent.

    This defines the minimal required inputs to start orchestration.
    Callers only need to provide these fields - all intermediate
    and output fields will be populated during execution.

    Fields:
        lead: The lead to process through the orchestration pipeline.
        process_config: Processing options that control which phases run.
            Common options:
            - skip_enrichment: bool - Skip Apollo enrichment
            - skip_hubspot_sync: bool - Skip HubSpot sync at end
            - skip_email: bool - Skip email generation
            - skip_script: bool - Skip script selection
    """

    lead: Lead
    process_config: dict[str, Any]


class OrchestratorOutput(TypedDict):
    """Output schema for Master Orchestrator Agent.

    This defines the fields returned to callers after orchestration
    completes. It excludes intermediate state fields that are only
    used internally during processing.

    Key outputs:
        tier: The qualification tier (Tier 1/2/3 or Not ICP)
        has_phone: Whether phone enrichment succeeded (CRITICAL for sales)
        qualification_score: The weighted ICP score (0-100)
        research_brief: Summary of research findings
        script_result: Personalized call script (if generated)
        email_result: Personalized email draft (if generated)
        hubspot_sync_result: HubSpot sync status (if synced)
        errors: List of any errors encountered during processing
    """

    tier: QualificationTier | None
    has_phone: bool
    qualification_score: float | None
    research_brief: ResearchBrief | None
    script_result: dict[str, Any] | None
    email_result: dict[str, Any] | None
    hubspot_sync_result: dict[str, Any] | None
    errors: list[str]
