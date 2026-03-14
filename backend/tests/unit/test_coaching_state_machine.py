"""Tests for coaching state machine — FSM transitions, state updates, invariants."""

import pytest

from app.data.coaching_schemas import (
    AccumulatedState,
    BookingSignal,
    BuyerDisc,
    CallHistoryEntry,
    CallStage,
    CoachingResponse,
    CoachingType,
    CurrentState,
    DiscConfidence,
    DiscType,
    MeddicScore,
    MeddicTracker,
)
from app.services.coaching.invariants import (
    StateSnapshot,
    check_invariants,
)
from app.services.coaching.state_machine import (
    apply_coaching_to_session,
    build_cross_call_context,
    update_accumulated_state,
)


# =============================================================================
# update_accumulated_state
# =============================================================================


class TestUpdateAccumulatedState:
    def test_meddic_only_flips_true(self) -> None:
        acc = AccumulatedState()
        cs = CurrentState(meddic=MeddicScore(metrics=True))
        coaching = CoachingResponse(summary_update="Customer mentioned $500k budget")
        update_accumulated_state(acc, cs, coaching)
        assert acc.meddic.metrics.confirmed is True
        assert acc.meddic.metrics.evidence == "Customer mentioned $500k budget"

        # Try to flip back
        cs2 = CurrentState(meddic=MeddicScore(metrics=False))
        coaching2 = CoachingResponse(summary_update="Different topic")
        update_accumulated_state(acc, cs2, coaching2)
        assert acc.meddic.metrics.confirmed is True
        assert acc.meddic.metrics.evidence == "Customer mentioned $500k budget"

    def test_disc_only_increases_confidence(self) -> None:
        acc = AccumulatedState()
        cs = CurrentState(
            buyer_disc=BuyerDisc(disc_type=DiscType.DOMINANT, confidence=DiscConfidence.LOW),
        )
        update_accumulated_state(acc, cs, CoachingResponse())
        assert acc.disc.disc_type == DiscType.DOMINANT

        # Equal confidence, different type — rejected
        cs2 = CurrentState(
            buyer_disc=BuyerDisc(disc_type=DiscType.INFLUENTIAL, confidence=DiscConfidence.LOW),
        )
        update_accumulated_state(acc, cs2, CoachingResponse())
        assert acc.disc.disc_type == DiscType.DOMINANT

        # Higher confidence — accepted
        cs3 = CurrentState(
            buyer_disc=BuyerDisc(disc_type=DiscType.STEADY, confidence=DiscConfidence.MEDIUM),
        )
        update_accumulated_state(acc, cs3, CoachingResponse())
        assert acc.disc.disc_type == DiscType.STEADY
        assert acc.disc.confidence == DiscConfidence.MEDIUM

    def test_evidence_from_rationale_fallback(self) -> None:
        acc = AccumulatedState()
        cs = CurrentState(meddic=MeddicScore(identify_pain=True))
        coaching = CoachingResponse(summary_update="", rationale="Buyer expressed frustration")
        update_accumulated_state(acc, cs, coaching)
        assert acc.meddic.identify_pain.evidence == "Buyer expressed frustration"

    def test_evidence_truncated(self) -> None:
        acc = AccumulatedState()
        cs = CurrentState(meddic=MeddicScore(metrics=True))
        long_summary = "x" * 200
        coaching = CoachingResponse(summary_update=long_summary)
        update_accumulated_state(acc, cs, coaching)
        assert len(acc.meddic.metrics.evidence or "") == 120


# =============================================================================
# apply_coaching_to_session
# =============================================================================


class TestApplyCoachingToSession:
    def test_appends_topics_deduped(self) -> None:
        meddic = MeddicTracker()
        topics: list[str] = ["budget"]
        objections: list[str] = []
        coaching = CoachingResponse(topics_added=["budget", "timeline"])
        apply_coaching_to_session(meddic, topics, objections, coaching)
        assert topics == ["budget", "timeline"]

    def test_appends_objections_deduped(self) -> None:
        meddic = MeddicTracker()
        topics: list[str] = []
        objections: list[str] = ["price"]
        coaching = CoachingResponse(objections_added=["price", "timing"])
        apply_coaching_to_session(meddic, topics, objections, coaching)
        assert objections == ["price", "timing"]

    def test_updates_meddic_with_current_state(self) -> None:
        meddic = MeddicTracker()
        cs = CurrentState(meddic=MeddicScore(metrics=True))
        coaching = CoachingResponse(summary_update="Budget confirmed")
        apply_coaching_to_session(meddic, [], [], coaching, current_state=cs)
        assert meddic.metrics.confirmed is True

    def test_returns_summary(self) -> None:
        meddic = MeddicTracker()
        coaching = CoachingResponse(summary_update="Call going well")
        result = apply_coaching_to_session(meddic, [], [], coaching)
        assert result == "Call going well"

    def test_returns_empty_when_no_summary(self) -> None:
        meddic = MeddicTracker()
        coaching = CoachingResponse()
        result = apply_coaching_to_session(meddic, [], [], coaching)
        assert result == ""


# =============================================================================
# build_cross_call_context
# =============================================================================


class TestBuildCrossCallContext:
    def test_empty_history(self) -> None:
        ctx = build_cross_call_context([])
        assert ctx.total_previous_calls == 0
        assert ctx.last_stage_reached is None
        assert ctx.recurring_topics == []

    def test_single_call(self) -> None:
        history = [
            CallHistoryEntry(
                id="1", date="2026-01-01",
                stage_reached="discovery",
                key_topics=["budget", "timeline"],
            ),
        ]
        ctx = build_cross_call_context(history)
        assert ctx.total_previous_calls == 1
        assert ctx.last_stage_reached == "discovery"
        assert ctx.recurring_topics == []  # need 2+ occurrences

    def test_recurring_topics(self) -> None:
        history = [
            CallHistoryEntry(id="1", date="2026-01-01", key_topics=["budget", "timeline"]),
            CallHistoryEntry(id="2", date="2026-01-05", key_topics=["budget", "security"]),
            CallHistoryEntry(id="3", date="2026-01-10", key_topics=["timeline", "integration"]),
        ]
        ctx = build_cross_call_context(history)
        assert ctx.total_previous_calls == 3
        assert "budget" in ctx.recurring_topics
        assert "timeline" in ctx.recurring_topics
        assert "security" not in ctx.recurring_topics

    def test_last_stage_from_most_recent_entry(self) -> None:
        history = [
            CallHistoryEntry(id="1", date="2026-01-01", stage_reached="demo"),
            CallHistoryEntry(id="2", date="2026-01-05", stage_reached="discovery"),
        ]
        ctx = build_cross_call_context(history)
        assert ctx.last_stage_reached == "discovery"  # most recent call's stage


# =============================================================================
# Invariant checking
# =============================================================================


class TestInvariants:
    def test_no_violations_on_valid_progression(self) -> None:
        prev = StateSnapshot.initial()
        next_snap = StateSnapshot(
            stage=CallStage.DISCOVERY,
            meddic_score=1,
            meddic_bits=[True, False, False, False, False, False],
            disc_confidence=0,
            booking_signal=BookingSignal.NONE,
            turn_count=1,
        )
        assert check_invariants(prev, next_snap) == []

    def test_catches_meddic_regression(self) -> None:
        prev = StateSnapshot(
            meddic_score=3,
            meddic_bits=[True, True, True, False, False, False],
        )
        next_snap = StateSnapshot(
            meddic_score=2,
            meddic_bits=[True, False, True, False, False, False],
            turn_count=1,
        )
        violations = check_invariants(prev, next_snap)
        rules = [v.rule for v in violations]
        assert "INV-1: MEDDIC monotonic" in rules
        assert "INV-2: MEDDIC criterion regression" in rules

    def test_catches_disc_confidence_drop(self) -> None:
        prev = StateSnapshot(disc_confidence=2)
        next_snap = StateSnapshot(disc_confidence=1, turn_count=1)
        violations = check_invariants(prev, next_snap)
        assert any(v.rule == "INV-3: DISC confidence monotonic" for v in violations)

    def test_catches_backward_stage(self) -> None:
        prev = StateSnapshot(stage=CallStage.DEMO)
        next_snap = StateSnapshot(stage=CallStage.OPENING, turn_count=1)
        violations = check_invariants(prev, next_snap)
        assert any(v.rule == "INV-4: stage transition valid" for v in violations)

    def test_catches_premature_booking(self) -> None:
        prev = StateSnapshot.initial()
        next_snap = StateSnapshot(
            stage=CallStage.DISCOVERY,
            meddic_score=1,
            meddic_bits=[True, False, False, False, False, False],
            booking_signal=BookingSignal.DIRECT,
            turn_count=1,
        )
        violations = check_invariants(prev, next_snap)
        assert any(v.rule == "INV-5: premature booking" for v in violations)

    def test_allows_booking_with_sufficient_meddic(self) -> None:
        prev = StateSnapshot.initial()
        next_snap = StateSnapshot(
            stage=CallStage.QUALIFICATION,
            meddic_score=4,
            meddic_bits=[True, True, True, True, False, False],
            booking_signal=BookingSignal.DIRECT,
            turn_count=1,
        )
        violations = check_invariants(prev, next_snap)
        assert not any(v.rule == "INV-5: premature booking" for v in violations)

    def test_catches_turn_count_decrease(self) -> None:
        prev = StateSnapshot(turn_count=5)
        next_snap = StateSnapshot(turn_count=3)
        violations = check_invariants(prev, next_snap)
        assert any(v.rule == "INV-6: turn count monotonic" for v in violations)

    def test_snapshot_capture(self) -> None:
        acc = AccumulatedState()
        acc.meddic.metrics.confirm("ev")
        acc.disc = BuyerDisc(disc_type=DiscType.DOMINANT, confidence=DiscConfidence.MEDIUM)
        snap = StateSnapshot.capture(
            acc, CallStage.DISCOVERY, BookingSignal.SOFT, turn_count=3,
        )
        assert snap.meddic_score == 1
        assert snap.disc_confidence == 1
        assert snap.stage == CallStage.DISCOVERY
        assert snap.turn_count == 3

    def test_lateral_stage_no_violation(self) -> None:
        prev = StateSnapshot(stage=CallStage.DEMO)
        next_snap = StateSnapshot(stage=CallStage.SUPPORT, turn_count=1)
        violations = check_invariants(prev, next_snap)
        assert not any(v.rule == "INV-4: stage transition valid" for v in violations)
