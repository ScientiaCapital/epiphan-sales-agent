"""Batch processing API route.

Provides endpoint for processing multiple leads through the
full agent pipeline: Research → Script Selection → Email Generation.
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.rate_limit import AGENT_RATE_LIMIT, limiter
from app.data.lead_schemas import Lead
from app.middleware.auth import require_auth
from app.services.langgraph.agents import (
    EmailPersonalizationAgent,
    LeadResearchAgent,
    ScriptSelectionAgent,
)

router = APIRouter(prefix="/api/batch", tags=["batch"], dependencies=[Depends(require_auth)])

# Singleton agent instances
lead_research_agent = LeadResearchAgent()
script_selection_agent = ScriptSelectionAgent()
email_personalization_agent = EmailPersonalizationAgent()


class BatchRequest(BaseModel):
    """Request for batch lead processing."""

    leads: list[Lead]
    persona_match: str | None = None
    trigger: str | None = None
    email_type: str = Field(
        default="pattern_interrupt",
        description="Email type to generate",
    )
    sequence_step: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Email sequence step",
    )
    concurrency: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Max concurrent lead processing",
    )


class LeadResult(BaseModel):
    """Result for a single lead."""

    hubspot_id: str
    lead_email: str
    research_brief: dict[str, Any] | None = None
    script: dict[str, Any] | None = None
    generated_email: dict[str, Any] | None = None
    error: str | None = None


class BatchSummary(BaseModel):
    """Summary of batch processing results."""

    total: int
    successful: int
    failed: int


class BatchResponse(BaseModel):
    """Response from batch processing."""

    results: list[LeadResult]
    summary: BatchSummary


async def process_single_lead(
    lead: Lead,
    persona_match: str | None,
    trigger: str | None,
    email_type: str,
    sequence_step: int,
) -> LeadResult:
    """
    Process a single lead through the full pipeline.

    Args:
        lead: Lead to process
        persona_match: Optional persona ID
        trigger: Optional trigger type
        email_type: Email type to generate
        sequence_step: Sequence step (1-4)

    Returns:
        LeadResult with all outputs or error
    """
    result = LeadResult(
        hubspot_id=lead.hubspot_id,
        lead_email=lead.email,
    )

    try:
        # Step 1: Research
        research = await lead_research_agent.run(
            lead=lead,
            research_depth="quick",
        )
        result.research_brief = research.get("research_brief")

        # Step 2: Script Selection
        script = await script_selection_agent.run(
            lead=lead,
            persona_match=persona_match,
            trigger=trigger,
            call_type="warm" if trigger else "cold",
        )
        result.script = {
            "personalized_script": script.get("personalized_script", ""),
            "talking_points": script.get("talking_points", []),
        }

        # Step 3: Email Generation
        email_result = await email_personalization_agent.run(
            lead=lead,
            research_brief=result.research_brief,
            persona={"id": persona_match} if persona_match else None,
            email_type=email_type,
            sequence_step=sequence_step,
        )
        result.generated_email = {
            "subject_line": email_result.get("subject_line", ""),
            "email_body": email_result.get("email_body", ""),
        }

    except Exception as e:
        result.error = str(e)

    return result


@router.post("/process", response_model=BatchResponse)
@limiter.limit(AGENT_RATE_LIMIT)
async def batch_process_leads(request: Request, body: BatchRequest) -> BatchResponse:
    """
    Process multiple leads through the full agent pipeline.

    Runs leads concurrently (up to concurrency limit) through:
    1. Lead Research - Gather intelligence
    2. Script Selection - Personalize call script
    3. Email Generation - Create outreach email

    Returns results for all leads plus summary statistics.
    """
    semaphore = asyncio.Semaphore(body.concurrency)

    async def process_with_limit(lead: Lead) -> LeadResult:
        async with semaphore:
            return await process_single_lead(
                lead=lead,
                persona_match=body.persona_match,
                trigger=body.trigger,
                email_type=body.email_type,
                sequence_step=body.sequence_step,
            )

    # Process all leads concurrently
    tasks = [process_with_limit(lead) for lead in body.leads]
    results = await asyncio.gather(*tasks)

    # Calculate summary
    successful = sum(1 for r in results if r.error is None)
    failed = len(results) - successful

    return BatchResponse(
        results=list(results),
        summary=BatchSummary(
            total=len(results),
            successful=successful,
            failed=failed,
        ),
    )


class StreamingBatchRequest(BaseModel):
    """Request for streaming batch processing with orchestrator."""

    leads: list[Lead]
    concurrency: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Max concurrent lead processing",
    )
    skip_outreach: bool = Field(
        default=False,
        description="Skip outreach phase (research/qualify only)",
    )


class StreamEvent(BaseModel):
    """SSE event for streaming batch progress."""

    event_type: str  # "progress" | "result" | "error" | "complete"
    lead_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


@router.post("/process/stream")
@limiter.limit(AGENT_RATE_LIMIT)
async def batch_process_stream(request: Request, body: StreamingBatchRequest) -> StreamingResponse:
    """
    Process leads in parallel with real-time SSE progress streaming.

    Uses the Master Orchestrator Agent for full pipeline processing.
    Streams results as they complete for immediate feedback.

    Events:
    - progress: Lead processing started
    - result: Lead processing completed with full result
    - error: Lead processing failed
    - complete: All leads processed with summary

    Example usage:
        curl -N -X POST http://localhost:8001/api/batch/process/stream \\
            -H "Content-Type: application/json" \\
            -d '{"leads": [{"hubspot_id": "123", "email": "test@example.com"}]}'
    """
    from collections.abc import AsyncGenerator
    from json import dumps

    from fastapi.responses import StreamingResponse

    from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent

    async def event_generator() -> AsyncGenerator[str, None]:
        semaphore = asyncio.Semaphore(body.concurrency)
        orchestrator = MasterOrchestratorAgent()
        completed = 0
        failed = 0
        total = len(body.leads)

        async def process_lead(lead: Lead) -> tuple[str, dict[str, Any] | None, str | None]:
            """Process a single lead and return (hubspot_id, result, error)."""
            async with semaphore:
                try:
                    result = await orchestrator.run(
                        lead=lead,
                        process_config={"skip_outreach": body.skip_outreach},
                    )
                    return (lead.hubspot_id, result, None)
                except Exception as e:
                    return (lead.hubspot_id, None, str(e))

        # Create all tasks
        tasks = [process_lead(lead) for lead in body.leads]

        # Stream progress events for all leads starting
        for lead in body.leads:
            progress_event = StreamEvent(
                event_type="progress",
                lead_id=lead.hubspot_id,
                data={"status": "queued", "email": lead.email},
            )
            yield f"data: {dumps(progress_event.model_dump())}\n\n"

        # Process and stream results as they complete
        for coro in asyncio.as_completed(tasks):
            hubspot_id, result, error = await coro

            if error:
                failed += 1
                error_event = StreamEvent(
                    event_type="error",
                    lead_id=hubspot_id,
                    data={"error": error},
                )
                yield f"data: {dumps(error_event.model_dump())}\n\n"
            else:
                completed += 1
                result_event = StreamEvent(
                    event_type="result",
                    lead_id=hubspot_id,
                    data={
                        "tier": result.get("tier") if result else None,
                        "is_atl": result.get("is_atl") if result else None,
                        "has_phone": result.get("has_phone") if result else None,
                        "has_script": bool(result.get("script_result")) if result else False,
                        "has_email": bool(result.get("email_result")) if result else False,
                        "duration_ms": result.get("total_duration_ms") if result else None,
                        "errors": result.get("errors", []) if result else [],
                    },
                )
                yield f"data: {dumps(result_event.model_dump())}\n\n"

        # Send completion event
        complete_event = StreamEvent(
            event_type="complete",
            data={
                "total": total,
                "completed": completed,
                "failed": failed,
                "success_rate": (completed / total * 100) if total > 0 else 0,
            },
        )
        yield f"data: {dumps(complete_event.model_dump())}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


class TokenStreamRequest(BaseModel):
    """Request for token-level streaming single lead processing."""

    lead: Lead
    skip_outreach: bool = Field(
        default=False,
        description="Skip outreach phase (research/qualify only)",
    )


@router.post("/process/stream/tokens")
@limiter.limit(AGENT_RATE_LIMIT)
async def process_lead_stream_tokens(request: Request, body: TokenStreamRequest) -> StreamingResponse:
    """
    Process a single lead with token-level streaming.

    Uses astream_events(version="v2") for fine-grained events including:
    - token: Individual LLM tokens as they're generated
    - chain_start/chain_end: Node/chain execution events
    - tool_start/tool_end: Tool execution events
    - custom: Developer-defined custom events

    This enables real-time UI feedback with typing indicators and
    progress animations during LLM generation.

    Example usage:
        curl -N -X POST http://localhost:8001/api/batch/process/stream/tokens \\
            -H "Content-Type: application/json" \\
            -d '{"lead": {"hubspot_id": "123", "email": "test@example.com"}}'
    """
    from collections.abc import AsyncGenerator
    from json import dumps

    from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent

    async def token_event_generator() -> AsyncGenerator[str, None]:
        orchestrator = MasterOrchestratorAgent()

        try:
            async for event in orchestrator.stream_tokens(
                lead=body.lead,
                process_config={"skip_outreach": body.skip_outreach},
            ):
                yield f"data: {dumps(event)}\n\n"

            # Send completion event
            yield f"data: {dumps({'event_type': 'complete'})}\n\n"

        except Exception as e:
            error_event = {"event_type": "error", "error": str(e)}
            yield f"data: {dumps(error_event)}\n\n"

    return StreamingResponse(
        token_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
