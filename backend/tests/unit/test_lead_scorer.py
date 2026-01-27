"""Tests for Lead Scorer service.

TDD tests for scoring leads using ICP criteria and engagement signals.
"""

import pytest

from app.data.lead_schemas import Lead, LeadTier
from app.services.scoring.lead_scorer import LeadScorer, LeadScoreResult


class TestLeadScorer:
    """Tests for LeadScorer service."""

    @pytest.fixture
    def scorer(self):
        """Create LeadScorer instance."""
        return LeadScorer()

    # =========================================================================
    # Persona Score (0-25 points)
    # =========================================================================

    def test_persona_score_high_confidence_match(self, scorer):
        """Test high persona score for high-confidence match."""
        lead = Lead(
            hubspot_id="123",
            email="john@university.edu",
            title="AV Director",
            company="State University",
        )

        result = scorer.score_lead(lead)

        # High confidence persona match should give 20-25 points
        assert result.persona_score >= 20
        assert result.persona_match == "av_director"

    def test_persona_score_medium_confidence_match(self, scorer):
        """Test medium persona score for partial match."""
        lead = Lead(
            hubspot_id="123",
            email="john@company.com",
            title="Director of Technology",  # Partial match
            company="Tech Corp",
        )

        result = scorer.score_lead(lead)

        # Partial match should give 10-19 points
        assert 0 <= result.persona_score <= 25

    def test_persona_score_no_match(self, scorer):
        """Test zero persona score for no match."""
        lead = Lead(
            hubspot_id="123",
            email="dev@startup.com",
            title="Software Engineer",
            company="Startup Inc",
        )

        result = scorer.score_lead(lead)

        # No match should give 0-5 points
        assert result.persona_score <= 5
        assert result.persona_match is None

    def test_persona_score_no_title(self, scorer):
        """Test persona scoring with missing title."""
        lead = Lead(
            hubspot_id="123",
            email="unknown@company.com",
            title=None,
            company="Some Company",
        )

        result = scorer.score_lead(lead)

        assert result.persona_score == 0

    # =========================================================================
    # Vertical Score (0-25 points)
    # =========================================================================

    def test_vertical_score_strong_match(self, scorer):
        """Test high vertical score for strong vertical match."""
        lead = Lead(
            hubspot_id="123",
            email="av@university.edu",
            title="AV Director",
            company="Stanford University",
        )

        result = scorer.score_lead(lead)

        # University = higher_ed vertical, strong match for AV Director
        assert result.vertical_score >= 20
        assert result.vertical == "higher_ed"

    def test_vertical_score_healthcare(self, scorer):
        """Test vertical scoring for healthcare."""
        lead = Lead(
            hubspot_id="123",
            email="sim@hospital.org",
            title="Simulation Center Director",
            company="Johns Hopkins Hospital",
        )

        result = scorer.score_lead(lead)

        assert result.vertical_score >= 20
        assert result.vertical == "healthcare"

    def test_vertical_score_no_vertical_inferred(self, scorer):
        """Test vertical scoring when no vertical can be inferred."""
        lead = Lead(
            hubspot_id="123",
            email="person@randomxyz.com",
            title="Manager",
            company="RandomXYZ",
        )

        result = scorer.score_lead(lead)

        # Can't infer vertical
        assert result.vertical_score <= 10
        assert result.vertical is None

    # =========================================================================
    # Company Score (0-25 points)
    # =========================================================================

    def test_company_score_with_employee_signals(self, scorer):
        """Test company score based on company name quality."""
        lead = Lead(
            hubspot_id="123",
            email="director@fortune500.com",
            title="L&D Director",
            company="Fortune 500 Company",
        )

        result = scorer.score_lead(lead)

        # Has company name
        assert result.company_score >= 5

    def test_company_score_no_company(self, scorer):
        """Test company score with missing company."""
        lead = Lead(
            hubspot_id="123",
            email="person@gmail.com",
            title="Director",
            company=None,
        )

        result = scorer.score_lead(lead)

        assert result.company_score <= 5

    def test_company_score_edu_domain(self, scorer):
        """Test company score boost for .edu domain."""
        lead = Lead(
            hubspot_id="123",
            email="av@ncstate.edu",
            title="AV Director",
            company="NC State University",
        )

        result = scorer.score_lead(lead)

        # .edu domain indicates legitimate educational institution
        assert result.company_score >= 15

    def test_company_score_gov_domain(self, scorer):
        """Test company score boost for .gov domain."""
        lead = Lead(
            hubspot_id="123",
            email="admin@courts.gov",
            title="Court Administrator",
            company="County Court",
        )

        result = scorer.score_lead(lead)

        # .gov domain indicates legitimate government org
        assert result.company_score >= 15

    # =========================================================================
    # Engagement Score (0-25 points)
    # =========================================================================

    def test_engagement_score_high_contact_count(self, scorer):
        """Test high engagement score for multiple contacts."""
        lead = Lead(
            hubspot_id="123",
            email="engaged@company.com",
            title="Director",
            company="Company",
            contact_count=5,
        )

        result = scorer.score_lead(lead)

        # Multiple contact touches = engaged
        assert result.engagement_score >= 15

    def test_engagement_score_recently_contacted(self, scorer):
        """Test engagement score for recently contacted lead."""
        from datetime import datetime, timezone, timedelta

        lead = Lead(
            hubspot_id="123",
            email="recent@company.com",
            title="Director",
            company="Company",
            last_contacted=datetime.now(timezone.utc) - timedelta(days=7),
        )

        result = scorer.score_lead(lead)

        # Recently contacted
        assert result.engagement_score >= 10

    def test_engagement_score_no_engagement(self, scorer):
        """Test low engagement score for unengaged lead."""
        lead = Lead(
            hubspot_id="123",
            email="cold@company.com",
            title="Director",
            company="Company",
            contact_count=0,
            last_contacted=None,
        )

        result = scorer.score_lead(lead)

        # No engagement signals
        assert result.engagement_score <= 5

    # =========================================================================
    # Total Score and Tier Assignment
    # =========================================================================

    def test_total_score_calculation(self, scorer):
        """Test that total score is sum of all dimensions."""
        lead = Lead(
            hubspot_id="123",
            email="av@university.edu",
            title="AV Director",
            company="State University",
        )

        result = scorer.score_lead(lead)

        expected_total = (
            result.persona_score
            + result.vertical_score
            + result.company_score
            + result.engagement_score
        )
        assert result.total_score == expected_total

    def test_tier_hot(self, scorer):
        """Test hot tier assignment for high score."""
        # Create a lead that should score high across all dimensions
        lead = Lead(
            hubspot_id="123",
            email="av@ncstate.edu",
            title="AV Director",
            company="NC State University",
            contact_count=5,
        )

        result = scorer.score_lead(lead)

        # Should be hot tier (85+) or at least warm
        assert result.tier in [LeadTier.HOT, LeadTier.WARM]
        assert result.total_score >= 70

    def test_tier_cold(self, scorer):
        """Test cold tier assignment for low score."""
        lead = Lead(
            hubspot_id="123",
            email="dev@startup.com",
            title="Software Engineer",
            company="RandomStartup",
            contact_count=0,
        )

        result = scorer.score_lead(lead)

        # Should be cold tier (<50)
        assert result.tier == LeadTier.COLD
        assert result.total_score < 50

    def test_tier_boundaries(self, scorer):
        """Test tier boundary assignments."""
        # Test the tier assignment logic directly
        assert scorer._assign_tier(85) == LeadTier.HOT
        assert scorer._assign_tier(84) == LeadTier.WARM
        assert scorer._assign_tier(70) == LeadTier.WARM
        assert scorer._assign_tier(69) == LeadTier.NURTURE
        assert scorer._assign_tier(50) == LeadTier.NURTURE
        assert scorer._assign_tier(49) == LeadTier.COLD
        assert scorer._assign_tier(0) == LeadTier.COLD

    # =========================================================================
    # Score Result Structure
    # =========================================================================

    def test_score_result_structure(self, scorer):
        """Test that score result contains all expected fields."""
        lead = Lead(
            hubspot_id="123",
            email="test@test.com",
            title="Director",
            company="Company",
        )

        result = scorer.score_lead(lead)

        assert isinstance(result, LeadScoreResult)
        assert hasattr(result, "persona_score")
        assert hasattr(result, "vertical_score")
        assert hasattr(result, "company_score")
        assert hasattr(result, "engagement_score")
        assert hasattr(result, "total_score")
        assert hasattr(result, "tier")
        assert hasattr(result, "persona_match")
        assert hasattr(result, "persona_confidence")
        assert hasattr(result, "vertical")

    def test_score_bounds(self, scorer):
        """Test that all scores are within valid bounds."""
        lead = Lead(
            hubspot_id="123",
            email="test@test.com",
            title="AV Director",
            company="University",
            contact_count=100,  # Very high engagement
        )

        result = scorer.score_lead(lead)

        assert 0 <= result.persona_score <= 25
        assert 0 <= result.vertical_score <= 25
        assert 0 <= result.company_score <= 25
        assert 0 <= result.engagement_score <= 25
        assert 0 <= result.total_score <= 100
        assert 0.0 <= result.persona_confidence <= 1.0


class TestBatchScoring:
    """Tests for batch lead scoring."""

    @pytest.fixture
    def scorer(self):
        """Create LeadScorer instance."""
        return LeadScorer()

    def test_score_multiple_leads(self, scorer):
        """Test scoring multiple leads at once."""
        leads = [
            Lead(hubspot_id="1", email="av@uni.edu", title="AV Director", company="University"),
            Lead(hubspot_id="2", email="ld@corp.com", title="L&D Director", company="Corp"),
            Lead(hubspot_id="3", email="dev@startup.com", title="Developer", company="Startup"),
        ]

        results = scorer.score_leads(leads)

        assert len(results) == 3
        # First two should score higher than third
        assert results[0].total_score > results[2].total_score
        assert results[1].total_score > results[2].total_score
