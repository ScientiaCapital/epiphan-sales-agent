"""State machine for coaching intelligence — FSM transitions and state updates.

Ported from souffleur-core/src/state_machine.rs.
"""

from __future__ import annotations

import logging
from collections import Counter

from app.data.coaching_schemas import (
    AccumulatedState,
    CallHistoryEntry,
    CoachingResponse,
    CrossCallContext,
    CurrentState,
    MeddicTracker,
)

logger = logging.getLogger(__name__)

EVIDENCE_TRUNCATE_LEN = 120
MAX_SESSION_TOPICS = 20
MAX_SESSION_OBJECTIONS = 20


def update_accumulated_state(acc: AccumulatedState, cs: CurrentState, coaching: CoachingResponse) -> None:
    """Update accumulated state from a parsed coaching response.

    MEDDIC: false→true only. DISC: higher confidence only.
    """
    evidence = _build_evidence(coaching)
    acc.update_from_current_state(cs, evidence)


def _build_evidence(coaching: CoachingResponse) -> str:
    """Build evidence string from coaching response context."""
    if coaching.summary_update.strip():
        return coaching.summary_update[:EVIDENCE_TRUNCATE_LEN]
    if coaching.rationale.strip():
        return coaching.rationale[:EVIDENCE_TRUNCATE_LEN]
    return ""


def apply_coaching_to_session(
    session_meddic: MeddicTracker,
    session_topics: list[str],
    session_objections: list[str],
    coaching: CoachingResponse,
    current_state: CurrentState | None = None,
) -> str:
    """Apply coaching metadata to session-level state.

    Updates topics, objections, MEDDIC, and returns the running summary.
    Operates on mutable references — modifies in place.
    """
    # Append new topics (deduplicated, capped to prevent prompt bloat)
    for topic in coaching.topics_added:
        if len(session_topics) < MAX_SESSION_TOPICS and topic not in session_topics:
            session_topics.append(topic)

    # Append new objections (deduplicated, capped)
    for objection in coaching.objections_added:
        if len(session_objections) < MAX_SESSION_OBJECTIONS and objection not in session_objections:
            session_objections.append(objection)

    # MEDDIC + DISC — delegate to shared logic
    if current_state is not None:
        evidence = _build_evidence(coaching)
        session_meddic.update_from_score(current_state.meddic, evidence)

    # Return running summary
    if coaching.summary_update.strip():
        return coaching.summary_update
    return ""


def build_cross_call_context(history: list[CallHistoryEntry]) -> CrossCallContext:
    """Build cross-call context from call history entries."""
    topic_counts: Counter[str] = Counter()
    # Most recent call's stage (history assumed chronological, so last non-None wins)
    last_stage: str | None = next(
        (call.stage_reached for call in reversed(history) if call.stage_reached),
        None,
    )

    for call in history:
        if call.key_topics:
            for topic in call.key_topics:
                topic_counts[topic] += 1

    recurring_topics = [topic for topic, count in topic_counts.items() if count >= 2]

    return CrossCallContext(
        confirmed_pains=[],
        open_commitments=[],
        unresolved_objections=[],
        recurring_topics=recurring_topics,
        last_stage_reached=last_stage,
        total_previous_calls=len(history),
    )
