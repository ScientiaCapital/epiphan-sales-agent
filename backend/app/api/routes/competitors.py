"""API routes for competitor battlecards."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.cache import with_cache_headers
from app.data.competitors import (
    COMPETITORS,
    get_active_competitors,
    get_competitor_by_id,
    get_competitors_by_vertical,
)
from app.data.schemas import CompetitorBattlecard, Vertical
from app.middleware.auth import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])

# Type aliases for query parameters
VerticalFilter = Annotated[
    Vertical | None,
    Query(description="Filter competitors by target vertical (optional)"),
]
IncludeInactiveParam = Annotated[
    bool,
    Query(description="Include discontinued/complementary competitors (default: false)"),
]


@router.get(
    "",
    response_model=list[CompetitorBattlecard],
    summary="List competitors",
    description="""
    Returns competitor battlecards for sales positioning.

    **By default, returns only active competitors.**

    Use `include_inactive=true` to also include:
    - Discontinued products (displacement opportunities, e.g., SlingStudio)
    - Complementary products (position as integration, e.g., Crestron)

    **Filtering by vertical** returns competitors targeting that market.

    **Top Competitors by Call Volume:**
    1. Blackmagic ATEM (507 mentions)
    2. Teradek (128 mentions)
    3. YoloBox (48 mentions)
    """,
    responses={
        200: {"description": "List of competitor battlecards"},
        422: {"description": "Invalid vertical value"},
    },
)
async def list_competitors(
    vertical: VerticalFilter = None,
    include_inactive: IncludeInactiveParam = False,
) -> JSONResponse:
    """List competitors, optionally filtered by vertical or including inactive."""
    if vertical is not None:
        # Vertical filter returns all statuses for that vertical
        competitors = get_competitors_by_vertical(vertical)
    elif include_inactive:
        # All competitors regardless of status
        competitors = list(COMPETITORS)
    else:
        # Default: active only
        competitors = get_active_competitors()

    return with_cache_headers(competitors)


@router.get(
    "/{competitor_id}",
    response_model=CompetitorBattlecard,
    summary="Get competitor by ID",
    description="""
    Returns a single competitor battlecard by its ID.

    **Top Competitor IDs:**
    - blackmagic_atem (Rank #1)
    - tricaster
    - vmix
    - teradek
    - yolobox
    - slingstudio (DISCONTINUED)
    - extron_smp
    - crestron (COMPLEMENTARY)
    - matrox
    - haivision
    - magewell
    - lumens
    - arec
    """,
    responses={
        200: {"description": "Competitor battlecard"},
        404: {"description": "Competitor not found"},
    },
)
async def get_competitor(competitor_id: str) -> JSONResponse:
    """Get a single competitor by ID."""
    competitor = get_competitor_by_id(competitor_id)

    if competitor is None:
        raise HTTPException(
            status_code=404,
            detail=f"Competitor '{competitor_id}' not found",
        )

    return with_cache_headers(competitor)
