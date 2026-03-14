"""Coaching intelligence module — MEDDIC, DISC, call stage FSM, and context building.

Ported from Souffleur (Rust) into Python/Pydantic for LangGraph agent integration.
"""

from app.data.coaching_schemas import (
    MEDDIC_CRITERION_NAMES,
    PARTNER_CRITERION_NAMES,
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
    PartnerProgress,
)
from app.services.coaching.invariants import (
    InvariantViolation,
    StateSnapshot,
    check_invariants,
)
from app.services.coaching.state_machine import (
    apply_coaching_to_session,
    build_cross_call_context,
    update_accumulated_state,
)

__all__ = [
    # Constants
    "MEDDIC_CRITERION_NAMES",
    "PARTNER_CRITERION_NAMES",
    # Types
    "AccumulatedState",
    "AudienceType",
    "BookingSignal",
    "BuyerDisc",
    "CallStage",
    "CoachingFocus",
    "CoachingResponse",
    "CoachingType",
    "CoachingUrgency",
    "CrossCallContext",
    "CurrentState",
    "CustomerSentiment",
    "DiscConfidence",
    "DiscType",
    "MeddicCriterion",
    "MeddicScore",
    "MeddicTracker",
    "NextGoal",
    "ObjectionType",
    "PartnerProgress",
    # State machine
    "apply_coaching_to_session",
    "build_cross_call_context",
    "update_accumulated_state",
    # Invariants
    "InvariantViolation",
    "StateSnapshot",
    "check_invariants",
]
