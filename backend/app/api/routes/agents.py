"""API routes for LangGraph agents.

Exposes agent functionality through REST endpoints:
- /api/agents/research - Lead research and enrichment
- /api/agents/scripts - Script selection and personalization
- /api/agents/competitors - Competitor intelligence
- /api/agents/emails - Email personalization
- /api/agents/emails/with-approval - Email with human-in-the-loop approval
- /api/agents/emails/approve/{thread_id} - Approve/reject pending email
- /api/agents/qualify - Lead qualification against ICP criteria
- /api/agents/qualify/stream - Streaming qualification progress

Rate limited at AGENT_RATE_LIMIT (10/min) because each call invokes LLM inference.
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.rate_limit import AGENT_RATE_LIMIT, limiter
from app.data.lead_schemas import Lead
from app.middleware.auth import require_auth
from app.services.langgraph.agents import (
    CompetitorIntelAgent,
    EmailPersonalizationAgent,
    LeadResearchAgent,
    QualificationAgent,
    ScriptSelectionAgent,
)
from app.services.langgraph.checkpointing import get_checkpointer
from app.services.langgraph.states import QualificationTier, ResearchBrief

router = APIRouter(prefix="/api/agents", tags=["agents"], dependencies=[Depends(require_auth)])

# Singleton agent instances
lead_research_agent = LeadResearchAgent()
script_selection_agent = ScriptSelectionAgent()
competitor_intel_agent = CompetitorIntelAgent()
email_personalization_agent = EmailPersonalizationAgent()
qualification_agent = QualificationAgent()


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
@limiter.limit(AGENT_RATE_LIMIT)
async def research_lead(request: Request, body: ResearchRequest) -> ResearchResponse:
    """
    Research a lead and generate intelligence brief.

    Uses Apollo and web scraping to gather information,
    then synthesizes into talking points and risk factors.
    """
    result = await lead_research_agent.run(
        lead=body.lead,
        research_depth=body.research_depth,
    )

    return ResearchResponse(
        research_brief=result.get("research_brief"),
        talking_points=result.get("talking_points", []),
        risk_factors=result.get("risk_factors", []),
    )


@router.post("/scripts", response_model=ScriptResponse)
@limiter.limit(AGENT_RATE_LIMIT)
async def select_script(request: Request, body: ScriptRequest) -> ScriptResponse:
    """
    Select and personalize a call script for a lead.

    Matches persona, selects appropriate warm/cold script,
    and personalizes based on lead context.
    """
    result = await script_selection_agent.run(
        lead=body.lead,
        persona_match=body.persona_match,
        trigger=body.trigger,
        call_type=body.call_type,
    )

    return ScriptResponse(
        personalized_script=result.get("personalized_script", ""),
        talking_points=result.get("talking_points", []),
        objection_responses=result.get("objection_responses", []),
    )


@router.post("/competitors", response_model=CompetitorResponse)
@limiter.limit(AGENT_RATE_LIMIT)
async def get_competitor_intel(request: Request, body: CompetitorRequest) -> CompetitorResponse:
    """
    Get competitor intelligence for a sales conversation.

    Looks up battlecard, matches relevant differentiators,
    and generates contextual response.
    """
    result = await competitor_intel_agent.run(
        competitor_name=body.competitor_name,
        context=body.context,
        query_type=body.query_type,
    )

    return CompetitorResponse(
        response=result.get("response", ""),
        proof_points=result.get("proof_points", []),
        follow_up_question=result.get("follow_up_question"),
    )


@router.post("/emails", response_model=EmailResponse)
@limiter.limit(AGENT_RATE_LIMIT)
async def personalize_email(request: Request, body: EmailRequest) -> EmailResponse:
    """
    Generate a personalized sales email.

    Uses research brief and persona data to create
    compelling, personalized outreach email.
    """
    # Convert dict to ResearchBrief if provided
    research_brief: ResearchBrief | None = None
    if body.research_brief:
        research_brief = {
            "company_overview": body.research_brief.get("company_overview", ""),
            "recent_news": body.research_brief.get("recent_news", []),
            "talking_points": body.research_brief.get("talking_points", []),
            "risk_factors": body.research_brief.get("risk_factors", []),
            "linkedin_summary": body.research_brief.get("linkedin_summary"),
        }

    result = await email_personalization_agent.run(
        lead=body.lead,
        research_brief=research_brief,
        persona=body.persona,
        email_type=body.email_type,
        sequence_step=body.sequence_step,
    )

    return EmailResponse(
        subject_line=result.get("subject_line", ""),
        email_body=result.get("email_body", ""),
        follow_up_note=result.get("follow_up_note"),
    )


# Qualification Models
class QualificationRequest(BaseModel):
    """Request for lead qualification."""

    lead: Lead
    enrichment_data: dict[str, Any] | None = Field(
        default=None,
        description="Pre-fetched enrichment data: {'apollo': {...}}",
    )
    skip_enrichment: bool = Field(
        default=False,
        description="If True, skip API enrichment and use provided data only",
    )


class DimensionScoreResponse(BaseModel):
    """Score breakdown for a single ICP dimension."""

    category: str
    raw_score: int
    weighted_score: float
    reason: str
    confidence: float


class ScoreBreakdownResponse(BaseModel):
    """Complete ICP score breakdown."""

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


class QualificationResponse(BaseModel):
    """Response from lead qualification."""

    total_score: float = Field(description="Weighted ICP score (0-100)")
    tier: QualificationTier = Field(description="Qualification tier")
    score_breakdown: ScoreBreakdownResponse
    confidence: float = Field(description="Overall confidence (0.0-1.0)")
    next_action: NextActionResponse
    missing_info: list[str] = Field(description="Data gaps identified")
    persona_match: str | None = Field(description="Matched persona if detected")


@router.post("/qualify", response_model=QualificationResponse)
@limiter.limit(AGENT_RATE_LIMIT)
async def qualify_lead(request: Request, body: QualificationRequest) -> QualificationResponse:
    """
    Qualify a lead against ICP criteria.

    Scores the lead across 5 weighted dimensions:
    - Company Size (25%)
    - Industry Vertical (20%)
    - Use Case Fit (25%)
    - Tech Stack Signals (15%)
    - Buying Authority (15%)

    Returns qualification tier and recommended next action.
    """
    result = await qualification_agent.run(
        lead=body.lead,
        enrichment_data=body.enrichment_data,
        skip_enrichment=body.skip_enrichment,
    )

    # Convert score breakdown
    breakdown = result.get("score_breakdown", {})
    score_breakdown = ScoreBreakdownResponse(
        company_size=DimensionScoreResponse(**breakdown.get("company_size", {})),
        industry_vertical=DimensionScoreResponse(
            **breakdown.get("industry_vertical", {})
        ),
        use_case_fit=DimensionScoreResponse(**breakdown.get("use_case_fit", {})),
        tech_stack_signals=DimensionScoreResponse(
            **breakdown.get("tech_stack_signals", {})
        ),
        buying_authority=DimensionScoreResponse(**breakdown.get("buying_authority", {})),
    )

    # Convert next action
    action = result.get("next_action", {})
    next_action = NextActionResponse(
        action_type=action.get("action_type", ""),
        description=action.get("description", ""),
        priority=action.get("priority", "low"),
        ae_involvement=action.get("ae_involvement", False),
        missing_info=action.get("missing_info", []),
    )

    return QualificationResponse(
        total_score=result.get("total_score", 0.0),
        tier=result.get("tier", QualificationTier.NOT_ICP),
        score_breakdown=score_breakdown,
        confidence=result.get("confidence", 0.0),
        next_action=next_action,
        missing_info=result.get("missing_info", []),
        persona_match=result.get("persona_match"),
    )


# =============================================================================
# Streaming Qualification Endpoint
# =============================================================================


@router.post("/qualify/stream")
@limiter.limit(AGENT_RATE_LIMIT)
async def qualify_lead_stream(request: Request, body: QualificationRequest) -> StreamingResponse:
    """
    Qualify lead with streaming progress updates.

    Returns Server-Sent Events (SSE) stream with progress from each
    qualification step: gather_data → score_dimensions → calculate_final → recommend_action

    Use this for real-time UI feedback during qualification.
    """
    async def event_stream() -> AsyncGenerator[str, None]:
        async for event in qualification_agent.stream(
            lead=body.lead,
            enrichment_data=body.enrichment_data,
            skip_enrichment=body.skip_enrichment,
        ):
            # Format as SSE
            yield f"data: {json.dumps(event)}\n\n"

        # Send completion event
        yield f"data: {json.dumps({'node': 'complete', 'updates': {}, 'timestamp': ''})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# =============================================================================
# Email Approval Workflow Endpoints
# =============================================================================


class EmailApprovalPending(BaseModel):
    """Response when email is pending approval."""

    thread_id: str = Field(description="Thread ID for approval workflow")
    email_preview: str = Field(description="Generated email body preview")
    subject_preview: str = Field(description="Generated subject line preview")
    lead_email: str | None = Field(description="Target lead email")
    lead_company: str | None = Field(description="Target lead company")
    status: str = Field(default="pending_approval")


class EmailApprovalInput(BaseModel):
    """Input for email approval decision."""

    approved: bool = Field(description="Whether to approve the email")
    feedback: str | None = Field(
        default=None,
        description="Optional feedback/reason for rejection",
    )


class EmailApprovalResponse(BaseModel):
    """Response from email approval."""

    thread_id: str
    approved: bool
    subject_line: str = ""
    email_body: str = ""
    follow_up_note: str | None = None
    rejection_reason: str | None = None


@router.post("/emails/with-approval", response_model=EmailApprovalPending)
@limiter.limit(AGENT_RATE_LIMIT)
async def generate_email_with_approval(request: Request, body: EmailRequest) -> EmailApprovalPending:
    """
    Generate email and pause for human approval.

    Creates a draft email using the personalization agent,
    then pauses execution for human review. Use the
    /emails/approve/{thread_id} endpoint to approve or reject.

    Workflow:
    1. Call this endpoint to generate draft
    2. Review email_preview and subject_preview
    3. Call /emails/approve/{thread_id} with decision
    """
    # Convert dict to ResearchBrief if provided
    research_brief: ResearchBrief | None = None
    if body.research_brief:
        research_brief = {
            "company_overview": body.research_brief.get("company_overview", ""),
            "recent_news": body.research_brief.get("recent_news", []),
            "talking_points": body.research_brief.get("talking_points", []),
            "risk_factors": body.research_brief.get("risk_factors", []),
            "linkedin_summary": body.research_brief.get("linkedin_summary"),
        }

    result = await email_personalization_agent.run_with_approval(
        lead=body.lead,
        research_brief=research_brief,
        persona=body.persona,
        email_type=body.email_type,
        sequence_step=body.sequence_step,
    )

    return EmailApprovalPending(
        thread_id=result["thread_id"],
        email_preview=result["email_preview"],
        subject_preview=result["subject_preview"],
        lead_email=result.get("lead_email"),
        lead_company=result.get("lead_company"),
        status=result["status"],
    )


@router.post("/emails/approve/{thread_id}", response_model=EmailApprovalResponse)
@limiter.limit(AGENT_RATE_LIMIT)
async def approve_email(request: Request, thread_id: str, approval: EmailApprovalInput) -> EmailApprovalResponse:
    """
    Approve or reject a pending email.

    Completes the human-in-the-loop workflow started by
    /emails/with-approval. If approved, finalizes the email.
    If rejected, returns the rejection reason.

    Args:
        thread_id: Thread ID from /emails/with-approval response
        approval: Approval decision and optional feedback
    """
    result = await email_personalization_agent.approve(
        thread_id=thread_id,
        approved=approval.approved,
        feedback=approval.feedback,
    )

    return EmailApprovalResponse(
        thread_id=result["thread_id"],
        approved=result["approved"],
        subject_line=result.get("subject_line", ""),
        email_body=result.get("email_body", ""),
        follow_up_note=result.get("follow_up_note"),
        rejection_reason=result.get("rejection_reason"),
    )


# =============================================================================
# Token-Level Streaming Endpoint
# =============================================================================


@router.post("/emails/stream")
@limiter.limit(AGENT_RATE_LIMIT)
async def stream_email_generation(request: Request, body: EmailRequest) -> StreamingResponse:
    """
    Stream email generation with token-level granularity.

    Returns Server-Sent Events (SSE) stream with fine-grained events:
    - token: Individual LLM tokens as the email is generated
    - chain_start/chain_end: Node execution events
    - custom: Developer-defined custom events

    This enables real-time UI with typing effect during email generation.

    Example usage:
        curl -N -X POST http://localhost:8001/api/agents/emails/stream \\
            -H "Content-Type: application/json" \\
            -d '{"lead": {"hubspot_id": "123", "email": "test@example.com"}}'
    """
    # Convert dict to ResearchBrief if provided
    research_brief: ResearchBrief | None = None
    if body.research_brief:
        research_brief = {
            "company_overview": body.research_brief.get("company_overview", ""),
            "recent_news": body.research_brief.get("recent_news", []),
            "talking_points": body.research_brief.get("talking_points", []),
            "risk_factors": body.research_brief.get("risk_factors", []),
            "linkedin_summary": body.research_brief.get("linkedin_summary"),
        }

    async def token_event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in email_personalization_agent.stream_tokens(
                lead=body.lead,
                research_brief=research_brief,
                persona=body.persona,
                email_type=body.email_type,
                sequence_step=body.sequence_step,
            ):
                yield f"data: {json.dumps(event)}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'event_type': 'complete'})}\n\n"

        except Exception as e:
            error_event = {"event_type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        token_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# =============================================================================
# Time-Travel Debugging Endpoint
# =============================================================================


@router.get("/debug/{thread_id}/history")
async def get_agent_history(thread_id: str) -> dict[str, Any]:
    """
    Get checkpoint history for debugging agent execution.

    This enables time-travel debugging by showing all state snapshots
    for a given thread, allowing developers to understand execution flow.

    Returns minimal data (checkpoint IDs and metadata) to avoid
    returning potentially large state objects.

    Args:
        thread_id: The thread ID to retrieve history for

    Returns:
        Dictionary with thread_id, list of checkpoints, and count
    """
    checkpointer = get_checkpointer()

    # Get state history from checkpointer
    config = {"configurable": {"thread_id": thread_id}}

    # Try to get history - return empty if thread doesn't exist
    try:
        history = []
        async for checkpoint in checkpointer.alist(config):
            history.append({
                "checkpoint_id": checkpoint.config.get("configurable", {}).get(
                    "checkpoint_id"
                ),
                "thread_id": thread_id,
                "metadata": checkpoint.metadata,
            })
        return {"thread_id": thread_id, "checkpoints": history, "count": len(history)}
    except Exception as e:
        return {"thread_id": thread_id, "checkpoints": [], "error": str(e)}
