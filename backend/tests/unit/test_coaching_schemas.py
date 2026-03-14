"""Tests for coaching intelligence types — MEDDIC, DISC, Call Stage FSM, Partner Progress."""


from app.data.coaching_schemas import (
    TRANSITIONS,
    AccumulatedState,
    AudienceType,
    BookingSignal,
    BuyerDisc,
    CallStage,
    CoachingFocus,
    CoachingResponse,
    CoachingType,
    CoachingUrgency,
    CrossCallContext,
    CurrentState,
    CustomerSentiment,
    DiscConfidence,
    DiscType,
    MeddicCriterion,
    MeddicScore,
    MeddicTracker,
    NextGoal,
    ObjectionType,
    PartnerFamiliarity,
    PartnerProgress,
    SpecInStatus,
)

# =============================================================================
# CallStage
# =============================================================================


class TestCallStage:
    def test_all_stages_exist(self) -> None:
        assert len(CallStage) == 9

    def test_stage_values(self) -> None:
        assert CallStage.OPENING.value == "opening"
        assert CallStage.OBJECTION_HANDLING.value == "objection_handling"
        assert CallStage.RENEWAL.value == "renewal"

    def test_level_ordering(self) -> None:
        assert CallStage.OPENING.level == 0
        assert CallStage.DISCOVERY.level == 1
        assert CallStage.QUALIFICATION.level == 2
        assert CallStage.DEMO.level == 3
        assert CallStage.NEGOTIATION.level == 4
        assert CallStage.OBJECTION_HANDLING.level == 5
        assert CallStage.CLOSING.level == 6

    def test_lateral_stages_level_zero(self) -> None:
        assert CallStage.SUPPORT.level == 0
        assert CallStage.RENEWAL.level == 0

    def test_forward_transition_allowed(self) -> None:
        assert CallStage.OPENING.can_transition_to(CallStage.DISCOVERY)
        assert CallStage.OPENING.can_transition_to(CallStage.CLOSING)
        assert CallStage.DISCOVERY.can_transition_to(CallStage.QUALIFICATION)

    def test_same_stage_transition_allowed(self) -> None:
        assert CallStage.DEMO.can_transition_to(CallStage.DEMO)
        assert CallStage.OPENING.can_transition_to(CallStage.OPENING)

    def test_backward_transition_blocked(self) -> None:
        assert not CallStage.DEMO.can_transition_to(CallStage.OPENING)
        assert not CallStage.DEMO.can_transition_to(CallStage.DISCOVERY)
        assert not CallStage.DEMO.can_transition_to(CallStage.QUALIFICATION)

    def test_lateral_always_reachable(self) -> None:
        assert CallStage.OPENING.can_transition_to(CallStage.OBJECTION_HANDLING)
        assert CallStage.DEMO.can_transition_to(CallStage.OBJECTION_HANDLING)
        assert CallStage.CLOSING.can_transition_to(CallStage.OBJECTION_HANDLING)
        assert CallStage.DISCOVERY.can_transition_to(CallStage.SUPPORT)
        assert CallStage.NEGOTIATION.can_transition_to(CallStage.RENEWAL)

    def test_support_renewal_can_go_anywhere(self) -> None:
        assert CallStage.SUPPORT.can_transition_to(CallStage.OPENING)
        assert CallStage.SUPPORT.can_transition_to(CallStage.CLOSING)
        assert CallStage.RENEWAL.can_transition_to(CallStage.DEMO)

    def test_validated_transition_forward(self) -> None:
        stage, wm = CallStage.QUALIFICATION.validated_transition(CallStage.DEMO, 2)
        assert stage == CallStage.DEMO
        assert wm == 3

    def test_validated_transition_blocks_regression(self) -> None:
        stage, wm = CallStage.DEMO.validated_transition(CallStage.OPENING, 3)
        assert stage == CallStage.DEMO  # blocked
        assert wm == 3

    def test_validated_transition_lateral_no_watermark_update(self) -> None:
        stage, wm = CallStage.DISCOVERY.validated_transition(CallStage.SUPPORT, 1)
        assert stage == CallStage.SUPPORT
        assert wm == 1  # watermark unchanged

    def test_validated_transition_watermark_survives_lateral(self) -> None:
        stage, wm = CallStage.OPENING.validated_transition(CallStage.DISCOVERY, 0)
        assert stage == CallStage.DISCOVERY
        assert wm == 1

        stage2, wm2 = stage.validated_transition(CallStage.SUPPORT, wm)
        assert stage2 == CallStage.SUPPORT
        assert wm2 == 1

        # Can't go to Opening (level 0) after reaching Discovery (level 1)
        stage3, wm3 = stage2.validated_transition(CallStage.OPENING, wm2)
        assert stage3 == CallStage.SUPPORT  # blocked
        assert wm3 == 1

        # But forward from Support is fine
        stage4, wm4 = stage2.validated_transition(CallStage.DEMO, wm2)
        assert stage4 == CallStage.DEMO
        assert wm4 == 3

    def test_transition_matrix_dimensions(self) -> None:
        assert len(TRANSITIONS) == 9
        for row in TRANSITIONS:
            assert len(row) == 9

    def test_index_matches_enum_order(self) -> None:
        for i, stage in enumerate(CallStage):
            assert stage.stage_index == i


# =============================================================================
# Enums
# =============================================================================


class TestEnums:
    def test_customer_sentiment_count(self) -> None:
        assert len(CustomerSentiment) == 8

    def test_coaching_type_values(self) -> None:
        assert CoachingType.WHISPER.value == "whisper"
        assert CoachingType.LISTEN.value == "listen"
        assert CoachingType.SILENCE.value == "silence"
        assert len(CoachingType) == 7

    def test_coaching_urgency(self) -> None:
        assert len(CoachingUrgency) == 3

    def test_coaching_focus(self) -> None:
        assert len(CoachingFocus) == 7

    def test_next_goal(self) -> None:
        assert len(NextGoal) == 7

    def test_objection_type(self) -> None:
        assert len(ObjectionType) == 7
        assert ObjectionType.NONE.value == "none"

    def test_booking_signal(self) -> None:
        assert len(BookingSignal) == 3
        assert BookingSignal.NONE.value == "none"
        assert BookingSignal.DIRECT.value == "direct"

    def test_disc_type(self) -> None:
        assert len(DiscType) == 5
        assert DiscType.UNKNOWN.value == "unknown"

    def test_disc_confidence_level(self) -> None:
        assert DiscConfidence.LOW.level == 0
        assert DiscConfidence.MEDIUM.level == 1
        assert DiscConfidence.HIGH.level == 2

    def test_audience_type(self) -> None:
        assert AudienceType.DIRECT_SALE.is_channel is False
        assert AudienceType.CHANNEL_PARTNER.is_channel is True


# =============================================================================
# MeddicCriterion
# =============================================================================


class TestMeddicCriterion:
    def test_default_unconfirmed(self) -> None:
        c = MeddicCriterion()
        assert c.confirmed is False
        assert c.evidence is None

    def test_confirm_sets_evidence(self) -> None:
        c = MeddicCriterion()
        c.confirm("Budget is $500k")
        assert c.confirmed is True
        assert c.evidence == "Budget is $500k"

    def test_confirm_monotonic_no_revert(self) -> None:
        c = MeddicCriterion()
        c.confirm("First evidence")
        assert c.confirmed is True

        # Calling confirm again doesn't change evidence
        c.confirm("Second evidence")
        assert c.evidence == "First evidence"

    def test_confirmed_stays_true(self) -> None:
        c = MeddicCriterion()
        c.confirm("evidence")
        # Can't manually set back (enforced by confirm method, not field)
        c.confirm("new evidence")
        assert c.confirmed is True


# =============================================================================
# MeddicScore
# =============================================================================


class TestMeddicScore:
    def test_default_score_zero(self) -> None:
        s = MeddicScore()
        assert s.score() == 0

    def test_partial_score(self) -> None:
        s = MeddicScore(metrics=True, identify_pain=True)
        assert s.score() == 2

    def test_full_score(self) -> None:
        s = MeddicScore(
            metrics=True, economic_buyer=True, decision_criteria=True,
            decision_process=True, identify_pain=True, champion=True,
        )
        assert s.score() == 6

    def test_gaps_returns_unconfirmed(self) -> None:
        s = MeddicScore(metrics=True, champion=True)
        gaps = s.gaps()
        assert "Metrics" not in gaps
        assert "Champion" not in gaps
        assert "Economic Buyer" in gaps
        assert len(gaps) == 4

    def test_values_order(self) -> None:
        s = MeddicScore(metrics=True)
        vals = s.values()
        assert vals[0] is True
        assert all(v is False for v in vals[1:])


# =============================================================================
# MeddicTracker
# =============================================================================


class TestMeddicTracker:
    def test_default_score_zero(self) -> None:
        t = MeddicTracker()
        assert t.score() == 0

    def test_confirm_updates_score(self) -> None:
        t = MeddicTracker()
        t.metrics.confirm("$500k budget")
        t.identify_pain.confirm("Unreliable lecture capture")
        assert t.score() == 2

    def test_gaps(self) -> None:
        t = MeddicTracker()
        t.metrics.confirm("ev")
        gaps = t.gaps()
        assert "Metrics" not in gaps
        assert len(gaps) == 5

    def test_to_score(self) -> None:
        t = MeddicTracker()
        t.metrics.confirm("ev")
        t.champion.confirm("VP Engineering")
        s = t.to_score()
        assert s.metrics is True
        assert s.champion is True
        assert s.economic_buyer is False
        assert s.score() == 2

    def test_update_from_score_only_flips_true(self) -> None:
        t = MeddicTracker()
        t.metrics.confirm("original evidence")

        score = MeddicScore(metrics=False, identify_pain=True)
        t.update_from_score(score, "new evidence")

        # metrics stays confirmed (can't revert)
        assert t.metrics.confirmed is True
        assert t.metrics.evidence == "original evidence"
        # identify_pain newly confirmed
        assert t.identify_pain.confirmed is True
        assert t.identify_pain.evidence == "new evidence"

    def test_criteria_returns_all_six(self) -> None:
        t = MeddicTracker()
        assert len(t.criteria()) == 6


# =============================================================================
# BuyerDisc
# =============================================================================


class TestBuyerDisc:
    def test_default_unknown(self) -> None:
        d = BuyerDisc()
        assert d.disc_type == DiscType.UNKNOWN
        assert d.confidence == DiscConfidence.LOW

    def test_merge_higher_first_detection(self) -> None:
        d = BuyerDisc()
        incoming = BuyerDisc(disc_type=DiscType.DOMINANT, confidence=DiscConfidence.LOW)
        d.merge_higher(incoming)
        assert d.disc_type == DiscType.DOMINANT
        assert d.confidence == DiscConfidence.LOW

    def test_merge_higher_increases_confidence(self) -> None:
        d = BuyerDisc(disc_type=DiscType.DOMINANT, confidence=DiscConfidence.LOW)
        incoming = BuyerDisc(disc_type=DiscType.STEADY, confidence=DiscConfidence.MEDIUM)
        d.merge_higher(incoming)
        assert d.disc_type == DiscType.STEADY
        assert d.confidence == DiscConfidence.MEDIUM

    def test_merge_equal_confidence_no_flicker(self) -> None:
        d = BuyerDisc(disc_type=DiscType.DOMINANT, confidence=DiscConfidence.LOW)
        incoming = BuyerDisc(disc_type=DiscType.INFLUENTIAL, confidence=DiscConfidence.LOW)
        d.merge_higher(incoming)
        assert d.disc_type == DiscType.DOMINANT  # stays — same confidence

    def test_merge_unknown_incoming_ignored(self) -> None:
        d = BuyerDisc(disc_type=DiscType.DOMINANT, confidence=DiscConfidence.MEDIUM)
        incoming = BuyerDisc(disc_type=DiscType.UNKNOWN, confidence=DiscConfidence.HIGH)
        d.merge_higher(incoming)
        assert d.disc_type == DiscType.DOMINANT  # Unknown incoming ignored


# =============================================================================
# PartnerProgress
# =============================================================================


class TestPartnerProgress:
    def test_default_score_zero(self) -> None:
        p = PartnerProgress()
        assert p.score() == 0

    def test_score_counts_active_fields(self) -> None:
        p = PartnerProgress(
            product_familiarity=PartnerFamiliarity.AWARE,
            active_projects=2,
            margin_discussed=True,
        )
        assert p.score() == 3

    def test_full_score(self) -> None:
        p = PartnerProgress(
            product_familiarity=PartnerFamiliarity.CERTIFIED,
            active_projects=5,
            displacement_opportunities=["Extron → Pearl"],
            spec_in_status=SpecInStatus.COMMITTED,
            margin_discussed=True,
            certification_interest=True,
        )
        assert p.score() == 6

    def test_gaps(self) -> None:
        p = PartnerProgress(product_familiarity=PartnerFamiliarity.AWARE)
        gaps = p.gaps()
        assert "Product Familiarity" not in gaps
        assert len(gaps) == 5

    def test_merge_advances_only(self) -> None:
        p = PartnerProgress(
            product_familiarity=PartnerFamiliarity.AWARE,
            active_projects=1,
        )
        incoming = PartnerProgress(
            product_familiarity=PartnerFamiliarity.FAMILIAR,
            active_projects=3,
            margin_discussed=True,
        )
        p.merge(incoming)
        assert p.product_familiarity == PartnerFamiliarity.FAMILIAR
        assert p.active_projects == 3
        assert p.margin_discussed is True

    def test_merge_no_regress(self) -> None:
        p = PartnerProgress(
            product_familiarity=PartnerFamiliarity.CERTIFIED,
            active_projects=5,
        )
        incoming = PartnerProgress(
            product_familiarity=PartnerFamiliarity.AWARE,
            active_projects=2,
        )
        p.merge(incoming)
        assert p.product_familiarity == PartnerFamiliarity.CERTIFIED
        assert p.active_projects == 5

    def test_merge_displacement_dedup(self) -> None:
        p = PartnerProgress(displacement_opportunities=["Extron → Pearl"])
        incoming = PartnerProgress(
            displacement_opportunities=["Extron → Pearl", "Crestron → Nexus"]
        )
        p.merge(incoming)
        assert len(p.displacement_opportunities) == 2
        assert "Crestron → Nexus" in p.displacement_opportunities

    def test_merge_displacement_cap(self) -> None:
        p = PartnerProgress(displacement_opportunities=[f"item{i}" for i in range(8)])
        incoming = PartnerProgress(displacement_opportunities=["overflow"])
        p.merge(incoming)
        assert len(p.displacement_opportunities) == 8  # capped


# =============================================================================
# PartnerFamiliarity / SpecInStatus
# =============================================================================


class TestPartnerFamiliarity:
    def test_level_ordering(self) -> None:
        assert PartnerFamiliarity.UNKNOWN.level == 0
        assert PartnerFamiliarity.AWARE.level == 1
        assert PartnerFamiliarity.FAMILIAR.level == 2
        assert PartnerFamiliarity.CERTIFIED.level == 3

    def test_merge_higher_advances(self) -> None:
        result = PartnerFamiliarity.AWARE.merge_higher(PartnerFamiliarity.CERTIFIED)
        assert result == PartnerFamiliarity.CERTIFIED

    def test_merge_higher_no_regress(self) -> None:
        result = PartnerFamiliarity.CERTIFIED.merge_higher(PartnerFamiliarity.UNKNOWN)
        assert result == PartnerFamiliarity.CERTIFIED


class TestSpecInStatus:
    def test_level_ordering(self) -> None:
        assert SpecInStatus.NONE.level == 0
        assert SpecInStatus.INTERESTED.level == 1
        assert SpecInStatus.COMMITTED.level == 2

    def test_merge_higher(self) -> None:
        result = SpecInStatus.NONE.merge_higher(SpecInStatus.COMMITTED)
        assert result == SpecInStatus.COMMITTED

    def test_merge_no_regress(self) -> None:
        result = SpecInStatus.COMMITTED.merge_higher(SpecInStatus.NONE)
        assert result == SpecInStatus.COMMITTED


# =============================================================================
# AccumulatedState
# =============================================================================


class TestAccumulatedState:
    def test_default_empty(self) -> None:
        acc = AccumulatedState()
        assert acc.meddic.score() == 0
        assert acc.disc.disc_type == DiscType.UNKNOWN

    def test_update_from_current_state(self) -> None:
        acc = AccumulatedState()
        cs = CurrentState(
            meddic=MeddicScore(metrics=True, identify_pain=True),
            buyer_disc=BuyerDisc(
                disc_type=DiscType.DOMINANT,
                confidence=DiscConfidence.MEDIUM,
            ),
        )
        acc.update_from_current_state(cs, "Budget $500k mentioned")
        assert acc.meddic.score() == 2
        assert acc.meddic.metrics.evidence == "Budget $500k mentioned"
        assert acc.disc.disc_type == DiscType.DOMINANT

    def test_monotonic_meddic(self) -> None:
        acc = AccumulatedState()
        cs1 = CurrentState(meddic=MeddicScore(metrics=True))
        acc.update_from_current_state(cs1, "ev1")
        assert acc.meddic.metrics.confirmed is True

        # Try to flip back
        cs2 = CurrentState(meddic=MeddicScore(metrics=False))
        acc.update_from_current_state(cs2, "ev2")
        assert acc.meddic.metrics.confirmed is True  # stays

    def test_monotonic_disc(self) -> None:
        acc = AccumulatedState()
        cs1 = CurrentState(
            buyer_disc=BuyerDisc(disc_type=DiscType.DOMINANT, confidence=DiscConfidence.LOW),
        )
        acc.update_from_current_state(cs1, "ev")

        # Equal confidence, different type — rejected
        cs2 = CurrentState(
            buyer_disc=BuyerDisc(disc_type=DiscType.INFLUENTIAL, confidence=DiscConfidence.LOW),
        )
        acc.update_from_current_state(cs2, "ev")
        assert acc.disc.disc_type == DiscType.DOMINANT  # stays


# =============================================================================
# CrossCallContext
# =============================================================================


class TestCrossCallContext:
    def test_default_empty(self) -> None:
        ctx = CrossCallContext()
        assert ctx.total_previous_calls == 0
        assert ctx.last_stage_reached is None

    def test_with_data(self) -> None:
        ctx = CrossCallContext(
            confirmed_pains=["Unreliable capture"],
            last_stage_reached="demo",
            total_previous_calls=3,
        )
        assert len(ctx.confirmed_pains) == 1
        assert ctx.total_previous_calls == 3


# =============================================================================
# CoachingResponse
# =============================================================================


class TestCoachingResponse:
    def test_default_values(self) -> None:
        r = CoachingResponse()
        assert r.coaching_type == CoachingType.WHISPER
        assert r.urgency == CoachingUrgency.MEDIUM
        assert r.booking_signal == BookingSignal.NONE

    def test_with_topics(self) -> None:
        r = CoachingResponse(
            response="Ask about budget",
            topics_added=["budget", "timeline"],
            objections_added=["price"],
        )
        assert len(r.topics_added) == 2
        assert len(r.objections_added) == 1
