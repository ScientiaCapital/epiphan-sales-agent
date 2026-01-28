"""Tools for Qualification Agent.

Provides scoring functions for Tim's 5-dimension weighted ICP criteria:
- Company Size (25%)
- Industry Vertical (20%)
- Use Case Fit (25%)
- Tech Stack Signals (15%)
- Buying Authority (15%)

Tier Thresholds (0-100 weighted scale):
- Tier 1 (70+): Priority sequence, AE involvement early
- Tier 2 (50-69): Standard sequence
- Tier 3 (30-49): Light touch, marketing nurture
- Not ICP (<30): Disqualify
"""

from typing import Any

from app.services.langgraph.states import (
    ICPScoreBreakdown,
    NextAction,
    QualificationTier,
)

# Weight constants
WEIGHT_COMPANY_SIZE = 0.25
WEIGHT_INDUSTRY_VERTICAL = 0.20
WEIGHT_USE_CASE_FIT = 0.25
WEIGHT_TECH_STACK = 0.15
WEIGHT_BUYING_AUTHORITY = 0.15

# Competitor tech keywords (replacement opportunities)
COMPETITOR_TECH = {
    "vaddio",
    "crestron",
    "panopto",
    "kaltura",
    "mediasite",
    "yuja",
    "qumu",
    "brightcove",
    "vidyo",
    "polycom",
    "cisco webex",
    "lifesize",
}

# LMS/collaboration tools (integration opportunities)
LMS_COLLABORATION_TECH = {
    "canvas",
    "blackboard",
    "moodle",
    "d2l",
    "brightspace",
    "schoology",
    "microsoft teams",
    "zoom",
    "webex",
    "google meet",
    "slack",
}


def classify_company_size(
    employees: int | None,
) -> tuple[str, int, str]:
    """
    Classify company by size and return score.

    Scoring (Weight: 25%):
    - Enterprise (1000+): 10 points
    - Mid-market (100-999): 8 points
    - SMB (10-99): 4 points
    - Too small (<10): 0 points

    Args:
        employees: Number of employees or None if unknown

    Returns:
        Tuple of (category, score, reason)
    """
    if employees is None:
        return ("Unknown", 0, "Employee count missing or unknown")

    if employees >= 1000:
        return ("Enterprise", 10, f"Large organization with {employees:,} employees")
    elif employees >= 100:
        return ("Mid-market", 8, f"Mid-size organization with {employees:,} employees")
    elif employees >= 10:
        return ("SMB", 4, f"Small business with {employees:,} employees")
    else:
        return ("Too small", 0, f"Very small organization ({employees} employees)")


def classify_vertical(
    industry: str | None,
    company: str | None,
    inferred: str | None = None,
) -> tuple[str, int, str]:
    """
    Classify industry vertical and return score.

    Scoring (Weight: 20%):
    - Higher Ed: 10 points
    - Healthcare: 9 points
    - Corporate: 8 points
    - Broadcast/Media: 7 points
    - Legal/Government: 6 points
    - Other: 3 points

    Args:
        industry: Industry from enrichment data
        company: Company name for keyword detection
        inferred: Inferred vertical if industry is None

    Returns:
        Tuple of (category, score, reason)
    """
    # Use inferred if industry is None
    source_str = industry or inferred or ""
    source_str_lower = source_str.lower() if source_str else ""
    company_lower = (company or "").lower()

    # Higher Ed detection
    if any(
        kw in source_str_lower
        for kw in ["education", "higher ed", "university", "college", "academic"]
    ) or any(
        kw in company_lower for kw in ["university", "college", "school", "institute"]
    ):
        return (
            "Higher Ed",
            10,
            f"Higher education vertical detected ({source_str or company})",
        )

    # Healthcare detection
    if any(
        kw in source_str_lower
        for kw in ["healthcare", "health care", "medical", "hospital", "clinical"]
    ) or any(kw in company_lower for kw in ["hospital", "medical", "health", "clinic"]):
        return (
            "Healthcare",
            9,
            f"Healthcare vertical detected ({source_str or company})",
        )

    # Corporate/Enterprise detection
    if any(
        kw in source_str_lower
        for kw in ["corporate", "enterprise", "business services", "financial"]
    ):
        return (
            "Corporate",
            8,
            f"Corporate vertical detected ({source_str})",
        )

    # Broadcast/Media detection
    if any(
        kw in source_str_lower
        for kw in ["broadcast", "media", "entertainment", "television", "streaming"]
    ):
        return (
            "Broadcast",
            7,
            f"Broadcast/Media vertical detected ({source_str})",
        )

    # Legal/Government detection
    if any(
        kw in source_str_lower for kw in ["legal", "law", "government", "public sector"]
    ) or any(kw in company_lower for kw in ["court", "law firm", "government"]):
        return (
            "Legal/Government",
            6,
            f"Legal/Government vertical detected ({source_str or company})",
        )

    # Other/Unknown
    if source_str:
        return ("Other", 3, f"Non-core vertical: {source_str}")
    return ("Other", 3, "Industry vertical unknown")


def classify_use_case(
    persona: str | None,
    vertical: str | None,
    title: str | None,
    tech_stack: list[str] | None = None,
) -> tuple[str, int, str]:
    """
    Classify use case fit and return score.

    Scoring (Weight: 25%):
    - Live streaming: 10 points
    - Lecture capture: 9 points
    - Recording only: 6 points
    - Consumer/Other: 0 points

    Args:
        persona: Matched persona (e.g., "AV Director")
        vertical: Industry vertical
        title: Job title
        tech_stack: Tech stack for signal detection

    Returns:
        Tuple of (category, score, reason)
    """
    persona_lower = (persona or "").lower()
    title_lower = (title or "").lower()
    tech_stack_lower = [t.lower() for t in (tech_stack or [])]

    # Consumer detection (early exit)
    if any(kw in title_lower for kw in ["student", "intern", "amateur", "hobbyist"]):
        return ("Consumer", 0, "Consumer/non-business user detected")

    # AV Director / Technical Director - Live streaming fit
    if any(
        p in persona_lower for p in ["av director", "technical director", "av"]
    ) or any(kw in title_lower for kw in ["av director", "technical director", "av "]):
        return ("Live streaming", 10, f"Live production persona: {persona or title}")

    # L&D Director / Corporate Communications - Lecture capture fit
    if any(
        p in persona_lower
        for p in ["l&d director", "corporate communications", "training"]
    ) or any(
        kw in title_lower for kw in ["l&d", "learning", "training", "communications"]
    ):
        return (
            "Lecture capture",
            9,
            f"Training/communications persona: {persona or title}",
        )

    # Simulation Director - Healthcare training fit
    if "simulation" in persona_lower or "simulation" in title_lower:
        return (
            "Lecture capture",
            9,
            f"Simulation training persona: {persona or title}",
        )

    # Court Administrator / EHS - Recording fit
    if any(
        p in persona_lower for p in ["court administrator", "ehs", "law firm it"]
    ) or any(kw in title_lower for kw in ["court", "ehs", "compliance", "legal"]):
        return ("Recording only", 6, f"Recording-focused persona: {persona or title}")

    # Video-related title detection
    if any(kw in title_lower for kw in ["video", "media", "broadcast", "production"]):
        return ("Live streaming", 10, f"Video-related title: {title}")

    # Tech stack signals
    if tech_stack_lower:
        streaming_tools = ["obs", "vmix", "wirecast", "tricaster", "livestream"]
        if any(tool in " ".join(tech_stack_lower) for tool in streaming_tools):
            return ("Live streaming", 10, "Streaming tools detected in tech stack")

        # Collaboration tools suggest training use case
        if any(
            tool in " ".join(tech_stack_lower)
            for tool in ["zoom", "teams", "webex", "canvas"]
        ):
            return ("Lecture capture", 9, "Collaboration tools suggest training use case")

    # Default based on vertical
    if vertical and "higher ed" in vertical.lower():
        return ("Lecture capture", 9, "Higher Ed vertical suggests lecture capture")

    # No clear use case
    if title:
        return ("Recording only", 6, f"General business user: {title}")

    return ("Consumer", 0, "No clear use case fit identified")


def classify_tech_stack(
    tech_stack: list[str] | None,
    clearbit_data: dict[str, Any] | None = None,
) -> tuple[str, int, str]:
    """
    Classify tech stack signals and return score.

    Scoring (Weight: 15%):
    - Competitive solution (Vaddio, Crestron, etc.): 10 points
    - LMS/collaboration need (Canvas, Teams, etc.): 8 points
    - No relevant solution: 5 points

    Args:
        tech_stack: List of tech/tools from enrichment
        clearbit_data: Clearbit data which may contain tech_stack

    Returns:
        Tuple of (category, score, reason)
    """
    # Extract tech stack from clearbit if not provided
    stack = tech_stack or []
    if not stack and clearbit_data:
        stack = clearbit_data.get("tech_stack", [])

    if not stack:
        return ("No solution", 5, "No tech stack information available")

    stack_lower = [t.lower() for t in stack]
    stack_str = " ".join(stack_lower)

    # Check for competitor solutions (highest priority)
    competitors_found = []
    for competitor in COMPETITOR_TECH:
        if competitor in stack_str:
            competitors_found.append(competitor)

    if competitors_found:
        return (
            "Competitive solution",
            10,
            f"Competitor tech detected: {', '.join(competitors_found[:3])}",
        )

    # Check for LMS/collaboration tools
    lms_found = []
    for tool in LMS_COLLABORATION_TECH:
        if tool in stack_str:
            lms_found.append(tool)

    if lms_found:
        return (
            "LMS need",
            8,
            f"LMS/collaboration tools: {', '.join(lms_found[:3])}",
        )

    # No relevant tech
    return ("No solution", 5, f"No relevant AV/video tech in stack: {stack[:3]}")


def classify_buying_authority(
    title: str | None,
    seniority: str | None = None,
    apollo_data: dict[str, Any] | None = None,
) -> tuple[str, int, str]:
    """
    Classify buying authority and return score.

    Scoring (Weight: 15%):
    - Budget holder (Director+): 10 points
    - Influencer (Manager, Sr.): 7 points
    - End user (Specialist, Analyst): 4 points
    - Student/Intern: 0 points

    Args:
        title: Job title
        seniority: Seniority level (e.g., "director", "manager")
        apollo_data: Apollo data which may contain seniority

    Returns:
        Tuple of (category, score, reason)
    """
    # Extract seniority from apollo if not provided
    sen = seniority
    if not sen and apollo_data:
        sen = apollo_data.get("seniority")

    title_lower = (title or "").lower()
    sen_lower = (sen or "").lower()

    # Student/Intern detection (early exit)
    if any(kw in title_lower for kw in ["student", "intern"]):
        return ("Student", 0, f"Non-buyer: {title}")

    # Budget holder detection
    budget_holder_keywords = [
        "director",
        "vp",
        "vice president",
        "chief",
        "cto",
        "cio",
        "coo",
        "ceo",
        "president",
        "head of",
        "dean",
        "administrator",
    ]

    if any(kw in title_lower for kw in budget_holder_keywords) or any(
        kw in sen_lower for kw in ["director", "vp", "c-level", "executive", "owner"]
    ):
        return ("Budget holder", 10, f"Decision maker: {title or sen}")

    # Influencer detection
    influencer_keywords = ["manager", "senior", "sr.", "sr ", "lead", "principal"]

    if any(kw in title_lower for kw in influencer_keywords) or any(
        kw in sen_lower for kw in ["manager", "senior"]
    ):
        return ("Influencer", 7, f"Influencer role: {title or sen}")

    # End user detection
    end_user_keywords = [
        "analyst",
        "specialist",
        "coordinator",
        "associate",
        "engineer",
        "technician",
    ]

    if any(kw in title_lower for kw in end_user_keywords):
        return ("End user", 4, f"End user role: {title}")

    # Default to end user if title exists but doesn't match
    if title:
        return ("End user", 4, f"Unknown seniority: {title}")

    # No title info
    return ("End user", 4, "Title/seniority unknown")


def calculate_weighted_score(breakdown: ICPScoreBreakdown) -> float:
    """
    Calculate total weighted score from dimension breakdown.

    Weights:
    - Company Size: 25%
    - Industry Vertical: 20%
    - Use Case Fit: 25%
    - Tech Stack Signals: 15%
    - Buying Authority: 15%

    Args:
        breakdown: Score breakdown with all 5 dimensions

    Returns:
        Total weighted score (0-100)
    """
    return (
        breakdown["company_size"]["weighted_score"]
        + breakdown["industry_vertical"]["weighted_score"]
        + breakdown["use_case_fit"]["weighted_score"]
        + breakdown["tech_stack_signals"]["weighted_score"]
        + breakdown["buying_authority"]["weighted_score"]
    )


def assign_tier(score: float) -> QualificationTier:
    """
    Assign qualification tier based on weighted score.

    Tier Thresholds:
    - Tier 1 (70+): Priority sequence, AE involvement early
    - Tier 2 (50-69): Standard sequence
    - Tier 3 (30-49): Light touch, marketing nurture
    - Not ICP (<30): Disqualify

    Args:
        score: Weighted score (0-100)

    Returns:
        QualificationTier enum value
    """
    if score >= 70.0:
        return QualificationTier.TIER_1
    elif score >= 50.0:
        return QualificationTier.TIER_2
    elif score >= 30.0:
        return QualificationTier.TIER_3
    else:
        return QualificationTier.NOT_ICP


def determine_next_action(
    tier: QualificationTier,
    missing_info: list[str],
    confidence: float,
) -> NextAction:
    """
    Determine recommended next action based on tier and data quality.

    Args:
        tier: Assigned qualification tier
        missing_info: List of missing data dimensions
        confidence: Overall confidence score (0.0-1.0)

    Returns:
        NextAction with action_type, description, priority, ae_involvement, missing_info
    """
    # Base recommendations by tier
    if tier == QualificationTier.TIER_1:
        action: NextAction = {
            "action_type": "priority_sequence",
            "description": "High-priority lead. Add to priority outreach sequence with immediate BDR follow-up.",
            "priority": "high",
            "ae_involvement": True,
            "missing_info": missing_info,
        }

        # Adjust if low confidence
        if confidence < 0.5 and missing_info:
            action["description"] = (
                f"High-potential lead but needs more research. "
                f"Missing: {', '.join(missing_info)}. Verify before priority sequence."
            )

    elif tier == QualificationTier.TIER_2:
        action = {
            "action_type": "standard_sequence",
            "description": "Good lead. Add to standard outreach sequence.",
            "priority": "medium",
            "ae_involvement": False,
            "missing_info": missing_info,
        }

    elif tier == QualificationTier.TIER_3:
        action = {
            "action_type": "nurture",
            "description": "Lower priority lead. Add to marketing nurture campaign.",
            "priority": "low",
            "ae_involvement": False,
            "missing_info": missing_info,
        }

    else:  # NOT_ICP
        action = {
            "action_type": "disqualify",
            "description": "Does not meet ICP criteria. Mark as disqualified.",
            "priority": "low",
            "ae_involvement": False,
            "missing_info": missing_info,
        }

    return action
