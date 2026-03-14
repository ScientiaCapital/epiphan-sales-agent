"""Coaching LangGraph Agent (7th Agent).

Analyzes conversation turns and produces real-time coaching responses
for BDRs during live sales calls. Uses existing coaching intelligence
layer (context_builder, state_machine, invariants) with LLM structured output.

LLM routing:
- analyze_turn: Claude (quality — "synthesis")
- generate_coaching: Claude (quality — "personalization")
"""

from typing import Any, cast

from app.data.coaching_schemas import (
    AccumulatedState,
    AudienceType,
    BookingSignal,
    CallStage,
    CoachingResponse,
    CrossCallContext,
    CurrentState,
)
from app.services.coaching.context_builder import build_coach_system_prompt
from app.services.coaching.invariants import StateSnapshot, check_invariants
from app.services.coaching.state_machine import update_accumulated_state
from app.services.langgraph.states import CoachingAgentState
from app.services.llm.clients import llm_router
from langgraph.graph import END, StateGraph


class CoachingAgent:
    """Agent for real-time coaching during sales calls.

    Flow:
    1. build_context — Assemble layered system prompt via context_builder
    2. analyze_turn — LLM: parse conversation → CurrentState (structured output)
    3. generate_coaching — LLM: CurrentState + context → CoachingResponse (structured output)
    4. validate_state — Check invariants, update accumulated state
    """

    def __init__(self) -> None:
        """Initialize agent with LLM clients."""
        self._graph: StateGraph[CoachingAgentState] | None = None
        self._compiled: Any = None

    @property
    def graph(self) -> StateGraph[CoachingAgentState]:
        """Build and return the state graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    @property
    def compiled_graph(self) -> Any:
        """Get compiled graph for execution."""
        if self._compiled is None:
            self._compiled = self.graph.compile()
        return self._compiled

    def _build_graph(self) -> StateGraph[CoachingAgentState]:
        """Build the LangGraph state graph."""
        graph = StateGraph(CoachingAgentState)

        graph.add_node("build_context", self._build_context)
        graph.add_node("analyze_turn", self._analyze_turn)
        graph.add_node("generate_coaching", self._generate_coaching)
        graph.add_node("validate_state", self._validate_state)

        graph.set_entry_point("build_context")
        graph.add_edge("build_context", "analyze_turn")
        graph.add_edge("analyze_turn", "generate_coaching")
        graph.add_edge("generate_coaching", "validate_state")
        graph.add_edge("validate_state", END)

        return graph

    async def run(
        self,
        transcript: str,
        call_stage: CallStage,
        accumulated_state: AccumulatedState,
        audience: AudienceType = AudienceType.DIRECT_SALE,
        topics: list[str] | None = None,
        objections: list[str] | None = None,
        cross_call: CrossCallContext | None = None,
    ) -> dict[str, Any]:
        """Run the coaching agent on a conversation turn.

        Args:
            transcript: Current conversation transcript
            call_stage: Current call stage
            accumulated_state: Accumulated MEDDIC/DISC state
            audience: Direct sale or channel partner
            topics: Topics discussed so far
            objections: Objections raised so far
            cross_call: Cross-call context from prior conversations

        Returns:
            Dict with coaching, current_state, updated_accumulated, invariant_violations
        """
        initial_state: CoachingAgentState = {
            "transcript": transcript,
            "call_stage": call_stage,
            "accumulated_state": accumulated_state,
            "audience": audience,
            "topics": topics or [],
            "objections": objections or [],
            "cross_call": cross_call,
            "system_prompt": "",
            "current_state": None,
            "coaching": None,
            "updated_accumulated": None,
            "invariant_violations": [],
        }

        final_state = await self.compiled_graph.ainvoke(initial_state)

        return {
            "coaching": final_state["coaching"],
            "current_state": final_state["current_state"],
            "updated_accumulated": final_state["updated_accumulated"],
            "invariant_violations": final_state["invariant_violations"],
        }

    async def _build_context(
        self,
        state: CoachingAgentState,
    ) -> dict[str, Any]:
        """Assemble layered system prompt via context_builder."""
        system_prompt = build_coach_system_prompt(
            stage=state["call_stage"],
            audience=state["audience"],
            acc=state["accumulated_state"],
            topics=state["topics"],
            objections=state["objections"],
            cross_call=state["cross_call"],
        )
        return {"system_prompt": system_prompt}

    async def _analyze_turn(
        self,
        state: CoachingAgentState,
    ) -> dict[str, Any]:
        """Parse conversation transcript into CurrentState using structured output."""
        llm = llm_router.get_model("synthesis")  # Claude — quality task
        structured_llm = llm.with_structured_output(CurrentState)

        prompt = (
            f"Analyze this sales conversation turn and extract the current state.\n\n"
            f"TRANSCRIPT:\n{state['transcript']}\n\n"
            f"Current call stage context: {state['call_stage'].value}\n"
            f"Extract: call stage, customer sentiment, topic being discussed, "
            f"pain points, next goal, MEDDIC criteria confirmed, and DISC buyer profile signals."
        )

        try:
            result = cast(CurrentState, await structured_llm.ainvoke(prompt))
            return {"current_state": result}
        except Exception:
            # Fallback: return default CurrentState on LLM failure
            return {"current_state": CurrentState(call_stage=state["call_stage"])}

    async def _generate_coaching(
        self,
        state: CoachingAgentState,
    ) -> dict[str, Any]:
        """Generate coaching response from CurrentState + system prompt."""
        current_state = state["current_state"]
        if current_state is None:
            return {"coaching": CoachingResponse()}

        llm = llm_router.get_model("personalization")  # Claude — quality task
        structured_llm = llm.with_structured_output(CoachingResponse)

        prompt = (
            f"{state['system_prompt']}\n\n"
            f"CURRENT STATE:\n"
            f"- Stage: {current_state.call_stage.value}\n"
            f"- Sentiment: {current_state.customer_sentiment.value}\n"
            f"- Topic: {current_state.topic_being_discussed}\n"
            f"- Pain: {current_state.customer_pain_point or 'none detected'}\n"
            f"- Next goal: {current_state.next_goal.value}\n"
            f"- MEDDIC score: {current_state.meddic.score()}/6\n"
            f"- DISC: {current_state.buyer_disc.disc_type.value}\n\n"
            f"TRANSCRIPT:\n{state['transcript']}\n\n"
            f"Generate coaching for the sales rep. Be concise and actionable."
        )

        try:
            result = cast(CoachingResponse, await structured_llm.ainvoke(prompt))
            return {"coaching": result}
        except Exception:
            return {"coaching": CoachingResponse()}

    async def _validate_state(
        self,
        state: CoachingAgentState,
    ) -> dict[str, Any]:
        """Check invariants and update accumulated state."""
        current_state = state["current_state"]
        coaching = state["coaching"]
        acc = state["accumulated_state"]

        if current_state is None or coaching is None:
            return {
                "updated_accumulated": acc,
                "invariant_violations": [],
            }

        # Capture pre-update snapshot for invariant checking
        prev_snapshot = StateSnapshot.capture(
            acc=acc,
            stage=state["call_stage"],
            booking_signal=BookingSignal.NONE,
            turn_count=0,
        )

        # Update accumulated state (MEDDIC false→true, DISC higher confidence)
        updated = acc.model_copy(deep=True)
        update_accumulated_state(updated, current_state, coaching)

        # Capture post-update snapshot
        next_snapshot = StateSnapshot.capture(
            acc=updated,
            stage=current_state.call_stage,
            booking_signal=coaching.booking_signal,
            turn_count=1,
        )

        # Check invariants
        violations = check_invariants(prev_snapshot, next_snapshot)
        violation_strs = [f"{v.rule}: {v.detail}" for v in violations]

        return {
            "updated_accumulated": updated,
            "invariant_violations": violation_strs,
        }


# Singleton instance
coaching_agent = CoachingAgent()
