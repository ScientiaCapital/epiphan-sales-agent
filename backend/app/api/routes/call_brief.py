"""API route for call brief generation.

POST /api/agents/call-brief - Generate a complete one-page call prep brief.

Composes research, qualification, and script agents in parallel,
then enriches with playbook data (persona, discovery, competitors, stories).
"""

import logging
import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.data.lead_schemas import Lead
from app.services.langgraph.agents.call_brief import (
    CallBriefAssembler,
    CallBriefRequest,
    CallBriefResponse,
)
from app.services.langgraph.tracing import trace_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])

# Singleton assembler instance
_assembler = CallBriefAssembler()


class CallBriefAPIRequest(BaseModel):
    """API request for call brief generation."""

    lead: Lead
    trigger: str | None = Field(
        default=None,
        description="Trigger type: content_download, demo_request, pricing_page, etc.",
    )
    call_type: str = Field(default="warm", description="'warm' or 'cold'")
    research_depth: str = Field(
        default="quick",
        description="'quick' (API only, ~2s) or 'deep' (API + web, ~5s)",
    )


class CallBriefAPIResponse(BaseModel):
    """API response wrapper for call brief."""

    success: bool = True
    brief: CallBriefResponse
    processing_time_ms: float = 0.0


@router.post("/call-brief", response_model=CallBriefAPIResponse)
@trace_agent("call_brief", metadata={"version": "1.0"})
async def generate_call_brief(
    request: CallBriefAPIRequest,
) -> dict[str, Any]:
    """Generate a complete one-page call prep brief.

    Runs research, qualification, and script agents in parallel (~3-5s),
    then enriches with playbook data (objections, discovery questions,
    competitor intel, reference stories).

    This replaces 3 separate API calls + manual combination:
    - POST /api/agents/research
    - POST /api/agents/qualify
    - POST /api/agents/scripts

    Saves Tim 5-10 minutes per lead × 20 calls/day = 100-200 min/day.

    Returns:
        Complete call brief with all sections needed for call prep.
    """
    start_time = time.monotonic()

    brief_request = CallBriefRequest(
        lead=request.lead,
        trigger=request.trigger,
        call_type=request.call_type,
        research_depth=request.research_depth,
    )

    brief = await _assembler.assemble(brief_request)

    elapsed_ms = (time.monotonic() - start_time) * 1000

    logger.info(
        "Call brief generated",
        extra={
            "lead_email": request.lead.email,
            "brief_quality": brief.brief_quality.value,
            "has_phone": brief.contact.phones.has_phone,
            "tier": brief.qualification.tier,
            "processing_time_ms": round(elapsed_ms, 1),
            "gaps_count": len(brief.intelligence_gaps),
        },
    )

    return {
        "success": True,
        "brief": brief,
        "processing_time_ms": round(elapsed_ms, 1),
    }
