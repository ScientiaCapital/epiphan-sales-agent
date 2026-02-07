"""University account scoring service.

Scores university accounts on 5 dimensions tailored to higher education
AV/video opportunity sizing:

1. Carnegie Classification (25%) - Research intensity = tech budget proxy
2. Enrollment Size (25%) - More students = more rooms = more AV need
3. Technology Signals (20%) - Existing AV/LMS = readiness to buy
4. Engagement Level (15%) - Existing contacts and interactions
5. Strategic Fit (15%) - Public/private, athletics, closed-won history

Account Tiers:
- A (75+): Priority outreach - find decision-makers immediately
- B (50-74): Standard outreach - batch enrich contacts
- C (30-49): Marketing nurture
- D (<30): Low priority
"""

from app.data.university_schemas import (
    AccountDimensionScore,
    AccountScoreBreakdown,
    AccountTier,
    AthleticDivision,
    CarnegieClassification,
    InstitutionType,
    UniversityAccountCreate,
)
from app.services.langgraph.tools.qualification_tools import (
    COMPETITOR_TECH,
    LMS_COLLABORATION_TECH,
)

# Weight constants (total = 100%)
WEIGHT_CARNEGIE = 0.25
WEIGHT_ENROLLMENT = 0.25
WEIGHT_TECHNOLOGY = 0.20
WEIGHT_ENGAGEMENT = 0.15
WEIGHT_STRATEGIC = 0.15

# Tier thresholds (out of 100 weighted)
TIER_A_THRESHOLD = 75.0
TIER_B_THRESHOLD = 50.0
TIER_C_THRESHOLD = 30.0

# Video platform competitors (rip-and-replace opportunity)
VIDEO_PLATFORM_COMPETITORS = {
    "panopto",
    "kaltura",
    "mediasite",
    "yuja",
    "echo360",
    "tegrity",
    "opencast",
    "qumu",
    "brightcove",
    "vbrick",
}

# AV infrastructure vendors (expansion play)
AV_INFRASTRUCTURE = {
    "crestron",
    "extron",
    "qsc",
    "biamp",
    "shure",
    "vaddio",
    "polycom",
    "cisco",
    "logitech",
    "neat",
}


def classify_carnegie(
    classification: CarnegieClassification | None,
) -> tuple[str, int, str]:
    """
    Score by Carnegie Classification (Weight: 25%).

    R1/R2 institutions have largest AV budgets and most rooms.

    Returns:
        Tuple of (category, raw_score, reason)
    """
    if classification is None:
        return ("Unknown", 2, "Carnegie classification not available")

    scores: dict[CarnegieClassification, tuple[str, int, str]] = {
        CarnegieClassification.R1: (
            "R1",
            10,
            "R1: Very High Research Activity - largest AV budgets and room counts",
        ),
        CarnegieClassification.R2: (
            "R2",
            8,
            "R2: High Research Activity - strong AV infrastructure needs",
        ),
        CarnegieClassification.D_PU: (
            "Doctoral/Professional",
            7,
            "Doctoral/Professional University - meaningful AV demand",
        ),
        CarnegieClassification.M1: (
            "Master's Large",
            6,
            "Master's (Larger Programs) - moderate AV infrastructure",
        ),
        CarnegieClassification.M2: (
            "Master's Medium",
            5,
            "Master's (Medium Programs) - moderate AV needs",
        ),
        CarnegieClassification.M3: (
            "Master's Small",
            4,
            "Master's (Smaller Programs) - limited AV scope",
        ),
        CarnegieClassification.BACCALAUREATE: (
            "Baccalaureate",
            3,
            "Baccalaureate College - smaller AV footprint",
        ),
        CarnegieClassification.ASSOCIATE: (
            "Associate",
            2,
            "Associate's College - minimal AV investment",
        ),
        CarnegieClassification.SPECIAL_FOCUS: (
            "Special Focus",
            4,
            "Special Focus Institution - may have niche AV needs",
        ),
        CarnegieClassification.TRIBAL: (
            "Tribal",
            3,
            "Tribal College - limited budget but potential federal funding",
        ),
        CarnegieClassification.OTHER: (
            "Other",
            2,
            "Other institution type - unclear AV opportunity",
        ),
    }

    return scores.get(
        classification, ("Unknown", 2, "Unrecognized classification")
    )


def classify_enrollment(enrollment: int | None) -> tuple[str, int, str]:
    """
    Score by student enrollment (Weight: 20%).

    More students = more classrooms, lecture halls, and AV-equipped spaces.

    Returns:
        Tuple of (category, raw_score, reason)
    """
    if enrollment is None:
        return ("Unknown", 0, "Enrollment data not available")

    if enrollment >= 30000:
        return (
            "Very Large",
            10,
            f"Very large institution ({enrollment:,} students) - 200+ AV spaces likely",
        )
    elif enrollment >= 15000:
        return (
            "Large",
            8,
            f"Large institution ({enrollment:,} students) - 100+ AV spaces likely",
        )
    elif enrollment >= 5000:
        return (
            "Medium",
            6,
            f"Mid-size institution ({enrollment:,} students) - 50+ AV spaces likely",
        )
    elif enrollment >= 1000:
        return (
            "Small",
            4,
            f"Small institution ({enrollment:,} students) - limited AV footprint",
        )
    else:
        return (
            "Very Small",
            2,
            f"Very small institution ({enrollment:,} students) - minimal AV opportunity",
        )


def classify_technology(
    lms_platform: str | None,
    video_platform: str | None,
    av_system: str | None,
    tech_stack: list[str] | None,
) -> tuple[str, int, str]:
    """
    Score by technology signals (Weight: 20%).

    Existing video/AV platforms signal readiness to buy and potential
    rip-and-replace opportunities.

    Returns:
        Tuple of (category, raw_score, reason)
    """
    signals: list[str] = []
    score = 0

    # Check video platform (highest value - direct competitor = rip & replace)
    if video_platform:
        vp_lower = video_platform.lower()
        if any(comp in vp_lower for comp in VIDEO_PLATFORM_COMPETITORS):
            signals.append(f"competitor video platform: {video_platform}")
            score = max(score, 10)
        elif any(comp in vp_lower for comp in COMPETITOR_TECH):
            signals.append(f"competitor tech: {video_platform}")
            score = max(score, 10)
        else:
            signals.append(f"video platform: {video_platform}")
            score = max(score, 7)

    # Check AV system
    if av_system:
        av_lower = av_system.lower()
        if any(vendor in av_lower for vendor in AV_INFRASTRUCTURE):
            signals.append(f"AV infrastructure: {av_system}")
            score = max(score, 7)

    # Check LMS platform
    if lms_platform:
        lms_lower = lms_platform.lower()
        if any(lms in lms_lower for lms in LMS_COLLABORATION_TECH):
            signals.append(f"LMS: {lms_platform}")
            score = max(score, 8)
        else:
            signals.append(f"LMS: {lms_platform}")
            score = max(score, 6)

    # Check tech stack for additional signals
    if tech_stack:
        stack_lower = " ".join(t.lower() for t in tech_stack)
        for comp in VIDEO_PLATFORM_COMPETITORS | COMPETITOR_TECH:
            if comp in stack_lower and f"competitor: {comp}" not in " ".join(signals):
                signals.append(f"tech stack competitor: {comp}")
                score = max(score, 10)
                break

        for lms in LMS_COLLABORATION_TECH:
            if lms in stack_lower and f"LMS: {lms}" not in " ".join(signals):
                signals.append(f"tech stack LMS: {lms}")
                score = max(score, 8)
                break

    if not signals:
        return ("No signals", 3, "No technology information available")

    category = "Competitor" if score == 10 else ("LMS" if score >= 8 else "AV Infrastructure")
    return (category, score, f"Technology signals: {', '.join(signals[:3])}")


def classify_engagement(
    contact_count: int,
    decision_maker_count: int,
    is_existing_customer: bool,
    has_active_opportunity: bool,
) -> tuple[str, int, str]:
    """
    Score by engagement level (Weight: 15%).

    Existing relationships dramatically increase deal probability.

    Returns:
        Tuple of (category, raw_score, reason)
    """
    if is_existing_customer:
        return (
            "Existing Customer",
            10,
            "Existing customer - expansion/upsell opportunity",
        )

    if has_active_opportunity:
        return (
            "Active Opportunity",
            9,
            "Active sales opportunity in pipeline",
        )

    if decision_maker_count > 0:
        return (
            "Has Decision Maker",
            7,
            f"Has {decision_maker_count} decision-maker contact(s) on file",
        )

    if contact_count > 0:
        return (
            "Has Contacts",
            4,
            f"Has {contact_count} contact(s) but no identified decision-maker",
        )

    return (
        "No Contacts",
        0,
        "No contacts on file - needs research to identify decision-makers",
    )


def classify_strategic_fit(
    institution_type: InstitutionType | None,
    athletic_division: AthleticDivision | None,
    carnegie: CarnegieClassification | None,
) -> tuple[str, int, str]:
    """
    Score by strategic fit (Weight: 15%).

    Public R1s with D1 athletics are the ideal university target:
    - Public = larger budgets, procurement-friendly
    - D1 athletics = high demand for live streaming
    - R1 = large campus, many departments

    Returns:
        Tuple of (category, raw_score, reason)
    """
    score = 0
    reasons: list[str] = []

    # Public institution bonus (bigger budgets, RFP-friendly)
    if institution_type == InstitutionType.PUBLIC:
        score += 4
        reasons.append("public institution (larger AV budgets)")
    elif institution_type == InstitutionType.PRIVATE_NONPROFIT:
        score += 3
        reasons.append("private nonprofit")
    elif institution_type == InstitutionType.PRIVATE_FOR_PROFIT:
        score += 1
        reasons.append("private for-profit (limited AV investment)")

    # Athletics - streaming demand
    if athletic_division == AthleticDivision.NCAA_D1:
        score += 4
        reasons.append("NCAA D1 (high live streaming demand)")
    elif athletic_division == AthleticDivision.NCAA_D2:
        score += 3
        reasons.append("NCAA D2 (moderate streaming demand)")
    elif athletic_division == AthleticDivision.NCAA_D3:
        score += 2
        reasons.append("NCAA D3")
    elif athletic_division in (AthleticDivision.NAIA, AthleticDivision.NJCAA):
        score += 1
        reasons.append(f"{athletic_division.value.upper()}")

    # R1/R2 strategic bonus (multiple departments = multiple deals)
    if carnegie in (CarnegieClassification.R1, CarnegieClassification.R2):
        score += 2
        reasons.append("research university (multi-department potential)")

    score = min(score, 10)

    if not reasons:
        return ("Unknown", 2, "Insufficient data for strategic fit assessment")

    category = "High Fit" if score >= 7 else ("Medium Fit" if score >= 4 else "Low Fit")
    return (category, score, "; ".join(reasons))


class UniversityScorer:
    """Scores university accounts across 5 weighted dimensions."""

    def score_account(
        self, account: UniversityAccountCreate
    ) -> tuple[float, AccountTier, AccountScoreBreakdown, list[str]]:
        """
        Score a university account.

        Args:
            account: University account data to score

        Returns:
            Tuple of (total_score, tier, breakdown, missing_data)
        """
        missing_data: list[str] = []

        # 1. Carnegie Classification (25%)
        carnegie_cat, carnegie_raw, carnegie_reason = classify_carnegie(
            account.carnegie_classification
        )
        if account.carnegie_classification is None:
            missing_data.append("carnegie_classification")
        carnegie_weighted = carnegie_raw * WEIGHT_CARNEGIE * 10

        # 2. Enrollment Size (20%)
        enroll_cat, enroll_raw, enroll_reason = classify_enrollment(account.enrollment)
        if account.enrollment is None:
            missing_data.append("enrollment")
        enroll_weighted = enroll_raw * WEIGHT_ENROLLMENT * 10

        # 3. Technology Signals (20%)
        tech_cat, tech_raw, tech_reason = classify_technology(
            lms_platform=account.lms_platform,
            video_platform=account.video_platform,
            av_system=account.av_system,
            tech_stack=account.tech_stack,
        )
        if not any([account.lms_platform, account.video_platform, account.av_system, account.tech_stack]):
            missing_data.append("technology_data")
        tech_weighted = tech_raw * WEIGHT_TECHNOLOGY * 10

        # 4. Engagement Level (15%)
        engage_cat, engage_raw, engage_reason = classify_engagement(
            contact_count=account.contact_count,
            decision_maker_count=account.decision_maker_count,
            is_existing_customer=account.is_existing_customer,
            has_active_opportunity=account.has_active_opportunity,
        )
        if account.contact_count == 0:
            missing_data.append("contacts")
        engage_weighted = engage_raw * WEIGHT_ENGAGEMENT * 10

        # 5. Strategic Fit (15%)
        strat_cat, strat_raw, strat_reason = classify_strategic_fit(
            institution_type=account.institution_type,
            athletic_division=account.athletic_division,
            carnegie=account.carnegie_classification,
        )
        if account.institution_type is None:
            missing_data.append("institution_type")
        strat_weighted = strat_raw * WEIGHT_STRATEGIC * 10

        # Total weighted score (0-100)
        total_score = (
            carnegie_weighted
            + enroll_weighted
            + tech_weighted
            + engage_weighted
            + strat_weighted
        )

        # Assign tier
        tier = assign_account_tier(total_score)

        # Build breakdown
        breakdown = AccountScoreBreakdown(
            carnegie_classification=AccountDimensionScore(
                category=carnegie_cat,
                raw_score=carnegie_raw,
                weighted_score=carnegie_weighted,
                reason=carnegie_reason,
            ),
            enrollment_size=AccountDimensionScore(
                category=enroll_cat,
                raw_score=enroll_raw,
                weighted_score=enroll_weighted,
                reason=enroll_reason,
            ),
            technology_signals=AccountDimensionScore(
                category=tech_cat,
                raw_score=tech_raw,
                weighted_score=tech_weighted,
                reason=tech_reason,
            ),
            engagement_level=AccountDimensionScore(
                category=engage_cat,
                raw_score=engage_raw,
                weighted_score=engage_weighted,
                reason=engage_reason,
            ),
            strategic_fit=AccountDimensionScore(
                category=strat_cat,
                raw_score=strat_raw,
                weighted_score=strat_weighted,
                reason=strat_reason,
            ),
        )

        return total_score, tier, breakdown, missing_data

    def determine_next_action(
        self, tier: AccountTier, missing_data: list[str], account: UniversityAccountCreate
    ) -> str:
        """Determine recommended next action based on tier and data gaps."""
        if tier == AccountTier.A:
            if account.decision_maker_count == 0 and account.contact_count == 0:
                return (
                    "A-tier with zero contacts. Use LinkedIn Sales Navigator to find "
                    "'Director AV' OR 'Director IT' OR 'Manager Technology Services'. "
                    "Add to HubSpot immediately."
                )
            if account.decision_maker_count == 0:
                return (
                    "A-tier with contacts but no decision-maker. Research existing "
                    "contacts for budget authority, or find Director/VP-level contact."
                )
            return (
                "A-tier with decision-maker on file. Generate call brief and "
                "add to priority outreach sequence."
            )

        if tier == AccountTier.B:
            if "contacts" in missing_data:
                return (
                    "B-tier with no contacts. Batch enrich using Clay (10 accounts "
                    "at a time), find 2-3 contacts per account."
                )
            return "B-tier account. Add to standard outreach sequence."

        if tier == AccountTier.C:
            return "C-tier account. Add to marketing nurture campaign."

        return "D-tier account. Low priority - revisit if new signals emerge."


def assign_account_tier(score: float) -> AccountTier:
    """Assign account tier based on weighted score."""
    if score >= TIER_A_THRESHOLD:
        return AccountTier.A
    elif score >= TIER_B_THRESHOLD:
        return AccountTier.B
    elif score >= TIER_C_THRESHOLD:
        return AccountTier.C
    else:
        return AccountTier.D


# Singleton instance
university_scorer = UniversityScorer()
