"""API routes for BDR scripts - warm inbound and cold call."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.cache import with_cache_headers
from app.data.schemas import ColdCallScript, PersonaType, TriggerType, Vertical, WarmCallScript
from app.data.scripts import get_script_by_vertical, get_warm_script_for_call
from app.middleware.auth import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])

# Type aliases for query parameters with metadata
TriggerTypeParam = Annotated[
    TriggerType,
    Query(description="The action that triggered the inbound lead"),
]
PersonaTypeParam = Annotated[
    PersonaType | None,
    Query(description="The buyer persona type (optional - enables persona-specific script)"),
]


@router.get(
    "/warm",
    response_model=WarmCallScript,
    summary="Get warm inbound call script",
    description="""
    Returns a warm inbound call script based on the trigger action and optionally
    the buyer persona.

    **ACQP Framework:**
    - **Acknowledge**: Reference their action with persona context
    - **Connect**: Bridge to persona-specific pain point
    - **Qualify**: Understand scope, timeline, and decision process
    - **Propose**: Offer tailored next step with reference story

    **Trigger Types:**
    - `content_download`: Downloaded whitepaper, case study, datasheet
    - `webinar_attended`: Registered/attended a webinar
    - `demo_request`: Submitted demo request (HIGHEST INTENT)
    - `pricing_page`: Visited pricing page
    - `contact_form`: Submitted general inquiry
    - `trade_show`: Met at trade show
    - `referral`: Referred by customer/partner
    - `return_visitor`: Returning after previous engagement

    **Personas:**
    When persona is provided, returns persona-specific script with tailored
    messaging, discovery questions, and listening cues. Without persona,
    falls back to generic trigger-based script.
    """,
    responses={
        200: {
            "description": "Warm call script returned successfully",
        },
        404: {"description": "No script found for trigger/persona combination"},
        422: {"description": "Invalid trigger_type or persona_type value"},
    },
)
async def get_warm_script(
    trigger_type: TriggerTypeParam,
    persona_type: PersonaTypeParam = None,
) -> WarmCallScript:
    """Get warm inbound call script for BDR team."""
    script = get_warm_script_for_call(
        trigger_type=trigger_type,
        persona_type=persona_type,
    )

    if script is None:
        raise HTTPException(
            status_code=404,
            detail=f"No warm script found for trigger_type={trigger_type.value}"
            + (f", persona_type={persona_type.value}" if persona_type else ""),
        )

    return script


# Type alias for vertical query parameter
VerticalParam = Annotated[
    Vertical,
    Query(description="Target vertical market for cold call script"),
]


@router.get(
    "/cold",
    response_model=ColdCallScript,
    summary="Get cold call script by vertical",
    description="""
    Returns a cold call script tailored to the specified vertical market.

    **Script Structure:**
    - **Pattern Interrupt**: Opening to get attention (not the standard "how are you")
    - **Value Hook**: Reference customer + outcome (social proof)
    - **Pain Question**: Uncover their specific pain point
    - **Permission**: Ask for time to explain
    - **Pivot**: Handle initial brush-off

    **Available Verticals:**
    - `higher_ed`: Lecture capture, classroom technology
    - `corporate`: Training, executive communications
    - `healthcare`: Simulation centers, HIPAA compliance
    - `house_of_worship`: Volunteer-friendly, reliability
    - `government`: Courts, Open Meeting Law
    - `live_events`: Production, broadcast quality
    - `industrial`: EHS training, knowledge transfer
    """,
    responses={
        200: {"description": "Cold call script returned successfully"},
        404: {"description": "No script found for this vertical"},
        422: {"description": "Invalid vertical value"},
    },
)
async def get_cold_script(vertical: VerticalParam) -> JSONResponse:
    """Get cold call script for BDR team by target vertical."""
    script = get_script_by_vertical(vertical)

    if script is None:
        raise HTTPException(
            status_code=404,
            detail=f"No cold call script found for vertical={vertical.value}",
        )

    return with_cache_headers(script)
