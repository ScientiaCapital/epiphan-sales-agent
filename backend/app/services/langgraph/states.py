"""LangGraph state schemas for all agents.

State schemas use TypedDict to define the structure of state
that flows through each agent's graph nodes.
"""

from typing import Any, TypedDict

from app.data.lead_schemas import Lead


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

    Flow: enrich_apis (parallel) → scrape_web → synthesize → format_brief
    """

    # Inputs
    lead: Lead
    research_depth: str  # "quick" | "deep"

    # Tool outputs
    apollo_data: dict[str, Any] | None
    clearbit_data: dict[str, Any] | None
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
