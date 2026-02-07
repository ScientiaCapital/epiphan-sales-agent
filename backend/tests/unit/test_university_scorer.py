"""Tests for university account scoring service.

Tests the 5-dimension scoring model:
1. Carnegie Classification (25%)
2. Enrollment Size (20%)
3. Technology Signals (20%)
4. Engagement Level (15%)
5. Strategic Fit (15%)

And tier assignment: A (75+), B (50-74), C (30-49), D (<30)
"""


from app.data.university_schemas import (
    AccountTier,
    AthleticDivision,
    CarnegieClassification,
    InstitutionType,
    UniversityAccountCreate,
)
from app.services.scoring.university_scorer import (
    TIER_A_THRESHOLD,
    TIER_B_THRESHOLD,
    TIER_C_THRESHOLD,
    WEIGHT_CARNEGIE,
    WEIGHT_ENGAGEMENT,
    WEIGHT_ENROLLMENT,
    WEIGHT_STRATEGIC,
    WEIGHT_TECHNOLOGY,
    assign_account_tier,
    classify_carnegie,
    classify_engagement,
    classify_enrollment,
    classify_strategic_fit,
    classify_technology,
    university_scorer,
)

# =============================================================================
# Carnegie Classification Tests
# =============================================================================


class TestClassifyCarnegie:
    """Tests for Carnegie Classification dimension (25% weight)."""

    def test_r1_scores_highest(self) -> None:
        cat, score, reason = classify_carnegie(CarnegieClassification.R1)
        assert score == 10
        assert cat == "R1"
        assert "Very High Research" in reason

    def test_r2_scores_8(self) -> None:
        cat, score, reason = classify_carnegie(CarnegieClassification.R2)
        assert score == 8
        assert cat == "R2"

    def test_doctoral_professional_scores_7(self) -> None:
        cat, score, _ = classify_carnegie(CarnegieClassification.D_PU)
        assert score == 7

    def test_masters_large_scores_6(self) -> None:
        _, score, _ = classify_carnegie(CarnegieClassification.M1)
        assert score == 6

    def test_masters_medium_scores_5(self) -> None:
        _, score, _ = classify_carnegie(CarnegieClassification.M2)
        assert score == 5

    def test_masters_small_scores_4(self) -> None:
        _, score, _ = classify_carnegie(CarnegieClassification.M3)
        assert score == 4

    def test_baccalaureate_scores_3(self) -> None:
        _, score, _ = classify_carnegie(CarnegieClassification.BACCALAUREATE)
        assert score == 3

    def test_associate_scores_2(self) -> None:
        _, score, _ = classify_carnegie(CarnegieClassification.ASSOCIATE)
        assert score == 2

    def test_special_focus_scores_4(self) -> None:
        _, score, _ = classify_carnegie(CarnegieClassification.SPECIAL_FOCUS)
        assert score == 4

    def test_none_returns_2(self) -> None:
        cat, score, reason = classify_carnegie(None)
        assert score == 2
        assert "not available" in reason

    def test_all_classifications_return_valid_scores(self) -> None:
        for cls in CarnegieClassification:
            _, score, _ = classify_carnegie(cls)
            assert 0 <= score <= 10


# =============================================================================
# Enrollment Size Tests
# =============================================================================


class TestClassifyEnrollment:
    """Tests for Enrollment Size dimension (20% weight)."""

    def test_very_large_30k_plus(self) -> None:
        cat, score, reason = classify_enrollment(45000)
        assert score == 10
        assert cat == "Very Large"
        assert "45,000" in reason

    def test_large_15k_to_30k(self) -> None:
        cat, score, _ = classify_enrollment(20000)
        assert score == 8
        assert cat == "Large"

    def test_medium_5k_to_15k(self) -> None:
        cat, score, _ = classify_enrollment(8000)
        assert score == 6
        assert cat == "Medium"

    def test_small_1k_to_5k(self) -> None:
        cat, score, _ = classify_enrollment(2000)
        assert score == 4
        assert cat == "Small"

    def test_very_small_under_1k(self) -> None:
        cat, score, _ = classify_enrollment(500)
        assert score == 2
        assert cat == "Very Small"

    def test_none_enrollment(self) -> None:
        cat, score, reason = classify_enrollment(None)
        assert score == 0
        assert "not available" in reason

    def test_boundary_30k(self) -> None:
        _, score, _ = classify_enrollment(30000)
        assert score == 10

    def test_boundary_15k(self) -> None:
        _, score, _ = classify_enrollment(15000)
        assert score == 8

    def test_boundary_5k(self) -> None:
        _, score, _ = classify_enrollment(5000)
        assert score == 6

    def test_boundary_1k(self) -> None:
        _, score, _ = classify_enrollment(1000)
        assert score == 4


# =============================================================================
# Technology Signals Tests
# =============================================================================


class TestClassifyTechnology:
    """Tests for Technology Signals dimension (20% weight)."""

    def test_panopto_competitor_scores_10(self) -> None:
        cat, score, _ = classify_technology(None, "Panopto", None, None)
        assert score == 10
        assert cat == "Competitor"

    def test_kaltura_competitor_scores_10(self) -> None:
        _, score, _ = classify_technology(None, "Kaltura", None, None)
        assert score == 10

    def test_mediasite_competitor_scores_10(self) -> None:
        _, score, _ = classify_technology(None, "Mediasite", None, None)
        assert score == 10

    def test_canvas_lms_scores_8(self) -> None:
        cat, score, _ = classify_technology("Canvas", None, None, None)
        assert score == 8
        assert cat == "LMS"

    def test_blackboard_lms_scores_8(self) -> None:
        _, score, _ = classify_technology("Blackboard", None, None, None)
        assert score == 8

    def test_crestron_av_scores_7(self) -> None:
        _, score, _ = classify_technology(None, None, "Crestron", None)
        assert score == 7

    def test_no_tech_data_scores_3(self) -> None:
        cat, score, reason = classify_technology(None, None, None, None)
        assert score == 3
        assert cat == "No signals"

    def test_tech_stack_with_competitor(self) -> None:
        _, score, _ = classify_technology(None, None, None, ["panopto", "zoom"])
        assert score == 10

    def test_tech_stack_with_lms(self) -> None:
        _, score, _ = classify_technology(None, None, None, ["canvas", "slack"])
        assert score == 8

    def test_competitor_takes_priority_over_lms(self) -> None:
        """Competitor video platform should score higher than LMS."""
        _, score, _ = classify_technology("Canvas", "Panopto", None, None)
        assert score == 10

    def test_unknown_video_platform_scores_7(self) -> None:
        """A video platform we don't recognize is still a signal."""
        _, score, _ = classify_technology(None, "SomeUnknownPlatform", None, None)
        assert score == 7


# =============================================================================
# Engagement Level Tests
# =============================================================================


class TestClassifyEngagement:
    """Tests for Engagement Level dimension (15% weight)."""

    def test_existing_customer_scores_10(self) -> None:
        cat, score, _ = classify_engagement(
            contact_count=5, decision_maker_count=2,
            is_existing_customer=True, has_active_opportunity=False,
        )
        assert score == 10
        assert cat == "Existing Customer"

    def test_active_opportunity_scores_9(self) -> None:
        _, score, _ = classify_engagement(
            contact_count=3, decision_maker_count=1,
            is_existing_customer=False, has_active_opportunity=True,
        )
        assert score == 9

    def test_has_decision_maker_scores_7(self) -> None:
        _, score, reason = classify_engagement(
            contact_count=3, decision_maker_count=2,
            is_existing_customer=False, has_active_opportunity=False,
        )
        assert score == 7
        assert "decision-maker" in reason

    def test_has_contacts_no_dm_scores_4(self) -> None:
        _, score, _ = classify_engagement(
            contact_count=5, decision_maker_count=0,
            is_existing_customer=False, has_active_opportunity=False,
        )
        assert score == 4

    def test_no_contacts_scores_0(self) -> None:
        _, score, reason = classify_engagement(
            contact_count=0, decision_maker_count=0,
            is_existing_customer=False, has_active_opportunity=False,
        )
        assert score == 0
        assert "No contacts" in reason

    def test_customer_overrides_contacts(self) -> None:
        """Existing customer should score 10 even with zero contacts (data issue)."""
        _, score, _ = classify_engagement(
            contact_count=0, decision_maker_count=0,
            is_existing_customer=True, has_active_opportunity=False,
        )
        assert score == 10


# =============================================================================
# Strategic Fit Tests
# =============================================================================


class TestClassifyStrategicFit:
    """Tests for Strategic Fit dimension (15% weight)."""

    def test_public_r1_d1_scores_highest(self) -> None:
        """Public R1 with D1 athletics = ideal target."""
        cat, score, _ = classify_strategic_fit(
            InstitutionType.PUBLIC,
            AthleticDivision.NCAA_D1,
            CarnegieClassification.R1,
        )
        assert score == 10  # 4 + 4 + 2 = 10 (capped)
        assert cat == "High Fit"

    def test_public_d2(self) -> None:
        _, score, _ = classify_strategic_fit(
            InstitutionType.PUBLIC,
            AthleticDivision.NCAA_D2,
            None,
        )
        assert score == 7  # 4 + 3 = 7

    def test_private_nonprofit(self) -> None:
        _, score, _ = classify_strategic_fit(
            InstitutionType.PRIVATE_NONPROFIT,
            AthleticDivision.NONE,
            None,
        )
        assert score == 3  # 3 + 0 = 3

    def test_private_for_profit(self) -> None:
        _, score, _ = classify_strategic_fit(
            InstitutionType.PRIVATE_FOR_PROFIT,
            AthleticDivision.NONE,
            None,
        )
        assert score == 1

    def test_no_data(self) -> None:
        cat, score, reason = classify_strategic_fit(None, None, None)
        assert score == 2
        assert "Insufficient" in reason

    def test_r1_bonus(self) -> None:
        """R1/R2 get +2 for multi-department potential."""
        _, score_r1, _ = classify_strategic_fit(
            InstitutionType.PUBLIC, None, CarnegieClassification.R1,
        )
        _, score_m1, _ = classify_strategic_fit(
            InstitutionType.PUBLIC, None, CarnegieClassification.M1,
        )
        assert score_r1 > score_m1


# =============================================================================
# Tier Assignment Tests
# =============================================================================


class TestAssignAccountTier:
    """Tests for tier thresholds."""

    def test_a_tier_at_threshold(self) -> None:
        assert assign_account_tier(TIER_A_THRESHOLD) == AccountTier.A

    def test_a_tier_above(self) -> None:
        assert assign_account_tier(85.0) == AccountTier.A

    def test_b_tier_at_threshold(self) -> None:
        assert assign_account_tier(TIER_B_THRESHOLD) == AccountTier.B

    def test_b_tier_below_a(self) -> None:
        assert assign_account_tier(74.9) == AccountTier.B

    def test_c_tier_at_threshold(self) -> None:
        assert assign_account_tier(TIER_C_THRESHOLD) == AccountTier.C

    def test_c_tier_below_b(self) -> None:
        assert assign_account_tier(49.9) == AccountTier.C

    def test_d_tier_below_c(self) -> None:
        assert assign_account_tier(29.9) == AccountTier.D

    def test_d_tier_zero(self) -> None:
        assert assign_account_tier(0.0) == AccountTier.D

    def test_a_tier_max(self) -> None:
        assert assign_account_tier(100.0) == AccountTier.A


# =============================================================================
# Full Scoring Integration Tests
# =============================================================================


class TestUniversityScorerIntegration:
    """Integration tests for the full scoring pipeline."""

    def test_ideal_r1_university(self) -> None:
        """R1 + large enrollment + competitor tech + decision-maker = A-tier."""
        account = UniversityAccountCreate(
            name="University of Michigan",
            carnegie_classification=CarnegieClassification.R1,
            institution_type=InstitutionType.PUBLIC,
            enrollment=47000,
            lms_platform="Canvas",
            video_platform="Panopto",
            athletic_division=AthleticDivision.NCAA_D1,
            contact_count=3,
            decision_maker_count=1,
        )
        total, tier, breakdown, missing = university_scorer.score_account(account)
        assert tier == AccountTier.A
        assert total >= TIER_A_THRESHOLD
        assert breakdown.carnegie_classification.raw_score == 10
        assert breakdown.enrollment_size.raw_score == 10
        assert breakdown.technology_signals.raw_score == 10
        assert not missing  # All data present

    def test_small_community_college(self) -> None:
        """Associate + tiny enrollment + no tech = D-tier."""
        account = UniversityAccountCreate(
            name="Small County CC",
            carnegie_classification=CarnegieClassification.ASSOCIATE,
            institution_type=InstitutionType.PUBLIC,
            enrollment=800,
        )
        total, tier, breakdown, missing = university_scorer.score_account(account)
        assert tier == AccountTier.D
        assert total < TIER_C_THRESHOLD
        assert "contacts" in missing

    def test_mid_tier_university(self) -> None:
        """M1 + moderate enrollment + LMS = B-tier range."""
        account = UniversityAccountCreate(
            name="Regional State University",
            carnegie_classification=CarnegieClassification.M1,
            institution_type=InstitutionType.PUBLIC,
            enrollment=12000,
            lms_platform="Blackboard",
            athletic_division=AthleticDivision.NCAA_D2,
        )
        total, tier, breakdown, missing = university_scorer.score_account(account)
        assert tier in (AccountTier.B, AccountTier.C)
        assert TIER_C_THRESHOLD <= total < TIER_A_THRESHOLD

    def test_missing_data_reduces_score(self) -> None:
        """Account with no data should score very low."""
        account = UniversityAccountCreate(name="Unknown University")
        total, tier, _, missing = university_scorer.score_account(account)
        assert tier == AccountTier.D
        assert len(missing) > 0

    def test_weights_sum_to_100(self) -> None:
        """Verify scoring weights total 100%."""
        total_weight = (
            WEIGHT_CARNEGIE
            + WEIGHT_ENROLLMENT
            + WEIGHT_TECHNOLOGY
            + WEIGHT_ENGAGEMENT
            + WEIGHT_STRATEGIC
        )
        assert abs(total_weight - 1.0) < 0.001

    def test_max_possible_score(self) -> None:
        """Perfect scores across all dimensions should reach 100."""
        account = UniversityAccountCreate(
            name="Perfect University",
            carnegie_classification=CarnegieClassification.R1,
            institution_type=InstitutionType.PUBLIC,
            enrollment=50000,
            video_platform="Panopto",
            lms_platform="Canvas",
            athletic_division=AthleticDivision.NCAA_D1,
            is_existing_customer=True,
            contact_count=5,
            decision_maker_count=2,
        )
        total, tier, _, _ = university_scorer.score_account(account)
        assert tier == AccountTier.A
        assert total == 100.0

    def test_existing_customer_boosts_score(self) -> None:
        """Same account with vs without existing customer status."""
        base = {
            "name": "Test University",
            "carnegie_classification": CarnegieClassification.R2,
            "institution_type": InstitutionType.PUBLIC,
            "enrollment": 20000,
        }
        without = UniversityAccountCreate(**base, is_existing_customer=False)
        with_customer = UniversityAccountCreate(**base, is_existing_customer=True)

        score_without, _, _, _ = university_scorer.score_account(without)
        score_with, _, _, _ = university_scorer.score_account(with_customer)
        assert score_with > score_without

    def test_competitor_tech_boosts_score(self) -> None:
        """Competitor video platform should significantly boost tech score."""
        base = {
            "name": "Test University",
            "carnegie_classification": CarnegieClassification.R2,
            "enrollment": 15000,
        }
        no_tech = UniversityAccountCreate(**base)
        with_competitor = UniversityAccountCreate(**base, video_platform="Kaltura")

        score_no, _, _, _ = university_scorer.score_account(no_tech)
        score_comp, _, _, _ = university_scorer.score_account(with_competitor)
        assert score_comp > score_no


# =============================================================================
# Next Action Tests
# =============================================================================


class TestDetermineNextAction:
    """Tests for recommended next actions."""

    def test_a_tier_no_contacts(self) -> None:
        account = UniversityAccountCreate(
            name="Big R1", contact_count=0, decision_maker_count=0
        )
        action = university_scorer.determine_next_action(
            AccountTier.A, ["contacts"], account
        )
        assert "LinkedIn Sales Navigator" in action
        assert "Director AV" in action

    def test_a_tier_no_decision_maker(self) -> None:
        account = UniversityAccountCreate(
            name="Big R1", contact_count=5, decision_maker_count=0
        )
        action = university_scorer.determine_next_action(
            AccountTier.A, [], account
        )
        assert "decision-maker" in action

    def test_a_tier_ready(self) -> None:
        account = UniversityAccountCreate(
            name="Big R1", contact_count=3, decision_maker_count=1
        )
        action = university_scorer.determine_next_action(
            AccountTier.A, [], account
        )
        assert "call brief" in action

    def test_b_tier_no_contacts(self) -> None:
        account = UniversityAccountCreate(
            name="Medium U", contact_count=0, decision_maker_count=0
        )
        action = university_scorer.determine_next_action(
            AccountTier.B, ["contacts"], account
        )
        assert "Clay" in action

    def test_c_tier_nurture(self) -> None:
        account = UniversityAccountCreate(name="Small U")
        action = university_scorer.determine_next_action(
            AccountTier.C, [], account
        )
        assert "nurture" in action

    def test_d_tier_low_priority(self) -> None:
        account = UniversityAccountCreate(name="Tiny CC")
        action = university_scorer.determine_next_action(
            AccountTier.D, [], account
        )
        assert "Low priority" in action


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests for scoring robustness."""

    def test_zero_enrollment(self) -> None:
        _, score, _ = classify_enrollment(0)
        assert score == 2  # Very small

    def test_massive_enrollment(self) -> None:
        _, score, _ = classify_enrollment(200000)
        assert score == 10

    def test_empty_tech_stack(self) -> None:
        _, score, _ = classify_technology(None, None, None, [])
        assert score == 3

    def test_case_insensitive_video_platform(self) -> None:
        """Video platform matching should be case-insensitive."""
        _, score, _ = classify_technology(None, "PANOPTO", None, None)
        assert score == 10

    def test_case_insensitive_lms(self) -> None:
        _, score, _ = classify_technology("CANVAS", None, None, None)
        assert score == 8

    def test_multiple_tech_signals(self) -> None:
        """Multiple tech signals should use highest score."""
        _, score, _ = classify_technology("Canvas", "Panopto", "Crestron", None)
        assert score == 10  # Competitor takes priority
