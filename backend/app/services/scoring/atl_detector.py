"""Above-the-Line (ATL) Decision-Maker Detector.

Identifies ATL decision-makers from Tim's BDR Playbook personas who are
worth the 8-credit phone enrichment investment.

The matchmaker strategy:
- Fast company verification → Confirm ICP match
- Fast ATL identification → Know who to call
- Fast phone enrichment (for ATLs only) → Make the call before competitors

PHONES ARE GOLD - but only for people Tim will actually call.
Students and interns don't get dialed - save those credits for decision-makers.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum


class PersonaId(str, Enum):
    """The 8 ATL personas from the BDR Playbook."""

    AV_DIRECTOR = "av_director"
    LD_DIRECTOR = "ld_director"
    TECHNICAL_DIRECTOR = "technical_director"
    SIMULATION_DIRECTOR = "simulation_director"
    COURT_ADMINISTRATOR = "court_administrator"
    CORP_COMMS_DIRECTOR = "corp_comms_director"
    EHS_MANAGER = "ehs_manager"
    LAW_FIRM_IT = "law_firm_it"


# Title variations for each ATL persona (from BDR Playbook)
# These are the people Tim wants to call - they have budget authority
ATL_PERSONA_TITLES: dict[PersonaId, list[str]] = {
    PersonaId.AV_DIRECTOR: [
        "av director",
        "director of av services",
        "classroom technology manager",
        "director of learning spaces",
        "av manager",
    ],
    PersonaId.LD_DIRECTOR: [
        "l&d director",
        "vp of talent development",
        "chief learning officer",
        "director of learning & development",
        "director of learning and development",
        "training director",
    ],
    PersonaId.TECHNICAL_DIRECTOR: [
        "technical director",
        "production director",
        "media director",
        "broadcast engineer",
    ],
    PersonaId.SIMULATION_DIRECTOR: [
        "simulation center director",
        "director of simulation",
        "simulation center manager",
        "director of clinical simulation",
    ],
    PersonaId.COURT_ADMINISTRATOR: [
        "court administrator",
        "court executive officer",
        "clerk of court",
        "trial court administrator",
        "director of court operations",
    ],
    PersonaId.CORP_COMMS_DIRECTOR: [
        "corp comms director",
        "vp of corporate communications",
        "head of internal communications",
        "director of executive communications",
        "vp of internal comms",
    ],
    PersonaId.EHS_MANAGER: [
        "ehs manager",
        "ehs director",
        "safety manager",
        "director of safety",
        "plant safety manager",
        "vp of ehs",
    ],
    PersonaId.LAW_FIRM_IT: [
        "law firm it director",
        "director of information technology",  # in legal context
        "legal tech manager",
        "director of legal operations",
        "it operations manager",  # in legal context
    ],
}

# Flattened set of all ATL title variations (lowercase, for fast lookup)
ALL_ATL_TITLES: set[str] = set()
for titles in ATL_PERSONA_TITLES.values():
    ALL_ATL_TITLES.update(titles)

# Seniority levels that indicate ATL (from Apollo's seniority field)
ATL_SENIORITIES: set[str] = {
    "director",
    "vp",
    "c_suite",
    "owner",
    "founder",
    "partner",
    "manager",  # Sometimes managers have budget authority
}

# Title keywords that strongly suggest ATL
ATL_TITLE_KEYWORDS: set[str] = {
    "director",
    "vp",
    "vice president",
    "chief",
    "head",
    "president",
    "owner",
    "founder",
    "partner",
    "manager",  # Contextual - needs function check
}

# Negative signals - these are NOT ATL, save the credits
NON_ATL_KEYWORDS: set[str] = {
    "student",
    "intern",
    "coordinator",
    "assistant",
    "associate",
    "analyst",
    "specialist",
    "administrator",  # Generic admin, not court administrator
    "receptionist",
    "clerk",  # Generic clerk, not clerk of court
    "trainee",
    "fellow",
    "resident",  # Medical resident, not decision-maker
    "teacher",
    "professor",  # Academic, not buying
    "lecturer",
    "researcher",
    "scientist",
    "engineer",  # Unless "Broadcast Engineer"
    "developer",
    "programmer",
    "designer",
    "technician",
}

# Seniorities that indicate NOT ATL
NON_ATL_SENIORITIES: set[str] = {
    "entry",
    "individual_contributor",
    "intern",
    "student",
}


@dataclass
class ATLMatch:
    """Result of ATL decision-maker detection.

    PHONES ARE GOLD - but only for ATLs who Tim will actually call.
    """

    is_atl: bool
    """True if this contact is worth the 8-credit phone reveal."""

    persona_id: str | None
    """Matched persona ID (e.g., 'av_director') if exact/fuzzy match found."""

    confidence: float
    """0.0-1.0 confidence in the ATL determination."""

    reason: str
    """Human-readable explanation of the decision."""


def _normalize_title(title: str) -> str:
    """Normalize title for comparison (lowercase, strip, collapse whitespace)."""
    return " ".join(title.lower().strip().split())


def _title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity ratio between two titles using SequenceMatcher."""
    return SequenceMatcher(None, title1, title2).ratio()


def _find_exact_persona_match(normalized_title: str) -> tuple[PersonaId, str] | None:
    """Check for exact match against persona title variations.

    Returns:
        Tuple of (PersonaId, matched_title) if found, None otherwise.
    """
    for persona_id, titles in ATL_PERSONA_TITLES.items():
        for title in titles:
            if normalized_title == title:
                return (persona_id, title)
    return None


def _find_fuzzy_persona_match(
    normalized_title: str, threshold: float = 0.6
) -> tuple[PersonaId, str, float] | None:
    """Find best fuzzy match against persona title variations.

    Args:
        normalized_title: The normalized title to match.
        threshold: Minimum similarity ratio (0.0-1.0) to consider a match.

    Returns:
        Tuple of (PersonaId, matched_title, similarity) if found, None otherwise.
    """
    best_match: tuple[PersonaId, str, float] | None = None
    best_similarity = threshold

    for persona_id, titles in ATL_PERSONA_TITLES.items():
        for title in titles:
            similarity = _title_similarity(normalized_title, title)
            if similarity > best_similarity:
                best_match = (persona_id, title, similarity)
                best_similarity = similarity

    return best_match


def _has_non_atl_keyword(normalized_title: str) -> str | None:
    """Check if title contains non-ATL keywords.

    Returns:
        The non-ATL keyword found, or None if clean.
    """
    # Special case: "Broadcast Engineer" IS ATL (Technical Director persona)
    if "broadcast" in normalized_title and "engineer" in normalized_title:
        return None

    # Special case: "Court Administrator" or "Clerk of Court" IS ATL
    if "court" in normalized_title:
        return None

    words = normalized_title.split()
    for word in words:
        if word in NON_ATL_KEYWORDS:
            return word

    return None


def _has_atl_keyword(normalized_title: str) -> str | None:
    """Check if title contains ATL-indicating keywords.

    Returns:
        The ATL keyword found, or None if none found.
    """
    words = normalized_title.split()
    for word in words:
        if word in ATL_TITLE_KEYWORDS:
            return word

    # Check multi-word keywords
    if "vice president" in normalized_title:
        return "vice president"

    return None


def is_atl_decision_maker(
    title: str | None,
    seniority: str | None = None,
) -> ATLMatch:
    """Determine if a contact is an ATL decision-maker worth phone enrichment.

    This is the matchmaker strategy: identify decision-makers FAST so Tim can
    call them before distributors/integrators reach them.

    ATL Criteria (phone enrichment = YES):
    - Matches one of 8 persona titles (exact or fuzzy)
    - Has VP/Director/C-level in title
    - Seniority is "director" or higher (from Apollo)

    Non-ATL (phone enrichment = NO, save 7 credits):
    - Student, Intern, Coordinator, Assistant
    - Analyst, Specialist (end users)
    - Unknown/empty title with no seniority

    Args:
        title: Contact's job title (from Apollo or Harvester).
        seniority: Apollo's seniority field if available.

    Returns:
        ATLMatch with is_atl, persona_id, confidence, and reason.
    """
    # Handle missing title
    if not title or not title.strip():
        # If we have seniority data, use it
        if seniority:
            seniority_lower = seniority.lower().strip()
            if seniority_lower in ATL_SENIORITIES:
                return ATLMatch(
                    is_atl=True,
                    persona_id=None,
                    confidence=0.6,
                    reason=f"No title but seniority '{seniority}' indicates decision-maker",
                )
            if seniority_lower in NON_ATL_SENIORITIES:
                return ATLMatch(
                    is_atl=False,
                    persona_id=None,
                    confidence=0.8,
                    reason=f"No title and seniority '{seniority}' indicates non-decision-maker",
                )

        # No data at all - don't spend credits
        return ATLMatch(
            is_atl=False,
            persona_id=None,
            confidence=0.5,
            reason="No title or seniority data - conserve credits",
        )

    normalized_title = _normalize_title(title)

    # Check for non-ATL keywords first (negative signal override)
    non_atl_keyword = _has_non_atl_keyword(normalized_title)
    if non_atl_keyword:
        # Exception: if seniority indicates senior level, override keyword
        if seniority and seniority.lower() in ATL_SENIORITIES:
            # Senior level overrides generic keyword (e.g., "Senior Manager" vs "Manager")
            pass
        else:
            return ATLMatch(
                is_atl=False,
                persona_id=None,
                confidence=0.85,
                reason=f"Title contains non-ATL keyword '{non_atl_keyword}'",
            )

    # Check seniority for explicit non-ATL
    if seniority:
        seniority_lower = seniority.lower().strip()
        if seniority_lower in NON_ATL_SENIORITIES:
            return ATLMatch(
                is_atl=False,
                persona_id=None,
                confidence=0.9,
                reason=f"Seniority '{seniority}' indicates non-decision-maker",
            )

    # Try exact persona match first
    exact_match = _find_exact_persona_match(normalized_title)
    if exact_match:
        persona_id, matched_title = exact_match
        return ATLMatch(
            is_atl=True,
            persona_id=persona_id.value,
            confidence=1.0,
            reason=f"Exact match to {persona_id.value} persona title '{matched_title}'",
        )

    # Try fuzzy persona match
    fuzzy_match = _find_fuzzy_persona_match(normalized_title)
    if fuzzy_match:
        persona_id, matched_title, similarity = fuzzy_match
        return ATLMatch(
            is_atl=True,
            persona_id=persona_id.value,
            confidence=similarity,
            reason=f"Fuzzy match ({similarity:.0%}) to {persona_id.value} persona title '{matched_title}'",
        )

    # Check for ATL keywords in title
    atl_keyword = _has_atl_keyword(normalized_title)
    if atl_keyword:
        # Higher confidence if seniority confirms
        confidence = 0.8 if seniority and seniority.lower() in ATL_SENIORITIES else 0.7
        return ATLMatch(
            is_atl=True,
            persona_id=None,
            confidence=confidence,
            reason=f"Title contains ATL keyword '{atl_keyword}'",
        )

    # Check seniority alone
    if seniority:
        seniority_lower = seniority.lower().strip()
        if seniority_lower in ATL_SENIORITIES:
            return ATLMatch(
                is_atl=True,
                persona_id=None,
                confidence=0.6,
                reason=f"Seniority '{seniority}' indicates decision-maker level",
            )

    # Default: not ATL, conserve credits
    return ATLMatch(
        is_atl=False,
        persona_id=None,
        confidence=0.5,
        reason=f"Title '{title}' does not match ATL criteria",
    )


def get_all_atl_titles() -> list[str]:
    """Get all ATL title variations for reference.

    Returns:
        List of all 48+ ATL title variations from the BDR Playbook.
    """
    return sorted(ALL_ATL_TITLES)


def get_persona_titles(persona_id: str) -> list[str]:
    """Get title variations for a specific persona.

    Args:
        persona_id: The persona ID (e.g., 'av_director').

    Returns:
        List of title variations for that persona, or empty list if not found.
    """
    try:
        persona = PersonaId(persona_id)
        return ATL_PERSONA_TITLES.get(persona, [])
    except ValueError:
        return []
