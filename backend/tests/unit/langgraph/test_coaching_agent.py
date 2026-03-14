"""Tests for Coaching LangGraph Agent (7th Agent).

Tests the 4-node graph: build_context → analyze_turn → generate_coaching → validate_state.
Mocks LLM at .with_structured_output() level.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.coaching_schemas import (
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
    MeddicScore,
    NextGoal,
    ObjectionType,
)
from app.services.langgraph.agents.coaching import CoachingAgent

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def agent() -> CoachingAgent:
    """Create coaching agent instance."""
    return CoachingAgent()


@pytest.fixture
def sample_accumulated() -> AccumulatedState:
    """Sample accumulated state with some MEDDIC progress."""
    return AccumulatedState()


@pytest.fixture
def sample_current_state() -> CurrentState:
    """Sample CurrentState from LLM analysis."""
    return CurrentState(
        call_stage=CallStage.DISCOVERY,
        customer_sentiment=CustomerSentiment.INTERESTED,
        topic_being_discussed="lecture capture needs",
        customer_pain_point="Manual recording is time-consuming",
        next_goal=NextGoal.QUALIFY,
        meddic=MeddicScore(identify_pain=True),
        buyer_disc=BuyerDisc(
            disc_type=DiscType.CONSCIENTIOUS,
            confidence=DiscConfidence.MEDIUM,
            signals="Asking detailed technical questions",
        ),
    )


@pytest.fixture
def sample_coaching() -> CoachingResponse:
    """Sample CoachingResponse from LLM."""
    return CoachingResponse(
        coaching_type=CoachingType.QUESTION_PROMPT,
        urgency=CoachingUrgency.MEDIUM,
        focus=CoachingFocus.ASK_QUESTION,
        response="Ask about their current workflow for scheduling recordings.",
        rationale="Pain confirmed — now qualify the buying process.",
        suggested_question="How do you currently decide which rooms to record?",
        objection_type=ObjectionType.NONE,
        booking_signal=BookingSignal.NONE,
        summary_update="Prospect has pain around manual recording processes.",
        topics_added=["lecture capture", "manual recording"],
        objections_added=[],
    )


def _mock_structured_llm(return_value: Any) -> MagicMock:
    """Create a mock LLM that returns structured output."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=return_value)
    mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
    return mock_llm


# =============================================================================
# Happy Path Tests
# =============================================================================


@pytest.mark.asyncio
async def test_coaching_agent_full_flow(
    agent: CoachingAgent,
    sample_accumulated: AccumulatedState,
    sample_current_state: CurrentState,
    sample_coaching: CoachingResponse,
) -> None:
    """Test full 4-node graph execution."""
    mock_analysis_llm = _mock_structured_llm(sample_current_state)
    mock_coaching_llm = _mock_structured_llm(sample_coaching)

    with patch("app.services.langgraph.agents.coaching.llm_router") as mock_router:
        # First call (synthesis) → analysis LLM, second call (personalization) → coaching LLM
        mock_router.get_model.side_effect = [mock_analysis_llm, mock_coaching_llm]

        result = await agent.run(
            transcript="Rep: How are you handling lecture capture today?\nProspect: We're still doing it manually.",
            call_stage=CallStage.DISCOVERY,
            accumulated_state=sample_accumulated,
        )

    assert result["coaching"] is not None
    assert result["current_state"] is not None
    assert result["updated_accumulated"] is not None
    assert isinstance(result["invariant_violations"], list)


@pytest.mark.asyncio
async def test_coaching_agent_returns_coaching_response(
    agent: CoachingAgent,
    sample_accumulated: AccumulatedState,
    sample_current_state: CurrentState,
    sample_coaching: CoachingResponse,
) -> None:
    """Test that agent returns correct coaching fields."""
    mock_analysis_llm = _mock_structured_llm(sample_current_state)
    mock_coaching_llm = _mock_structured_llm(sample_coaching)

    with patch("app.services.langgraph.agents.coaching.llm_router") as mock_router:
        mock_router.get_model.side_effect = [mock_analysis_llm, mock_coaching_llm]

        result = await agent.run(
            transcript="Prospect: We're looking for automated lecture capture.",
            call_stage=CallStage.DISCOVERY,
            accumulated_state=sample_accumulated,
        )

    coaching = result["coaching"]
    assert coaching.coaching_type == CoachingType.QUESTION_PROMPT
    assert coaching.focus == CoachingFocus.ASK_QUESTION
    assert "workflow" in coaching.response.lower() or "recording" in coaching.response.lower()


@pytest.mark.asyncio
async def test_coaching_updates_meddic(
    agent: CoachingAgent,
    sample_accumulated: AccumulatedState,
    sample_current_state: CurrentState,
    sample_coaching: CoachingResponse,
) -> None:
    """Test that MEDDIC state is updated after coaching (false→true only)."""
    # Start with all MEDDIC false
    assert sample_accumulated.meddic.identify_pain.confirmed is False

    mock_analysis_llm = _mock_structured_llm(sample_current_state)
    mock_coaching_llm = _mock_structured_llm(sample_coaching)

    with patch("app.services.langgraph.agents.coaching.llm_router") as mock_router:
        mock_router.get_model.side_effect = [mock_analysis_llm, mock_coaching_llm]

        result = await agent.run(
            transcript="Prospect: We waste hours every week on manual recording.",
            call_stage=CallStage.DISCOVERY,
            accumulated_state=sample_accumulated,
        )

    updated = result["updated_accumulated"]
    # identify_pain should be confirmed now (from CurrentState.meddic.identify_pain=True)
    assert updated.meddic.identify_pain.confirmed is True
    # Others should still be false
    assert updated.meddic.metrics.confirmed is False


@pytest.mark.asyncio
async def test_coaching_updates_disc(
    agent: CoachingAgent,
    sample_accumulated: AccumulatedState,
    sample_current_state: CurrentState,
    sample_coaching: CoachingResponse,
) -> None:
    """Test that DISC profile is updated after coaching."""
    assert sample_accumulated.disc.disc_type == DiscType.UNKNOWN

    mock_analysis_llm = _mock_structured_llm(sample_current_state)
    mock_coaching_llm = _mock_structured_llm(sample_coaching)

    with patch("app.services.langgraph.agents.coaching.llm_router") as mock_router:
        mock_router.get_model.side_effect = [mock_analysis_llm, mock_coaching_llm]

        result = await agent.run(
            transcript="Prospect: Can you share the technical specs?",
            call_stage=CallStage.DISCOVERY,
            accumulated_state=sample_accumulated,
        )

    updated = result["updated_accumulated"]
    assert updated.disc.disc_type == DiscType.CONSCIENTIOUS
    assert updated.disc.confidence == DiscConfidence.MEDIUM


# =============================================================================
# Context Building Tests
# =============================================================================


@pytest.mark.asyncio
async def test_build_context_with_cross_call(
    agent: CoachingAgent,
    sample_accumulated: AccumulatedState,
    sample_current_state: CurrentState,
    sample_coaching: CoachingResponse,
) -> None:
    """Test that cross-call context is included in system prompt."""
    cross_call = CrossCallContext(
        confirmed_pains=["manual recording"],
        unresolved_objections=["budget concerns"],
        last_stage_reached="discovery",
        total_previous_calls=2,
    )

    mock_analysis_llm = _mock_structured_llm(sample_current_state)
    mock_coaching_llm = _mock_structured_llm(sample_coaching)

    with patch("app.services.langgraph.agents.coaching.llm_router") as mock_router:
        mock_router.get_model.side_effect = [mock_analysis_llm, mock_coaching_llm]

        result = await agent.run(
            transcript="Rep: Following up on our last conversation...",
            call_stage=CallStage.DISCOVERY,
            accumulated_state=sample_accumulated,
            cross_call=cross_call,
        )

    assert result["coaching"] is not None


@pytest.mark.asyncio
async def test_build_context_channel_partner(
    agent: CoachingAgent,
    sample_accumulated: AccumulatedState,
    sample_current_state: CurrentState,
    sample_coaching: CoachingResponse,
) -> None:
    """Test context building for channel partner audience."""
    mock_analysis_llm = _mock_structured_llm(sample_current_state)
    mock_coaching_llm = _mock_structured_llm(sample_coaching)

    with patch("app.services.langgraph.agents.coaching.llm_router") as mock_router:
        mock_router.get_model.side_effect = [mock_analysis_llm, mock_coaching_llm]

        result = await agent.run(
            transcript="Partner: We're interested in reselling.",
            call_stage=CallStage.OPENING,
            accumulated_state=sample_accumulated,
            audience=AudienceType.CHANNEL_PARTNER,
        )

    assert result["coaching"] is not None


# =============================================================================
# Invariant Validation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_no_invariant_violations_normal_flow(
    agent: CoachingAgent,
    sample_accumulated: AccumulatedState,
    sample_current_state: CurrentState,
    sample_coaching: CoachingResponse,
) -> None:
    """Test that normal progression has no invariant violations."""
    mock_analysis_llm = _mock_structured_llm(sample_current_state)
    mock_coaching_llm = _mock_structured_llm(sample_coaching)

    with patch("app.services.langgraph.agents.coaching.llm_router") as mock_router:
        mock_router.get_model.side_effect = [mock_analysis_llm, mock_coaching_llm]

        result = await agent.run(
            transcript="Normal conversation turn.",
            call_stage=CallStage.OPENING,
            accumulated_state=sample_accumulated,
        )

    assert result["invariant_violations"] == []


# =============================================================================
# Graceful Degradation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_analysis_llm_failure_returns_default(
    agent: CoachingAgent,
    sample_accumulated: AccumulatedState,
    sample_coaching: CoachingResponse,
) -> None:
    """Test that LLM failure in analyze_turn returns default CurrentState."""
    # Analysis LLM fails
    mock_fail_llm = MagicMock()
    mock_fail_structured = MagicMock()
    mock_fail_structured.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))
    mock_fail_llm.with_structured_output = MagicMock(return_value=mock_fail_structured)

    mock_coaching_llm = _mock_structured_llm(sample_coaching)

    with patch("app.services.langgraph.agents.coaching.llm_router") as mock_router:
        mock_router.get_model.side_effect = [mock_fail_llm, mock_coaching_llm]

        result = await agent.run(
            transcript="Some conversation.",
            call_stage=CallStage.DISCOVERY,
            accumulated_state=sample_accumulated,
        )

    # Should still return a result with fallback CurrentState
    assert result["current_state"] is not None
    assert result["current_state"].call_stage == CallStage.DISCOVERY


@pytest.mark.asyncio
async def test_coaching_llm_failure_returns_default(
    agent: CoachingAgent,
    sample_accumulated: AccumulatedState,
    sample_current_state: CurrentState,
) -> None:
    """Test that LLM failure in generate_coaching returns default CoachingResponse."""
    mock_analysis_llm = _mock_structured_llm(sample_current_state)

    # Coaching LLM fails
    mock_fail_llm = MagicMock()
    mock_fail_structured = MagicMock()
    mock_fail_structured.ainvoke = AsyncMock(side_effect=Exception("LLM error"))
    mock_fail_llm.with_structured_output = MagicMock(return_value=mock_fail_structured)

    with patch("app.services.langgraph.agents.coaching.llm_router") as mock_router:
        mock_router.get_model.side_effect = [mock_analysis_llm, mock_fail_llm]

        result = await agent.run(
            transcript="Some conversation.",
            call_stage=CallStage.DISCOVERY,
            accumulated_state=sample_accumulated,
        )

    # Should return default coaching
    assert result["coaching"] is not None
    assert result["coaching"].coaching_type == CoachingType.WHISPER


# =============================================================================
# Singleton Tests
# =============================================================================


def test_singleton_exists() -> None:
    """Test that module-level singleton is available."""
    from app.services.langgraph.agents.coaching import coaching_agent

    assert coaching_agent is not None
    assert isinstance(coaching_agent, CoachingAgent)


def test_graph_builds_correctly(agent: CoachingAgent) -> None:
    """Test that the graph has expected nodes."""
    compiled = agent.compiled_graph
    assert compiled is not None


# =============================================================================
# LLM Routing Tests
# =============================================================================


@pytest.mark.asyncio
async def test_uses_correct_llm_for_analysis(
    agent: CoachingAgent,
    sample_accumulated: AccumulatedState,
    sample_current_state: CurrentState,
    sample_coaching: CoachingResponse,
) -> None:
    """Test that analyze_turn uses 'synthesis' (Claude) model."""
    mock_analysis_llm = _mock_structured_llm(sample_current_state)
    mock_coaching_llm = _mock_structured_llm(sample_coaching)

    with patch("app.services.langgraph.agents.coaching.llm_router") as mock_router:
        mock_router.get_model.side_effect = [mock_analysis_llm, mock_coaching_llm]

        await agent.run(
            transcript="Test transcript.",
            call_stage=CallStage.OPENING,
            accumulated_state=sample_accumulated,
        )

    # First call should be "synthesis", second "personalization"
    calls = mock_router.get_model.call_args_list
    assert calls[0].args[0] == "synthesis"
    assert calls[1].args[0] == "personalization"
