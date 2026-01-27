"""API routes for BDR scripts - warm inbound and cold call."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.data.schemas import PersonaType, TriggerType, WarmCallScript
from app.data.scripts import get_warm_script_for_call

router = APIRouter()

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
