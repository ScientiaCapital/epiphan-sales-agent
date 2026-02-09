"""API route for call brief generation.

POST /api/agents/call-brief - Generate a complete one-page call prep brief.

Composes research, qualification, and script agents in parallel,
then enriches with playbook data (persona, discovery, competitors, stories).
"""

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.rate_limit import AGENT_RATE_LIMIT, limiter
from app.data.lead_schemas import Lead
from app.middleware.auth import require_auth
from app.services.langgraph.agents.call_brief import (
    CallBriefAssembler,
    CallBriefRequest,
    CallBriefResponse,
)
from app.services.langgraph.tracing import trace_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"], dependencies=[Depends(require_auth)])

# Singleton assembler instance
_assembler = CallBriefAssembler()


def save_call_brief(brief: CallBriefResponse, lead_id: str) -> str | None:
    """Persist a call brief to the database. Returns the brief_id or None on failure."""
    try:
        from app.services.database.supabase_client import supabase_client

        record = supabase_client.save_call_brief({
            "lead_id": lead_id,
            "brief_json": brief.model_dump(mode="json"),
            "brief_quality": brief.brief_quality.value,
            "trigger": brief.trigger,
            "call_type": brief.call_type,
        })
        return str(record["id"]) if record and "id" in record else None
    except Exception:
        logger.warning("Failed to persist call brief", exc_info=True)
        return None


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
@limiter.limit(AGENT_RATE_LIMIT)
@trace_agent("call_brief", metadata={"version": "1.0"})
async def generate_call_brief(
    request: Request,
    body: CallBriefAPIRequest,
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
        lead=body.lead,
        trigger=body.trigger,
        call_type=body.call_type,
        research_depth=body.research_depth,
    )

    brief = await _assembler.assemble(brief_request)

    # Persist the brief for feedback loop (graceful degradation — don't fail the request)
    brief_id = save_call_brief(brief, lead_id=body.lead.hubspot_id or body.lead.email)
    if brief_id:
        brief.brief_id = brief_id

    elapsed_ms = (time.monotonic() - start_time) * 1000

    logger.info(
        "Call brief generated",
        extra={
            "lead_email": body.lead.email,
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
