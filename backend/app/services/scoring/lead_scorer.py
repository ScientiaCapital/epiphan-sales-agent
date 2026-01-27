"""Lead Scorer service for scoring leads using ICP criteria.

Scores leads on 4 dimensions (0-25 points each) for a total of 0-100:
1. Persona fit: How well the title matches a buyer persona
2. Vertical alignment: How well the company fits target verticals
3. Company signals: Company quality indicators (domain, size hints)
4. Engagement data: Recent activity and contact history
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.data.lead_schemas import Lead, LeadTier
from app.services.scoring.persona_matcher import PersonaMatcher, persona_matcher


@dataclass
class LeadScoreResult:
    """Result of lead scoring with breakdown."""

    # Score breakdown (0-25 each)
    persona_score: int
    vertical_score: int
    company_score: int
    engagement_score: int

    # Total and tier
    total_score: int
    tier: LeadTier

    # Matching details
    persona_match: str | None
    persona_confidence: float
    vertical: str | None


class LeadScorer:
    """
    Service for scoring leads using ICP criteria.

    Scoring dimensions:
    - Persona fit (0-25): How well the job title matches a buyer persona
    - Vertical alignment (0-25): How well company fits target verticals
    - Company signals (0-25): Domain quality, company name indicators
    - Engagement data (0-25): Contact count, recency of activity

    Tiers:
    - Hot (85+): Immediate outreach priority
    - Warm (70-84): This week priority
    - Nurture (50-69): Sequence enrollment
    - Cold (<50): Long-term nurture
    """

    def __init__(self, matcher: PersonaMatcher | None = None):
        """Initialize scorer with persona matcher."""
        self.matcher = matcher or persona_matcher

    def score_lead(self, lead: Lead) -> LeadScoreResult:
        """
        Score a single lead across all dimensions.

        Args:
            lead: Lead to score

        Returns:
            LeadScoreResult with score breakdown and tier
        """
        # Match persona first
        persona_result = self.matcher.match_persona(
            title=lead.title,
            company=lead.company,
            industry=lead.industry,
        )

        # Calculate each dimension
        persona_score = self._calculate_persona_score(persona_result.confidence)
        vertical_score = self._calculate_vertical_score(
            persona_result.inferred_vertical,
            persona_result.persona_id,
        )
        company_score = self._calculate_company_score(lead)
        engagement_score = self._calculate_engagement_score(lead)

        # Calculate total
        total_score = persona_score + vertical_score + company_score + engagement_score

        # Assign tier
        tier = self._assign_tier(total_score)

        return LeadScoreResult(
            persona_score=persona_score,
            vertical_score=vertical_score,
            company_score=company_score,
            engagement_score=engagement_score,
            total_score=total_score,
            tier=tier,
            persona_match=persona_result.persona_id,
            persona_confidence=persona_result.confidence,
            vertical=persona_result.inferred_vertical,
        )

    def score_leads(self, leads: list[Lead]) -> list[LeadScoreResult]:
        """
        Score multiple leads.

        Args:
            leads: List of leads to score

        Returns:
            List of LeadScoreResult in same order as input
        """
        return [self.score_lead(lead) for lead in leads]

    def _calculate_persona_score(self, confidence: float) -> int:
        """
        Calculate persona fit score (0-25).

        Based on persona match confidence:
        - 0.9-1.0 confidence: 20-25 points
        - 0.7-0.89 confidence: 15-19 points
        - 0.5-0.69 confidence: 10-14 points
        - 0.3-0.49 confidence: 5-9 points
        - <0.3 confidence: 0-4 points
        """
        if confidence >= 0.9:
            return 20 + int((confidence - 0.9) * 50)  # 20-25
        elif confidence >= 0.7:
            return 15 + int((confidence - 0.7) * 20)  # 15-19
        elif confidence >= 0.5:
            return 10 + int((confidence - 0.5) * 20)  # 10-14
        elif confidence >= 0.3:
            return 5 + int((confidence - 0.3) * 20)  # 5-9
        else:
            return int(confidence * 15)  # 0-4

    def _calculate_vertical_score(
        self,
        vertical: str | None,
        persona_id: str | None,
    ) -> int:
        """
        Calculate vertical alignment score (0-25).

        Based on:
        - Whether a vertical could be inferred
        - Whether the vertical aligns with the matched persona
        """
        if not vertical:
            return 5  # Base points for having company info but no vertical inferred

        # Vertical inferred = good signal
        base_score = 15

        # Bonus if persona matches and vertical aligns with persona's target
        if persona_id:
            # Get persona's target verticals
            from app.data.personas import get_persona_by_id
            persona = get_persona_by_id(persona_id)
            if persona and vertical in persona.verticals:
                base_score += 10  # Perfect vertical alignment

        return min(base_score, 25)

    def _calculate_company_score(self, lead: Lead) -> int:
        """
        Calculate company signals score (0-25).

        Based on:
        - Presence of company name
        - Email domain quality (.edu, .gov, corporate)
        - Company name indicators
        """
        score = 0

        # Has company name
        if lead.company:
            score += 5

            # Check for quality company indicators
            company_lower = lead.company.lower()

            # Known quality indicators
            quality_indicators = [
                "university", "college", "hospital", "medical",
                "fortune", "global", "international", "corporation",
                "government", "federal", "state", "county", "city of",
            ]
            for indicator in quality_indicators:
                if indicator in company_lower:
                    score += 5
                    break

        # Email domain analysis
        if lead.email:
            email_lower = lead.email.lower()

            if email_lower.endswith(".edu"):
                score += 10  # Educational institution
            elif email_lower.endswith(".gov"):
                score += 10  # Government organization
            elif email_lower.endswith(".org"):
                score += 5  # Non-profit/organization
            elif any(
                email_lower.endswith(d)
                for d in [".com", ".net", ".io", ".co"]
            ):
                # Corporate domain - check if it's not a free email
                free_domains = [
                    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                    "aol.com", "icloud.com", "mail.com", "protonmail.com",
                ]
                domain = email_lower.split("@")[-1]
                if domain not in free_domains:
                    score += 5  # Corporate email

        return min(score, 25)

    def _calculate_engagement_score(self, lead: Lead) -> int:
        """
        Calculate engagement score (0-25).

        Based on:
        - Contact count (number of touches)
        - Recency of last contact
        - Activity signals
        """
        score = 0

        # Contact count scoring
        contact_count = lead.contact_count or 0
        if contact_count >= 5:
            score += 15
        elif contact_count >= 3:
            score += 10
        elif contact_count >= 1:
            score += 5

        # Recency scoring
        if lead.last_contacted:
            now = datetime.now(timezone.utc)

            # Make last_contacted timezone-aware if it isn't
            last_contacted = lead.last_contacted
            if last_contacted.tzinfo is None:
                last_contacted = last_contacted.replace(tzinfo=timezone.utc)

            days_since = (now - last_contacted).days

            if days_since <= 7:
                score += 10  # Very recent
            elif days_since <= 30:
                score += 7  # Recent
            elif days_since <= 90:
                score += 3  # Somewhat recent

        # Last activity date bonus
        if lead.last_activity_date:
            now = datetime.now(timezone.utc)
            last_activity = lead.last_activity_date
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)

            days_since = (now - last_activity).days
            if days_since <= 14:
                score += 5  # Recent activity

        return min(score, 25)

    def _assign_tier(self, total_score: int) -> LeadTier:
        """
        Assign lead tier based on total score.

        Tiers:
        - Hot: 85+ points
        - Warm: 70-84 points
        - Nurture: 50-69 points
        - Cold: <50 points
        """
        if total_score >= 85:
            return LeadTier.HOT
        elif total_score >= 70:
            return LeadTier.WARM
        elif total_score >= 50:
            return LeadTier.NURTURE
        else:
            return LeadTier.COLD


# Singleton instance
lead_scorer = LeadScorer()
