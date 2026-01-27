"""API routes for persona profiles."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.cache import with_cache_headers
from app.data.personas import PERSONAS, get_persona_by_id, get_personas_by_vertical
from app.data.schemas import PersonaProfile, Vertical

router = APIRouter()

# Type alias for optional vertical filter
VerticalFilter = Annotated[
    Vertical | None,
    Query(description="Filter personas by target vertical (optional)"),
]


@router.get(
    "",
    response_model=list[PersonaProfile],
    summary="List all personas",
    description="""
    Returns all buyer persona profiles used by the BDR team.

    **8 Personas:**
    - AV Director (higher_ed, corporate, government, live_events)
    - L&D Director (corporate, industrial)
    - Technical Director (house_of_worship, live_events, corporate)
    - Simulation Director (healthcare)
    - Court Administrator (government, legal)
    - Corp Comms Director (corporate)
    - EHS Manager (industrial)
    - Law Firm IT (legal)

    Optionally filter by vertical to see only relevant personas.
    """,
    responses={
        200: {"description": "List of persona profiles"},
        422: {"description": "Invalid vertical value"},
    },
)
async def list_personas(vertical: VerticalFilter = None) -> JSONResponse:
    """List all personas, optionally filtered by vertical."""
    personas = get_personas_by_vertical(vertical) if vertical is not None else list(PERSONAS)
    return with_cache_headers(personas)


@router.get(
    "/{persona_id}",
    response_model=PersonaProfile,
    summary="Get persona by ID",
    description="""
    Returns a single persona profile by its ID.

    **Valid IDs:**
    - av_director
    - ld_director
    - technical_director
    - simulation_director
    - court_administrator
    - corp_comms_director
    - ehs_manager
    - law_firm_it
    """,
    responses={
        200: {"description": "Persona profile"},
        404: {"description": "Persona not found"},
    },
)
async def get_persona(persona_id: str) -> JSONResponse:
    """Get a single persona by ID."""
    persona = get_persona_by_id(persona_id)

    if persona is None:
        raise HTTPException(
            status_code=404,
            detail=f"Persona '{persona_id}' not found",
        )

    return with_cache_headers(persona)
