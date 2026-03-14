"""Script Selection Agent.

Personalizes warm and cold call scripts based on lead context.
Uses Claude for high-quality personalization.
"""

from typing import Any, cast

from app.data.lead_schemas import Lead
from app.services.langgraph.states import ScriptResponseOutput, ScriptSelectionState
from app.services.langgraph.tools.script_tools import (
    get_cold_script,
    get_persona_profile,
    get_warm_script,
)
from app.services.llm.clients import llm_router
from langgraph.graph import END, StateGraph


class ScriptSelectionAgent:
    """
    Agent for selecting and personalizing call scripts.

    Flow:
    1. load_script - Load base script (warm or cold)
    2. extract_context - Extract relevant lead context
    3. personalize - Personalize script with LLM
    """

    def __init__(self) -> None:
        """Initialize agent with LLM and graph."""
        self.llm = llm_router.get_model("personalization")  # Claude for quality
        self._graph: StateGraph[ScriptSelectionState] | None = None
        self._compiled: Any = None

    @property
    def graph(self) -> StateGraph[ScriptSelectionState]:
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

    def _build_graph(self) -> StateGraph[ScriptSelectionState]:
        """Build the LangGraph state graph."""
        graph = StateGraph(ScriptSelectionState)

        # Add nodes
        graph.add_node("load_script", self._load_script)
        graph.add_node("extract_context", self._extract_context)
        graph.add_node("personalize", self._personalize)

        # Add edges
        graph.set_entry_point("load_script")
        graph.add_edge("load_script", "extract_context")
        graph.add_edge("extract_context", "personalize")
        graph.add_edge("personalize", END)

        return graph

    async def run(
        self,
        lead: Lead,
        persona_match: str | None,
        trigger: str | None,
        call_type: str = "warm",
    ) -> dict[str, Any]:
        """
        Run the agent to generate personalized script.

        Args:
            lead: Lead to generate script for
            persona_match: Matched persona ID
            trigger: Trigger type (for warm calls)
            call_type: "warm" or "cold"

        Returns:
            Dict with personalized_script, talking_points, objection_responses
        """
        initial_state: ScriptSelectionState = {
            "lead": lead,
            "persona_match": persona_match,
            "trigger": trigger,
            "call_type": call_type,
            "base_script": None,
            "lead_context": None,
            "persona_profile": None,
            "personalized_script": "",
            "talking_points": [],
            "objection_responses": [],
        }

        # Run the graph
        final_state = await self.compiled_graph.ainvoke(initial_state)

        return {
            "personalized_script": final_state["personalized_script"],
            "talking_points": final_state["talking_points"],
            "objection_responses": final_state["objection_responses"],
        }

    async def _load_script(
        self,
        state: ScriptSelectionState,
    ) -> dict[str, Any]:
        """Load the base script based on call type."""
        persona_profile = None
        if state["persona_match"]:
            persona_profile = get_persona_profile(state["persona_match"])

        base_script = None
        objection_responses = []

        if state["call_type"] == "warm" and state["trigger"] and state["persona_match"]:
            # Warm call - use persona + trigger
            base_script = get_warm_script(
                state["persona_match"],
                state["trigger"],
            )
        else:
            # Cold call - use vertical from persona or default
            vertical = "higher_ed"  # default
            if persona_profile and persona_profile.get("verticals"):
                vertical = persona_profile["verticals"][0]
            base_script = get_cold_script(vertical)

        # Extract objection handlers/pivots from script
        if base_script:
            handlers = base_script.get("objection_handlers") or base_script.get(
                "objection_pivots", []
            )
            objection_responses = handlers[:5]  # Top 5

        return {
            "base_script": base_script,
            "persona_profile": persona_profile,
            "objection_responses": objection_responses,
        }

    async def _extract_context(
        self,
        state: ScriptSelectionState,
    ) -> dict[str, Any]:
        """Extract relevant context from lead."""
        lead = state["lead"]
        persona = state["persona_profile"]

        context_parts = []

        # Lead info
        if lead.first_name:
            context_parts.append(f"Name: {lead.first_name}")
        if lead.company:
            context_parts.append(f"Company: {lead.company}")
        if lead.title:
            context_parts.append(f"Title: {lead.title}")

        # Persona pain points
        if persona and persona.get("pain_points"):
            top_pains = persona["pain_points"][:3]
            pain_text = ", ".join([p["point"] for p in top_pains])
            context_parts.append(f"Likely pain points: {pain_text}")

        # Talking points from persona hot buttons
        talking_points = []
        if persona and persona.get("hot_buttons"):
            talking_points = persona["hot_buttons"][:5]

        return {
            "lead_context": "\n".join(context_parts),
            "talking_points": talking_points,
        }

    async def _personalize(
        self,
        state: ScriptSelectionState,
    ) -> dict[str, Any]:
        """Personalize script using LLM with structured output."""
        if not state["base_script"]:
            return {
                "personalized_script": "No script template available for this combination.",
            }

        prompt = self._build_prompt(state)
        structured_llm = self.llm.with_structured_output(ScriptResponseOutput)
        result = cast(ScriptResponseOutput, await structured_llm.ainvoke(prompt))

        return {
            "personalized_script": result.personalized_script,
        }

    def _build_prompt(self, state: ScriptSelectionState) -> str:
        """Build prompt for personalization."""
        script = state["base_script"] or {}
        lead = state["lead"]

        if state["call_type"] == "warm":
            # ACQP framework for warm scripts
            script_text = f"""
ACKNOWLEDGE: {script.get('acknowledge', '')}
CONNECT: {script.get('connect', '')}
QUALIFY: {script.get('qualify', '')}
PROPOSE: {script.get('propose', '')}
"""
        else:
            # Pattern-interrupt framework for cold scripts
            script_text = f"""
PATTERN INTERRUPT: {script.get('pattern_interrupt', '')}
VALUE HOOK: {script.get('value_hook', '')}
PAIN QUESTION: {script.get('pain_question', '')}
PERMISSION: {script.get('permission', '')}
PIVOT: {script.get('pivot', '')}
"""

        return f"""You are a BDR for Epiphan Video. Personalize this call script for the specific lead.

LEAD CONTEXT:
{state['lead_context']}

BASE SCRIPT:
{script_text}

INSTRUCTIONS:
1. Replace [Name] with {lead.first_name or 'there'}
2. Make the value hook specific to their company/role if possible
3. Keep the structure but make it natural
4. Output ONLY the personalized script, ready to read

PERSONALIZED SCRIPT:"""


# Singleton instance
script_selection_agent = ScriptSelectionAgent()
