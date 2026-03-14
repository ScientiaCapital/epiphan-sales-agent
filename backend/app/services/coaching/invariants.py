"""State invariant checking — 6 rules for monotonic progression.

Ported from souffleur-core/src/invariants.rs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.data.coaching_schemas import (
    MEDDIC_CRITERION_NAMES,
    AccumulatedState,
    BookingSignal,
    CallStage,
)


@dataclass
class InvariantViolation:
    """Result of a failed invariant check."""

    rule: str
    detail: str


@dataclass
class StateSnapshot:
    """Lightweight snapshot of state for invariant checking."""

    stage: CallStage = CallStage.OPENING
    meddic_score: int = 0
    meddic_bits: list[bool] = field(default_factory=lambda: [False] * 6)
    disc_confidence: int = 0
    booking_signal: BookingSignal = BookingSignal.NONE
    turn_count: int = 0

    @staticmethod
    def capture(
        acc: AccumulatedState,
        stage: CallStage,
        booking_signal: BookingSignal,
        turn_count: int,
    ) -> StateSnapshot:
        """Capture snapshot from accumulated state + session state."""
        return StateSnapshot(
            stage=stage,
            meddic_score=acc.meddic.score(),
            meddic_bits=acc.meddic.values(),
            disc_confidence=acc.disc.confidence.level,
            booking_signal=booking_signal,
            turn_count=turn_count,
        )

    @staticmethod
    def initial() -> StateSnapshot:
        """Initial snapshot (turn 0)."""
        return StateSnapshot()


def check_invariants(prev: StateSnapshot, next_snap: StateSnapshot) -> list[InvariantViolation]:
    """Check all state invariants between two consecutive snapshots.

    Returns empty list if all invariants hold.
    """
    violations: list[InvariantViolation] = []

    # INV-1: MEDDIC score is monotonically non-decreasing
    if next_snap.meddic_score < prev.meddic_score:
        violations.append(InvariantViolation(
            rule="INV-1: MEDDIC monotonic",
            detail=f"MEDDIC decreased: {prev.meddic_score}/6 → {next_snap.meddic_score}/6",
        ))

    # INV-2: Individual MEDDIC criteria never regress (true→false)
    for i, name in enumerate(MEDDIC_CRITERION_NAMES):
        if prev.meddic_bits[i] and not next_snap.meddic_bits[i]:
            violations.append(InvariantViolation(
                rule="INV-2: MEDDIC criterion regression",
                detail=f"{name} regressed: true → false",
            ))

    # INV-3: DISC confidence is monotonically non-decreasing
    if next_snap.disc_confidence < prev.disc_confidence:
        violations.append(InvariantViolation(
            rule="INV-3: DISC confidence monotonic",
            detail=f"DISC confidence decreased: {prev.disc_confidence} → {next_snap.disc_confidence}",
        ))

    # INV-4: Stage transition is valid
    if not prev.stage.can_transition_to(next_snap.stage):
        violations.append(InvariantViolation(
            rule="INV-4: stage transition valid",
            detail=f"Invalid transition: {prev.stage.value} → {next_snap.stage.value}",
        ))

    # INV-5: Booking signal=direct only when MEDDIC ≥ 3
    if next_snap.booking_signal == BookingSignal.DIRECT and next_snap.meddic_score < 3:
        violations.append(InvariantViolation(
            rule="INV-5: premature booking",
            detail=f"booking_signal=direct but MEDDIC={next_snap.meddic_score}/6 (need ≥3)",
        ))

    # INV-6: Turn count is monotonically increasing
    if next_snap.turn_count < prev.turn_count:
        violations.append(InvariantViolation(
            rule="INV-6: turn count monotonic",
            detail=f"Turn count decreased: {prev.turn_count} → {next_snap.turn_count}",
        ))

    return violations
