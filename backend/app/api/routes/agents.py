"""API routes for LangGraph agents.

Exposes agent functionality through REST endpoints:
- /api/agents/research - Lead research and enrichment
- /api/agents/scripts - Script selection and personalization
- /api/agents/competitors - Competitor intelligence
- /api/agents/emails - Email personalization
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.data.lead_schemas import Lead
from app.services.langgraph.agents import (
    CompetitorIntelAgent,
    EmailPersonalizationAgent,
    LeadResearchAgent,
    ScriptSelectionAgent,
)
from app.services.langgraph.states import ResearchBrief

router = APIRouter(prefix="/api/agents", tags=["agents"])

# Singleton agent instances
lead_research_agent = LeadResearchAgent()
script_selection_agent = ScriptSelectionAgent()
competitor_intel_agent = CompetitorIntelAgent()
email_personalization_agent = EmailPersonalizationAgent()


# Request/Response Models
class ResearchRequest(BaseModel):
    """Request for lead research."""

    lead: Lead
    research_depth: str = Field(
        default="quick",
        description="Research depth: 'quick' (API only) or 'deep' (API + web)",
    )


class ResearchResponse(BaseModel):
    """Response from lead research."""

    research_brief: dict[str, Any] | None
    talking_points: list[str]
    risk_factors: list[str]


class ScriptRequest(BaseModel):
    """Request for script selection."""

    lead: Lead
    persona_match: str | None = None
    trigger: str | None = None
    call_type: str = Field(default="warm", description="'warm' or 'cold'")


class ScriptResponse(BaseModel):
    """Response from script selection."""

    personalized_script: str
    talking_points: list[str]
    objection_responses: list[dict[str, str]]


class CompetitorRequest(BaseModel):
    """Request for competitor intelligence."""

    competitor_name: str
    context: str
    query_type: str = Field(
        default="claim",
        description="Query type: 'claim', 'objection', or 'comparison'",
    )


class CompetitorResponse(BaseModel):
    """Response from competitor intelligence."""

    response: str
    proof_points: list[str]
    follow_up_question: str | None


class EmailRequest(BaseModel):
    """Request for email personalization."""

    lead: Lead
    research_brief: dict[str, Any] | None = None
    persona: dict[str, Any] | None = None
    email_type: str = Field(
        default="pattern_interrupt",
        description="Email type: pattern_interrupt, pain_point, breakup, nurture",
    )
    sequence_step: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Sequence step (1-4)",
    )


class EmailResponse(BaseModel):
    """Response from email personalization."""

    subject_line: str
    email_body: str
    follow_up_note: str | None


# Endpoints
@router.post("/research", response_model=ResearchResponse)
async def research_lead(request: ResearchRequest) -> ResearchResponse:
    """
    Research a lead and generate intelligence brief.

    Uses Apollo, Clearbit, and web scraping to gather information,
    then synthesizes into talking points and risk factors.
    """
    result = await lead_research_agent.run(
        lead=request.lead,
        research_depth=request.research_depth,
    )

    return ResearchResponse(
        research_brief=result.get("research_brief"),
        talking_points=result.get("talking_points", []),
        risk_factors=result.get("risk_factors", []),
    )


@router.post("/scripts", response_model=ScriptResponse)
async def select_script(request: ScriptRequest) -> ScriptResponse:
    """
    Select and personalize a call script for a lead.

    Matches persona, selects appropriate warm/cold script,
    and personalizes based on lead context.
    """
    result = await script_selection_agent.run(
        lead=request.lead,
        persona_match=request.persona_match,
        trigger=request.trigger,
        call_type=request.call_type,
    )

    return ScriptResponse(
        personalized_script=result.get("personalized_script", ""),
        talking_points=result.get("talking_points", []),
        objection_responses=result.get("objection_responses", []),
    )


@router.post("/competitors", response_model=CompetitorResponse)
async def get_competitor_intel(request: CompetitorRequest) -> CompetitorResponse:
    """
    Get competitor intelligence for a sales conversation.

    Looks up battlecard, matches relevant differentiators,
    and generates contextual response.
    """
    result = await competitor_intel_agent.run(
        competitor_name=request.competitor_name,
        context=request.context,
        query_type=request.query_type,
    )

    return CompetitorResponse(
        response=result.get("response", ""),
        proof_points=result.get("proof_points", []),
        follow_up_question=result.get("follow_up_question"),
    )


@router.post("/emails", response_model=EmailResponse)
async def personalize_email(request: EmailRequest) -> EmailResponse:
    """
    Generate a personalized sales email.

    Uses research brief and persona data to create
    compelling, personalized outreach email.
    """
    # Convert dict to ResearchBrief if provided
    research_brief: ResearchBrief | None = None
    if request.research_brief:
        research_brief = {
            "company_overview": request.research_brief.get("company_overview", ""),
            "recent_news": request.research_brief.get("recent_news", []),
            "talking_points": request.research_brief.get("talking_points", []),
            "risk_factors": request.research_brief.get("risk_factors", []),
            "linkedin_summary": request.research_brief.get("linkedin_summary"),
        }

    result = await email_personalization_agent.run(
        lead=request.lead,
        research_brief=research_brief,
        persona=request.persona,
        email_type=request.email_type,
        sequence_step=request.sequence_step,
    )

    return EmailResponse(
        subject_line=result.get("subject_line", ""),
        email_body=result.get("email_body", ""),
        follow_up_note=result.get("follow_up_note"),
    )
