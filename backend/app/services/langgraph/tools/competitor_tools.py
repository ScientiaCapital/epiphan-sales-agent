"""Tools for Competitor Intelligence Agent.

Provides functions to look up competitor battlecards, search
differentiators, and get pre-written claim responses.
"""

from typing import Any

from app.data.competitors import COMPETITORS, get_competitor_by_id


def get_battlecard(competitor_name: str) -> dict[str, Any] | None:
    """
    Get battlecard for a competitor by name.

    Searches by ID, name, and company name (case-insensitive).

    Args:
        competitor_name: Full or partial competitor name

    Returns:
        Battlecard dict or None if not found
    """
    name_lower = competitor_name.lower().strip()

    # Try exact ID match first
    for competitor in COMPETITORS:
        if competitor.id == name_lower or name_lower in competitor.id:
            return _battlecard_to_dict(competitor)

    # Try name match
    for competitor in COMPETITORS:
        if name_lower in competitor.name.lower():
            return _battlecard_to_dict(competitor)

    # Try company match
    for competitor in COMPETITORS:
        if name_lower in competitor.company.lower():
            return _battlecard_to_dict(competitor)

    return None


def search_differentiators(
    competitor_id: str,
    keyword: str,
) -> list[dict[str, str]]:
    """
    Search differentiators by keyword.

    Args:
        competitor_id: Competitor ID
        keyword: Keyword to search for

    Returns:
        List of matching differentiators
    """
    competitor = get_competitor_by_id(competitor_id)
    if not competitor:
        return []

    keyword_lower = keyword.lower()
    matches = []

    for diff in competitor.key_differentiators:
        searchable = f"{diff.feature} {diff.competitor_capability} {diff.pearl_capability} {diff.why_it_matters}".lower()
        if keyword_lower in searchable:
            matches.append(
                {
                    "feature": diff.feature,
                    "competitor": diff.competitor_capability,
                    "pearl": diff.pearl_capability,
                    "why_it_matters": diff.why_it_matters,
                }
            )

    return matches


def get_claim_responses(
    competitor_id: str,
    keyword: str | None = None,
) -> list[dict[str, str]]:
    """
    Get claim/response pairs for a competitor.

    Args:
        competitor_id: Competitor ID
        keyword: Optional keyword to filter claims

    Returns:
        List of claim/response dicts
    """
    competitor = get_competitor_by_id(competitor_id)
    if not competitor:
        return []

    responses = []
    for claim in competitor.claims:
        if keyword and keyword.lower() not in claim.claim.lower():
            continue
        responses.append(
            {
                "claim": claim.claim,
                "response": claim.response,
            }
        )

    return responses


def _battlecard_to_dict(competitor: Any) -> dict[str, Any]:
    """Convert CompetitorBattlecard to dict."""
    return {
        "id": competitor.id,
        "name": competitor.name,
        "company": competitor.company,
        "price_range": competitor.price_range,
        "positioning": competitor.positioning,
        "market_context": competitor.market_context,
        "when_to_compete": competitor.when_to_compete,
        "when_to_walk_away": competitor.when_to_walk_away,
        "key_differentiators": [
            {
                "feature": d.feature,
                "competitor": d.competitor_capability,
                "pearl": d.pearl_capability,
                "why_it_matters": d.why_it_matters,
            }
            for d in competitor.key_differentiators
        ],
        "claims": [
            {"claim": c.claim, "response": c.response} for c in competitor.claims
        ],
        "talk_tracks": (
            [{"scenario": t.opening, "track": t.closing} for t in [competitor.talk_track]]
            if competitor.talk_track
            else []
        ),
        "proof_points": competitor.proof_points or [],
    }
