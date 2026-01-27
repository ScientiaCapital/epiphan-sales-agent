"""Batch processing API route.

Provides endpoint for processing multiple leads through the
full agent pipeline: Research → Script Selection → Email Generation.
"""

import asyncio
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.data.lead_schemas import Lead
from app.services.langgraph.agents import (
    EmailPersonalizationAgent,
    LeadResearchAgent,
    ScriptSelectionAgent,
)

router = APIRouter(prefix="/api/batch", tags=["batch"])

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
async def batch_process_leads(request: BatchRequest) -> BatchResponse:
    """
    Process multiple leads through the full agent pipeline.

    Runs leads concurrently (up to concurrency limit) through:
    1. Lead Research - Gather intelligence
    2. Script Selection - Personalize call script
    3. Email Generation - Create outreach email

    Returns results for all leads plus summary statistics.
    """
    semaphore = asyncio.Semaphore(request.concurrency)

    async def process_with_limit(lead: Lead) -> LeadResult:
        async with semaphore:
            return await process_single_lead(
                lead=lead,
                persona_match=request.persona_match,
                trigger=request.trigger,
                email_type=request.email_type,
                sequence_step=request.sequence_step,
            )

    # Process all leads concurrently
    tasks = [process_with_limit(lead) for lead in request.leads]
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
