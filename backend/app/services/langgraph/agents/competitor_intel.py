"""Competitor Intelligence Agent.

Provides real-time battlecard responses during sales calls.
Uses fast LLM (Cerebras/DeepSeek) for <2s response time.
"""

from typing import Any

from langgraph.graph import END, StateGraph

from app.services.langgraph.states import CompetitorIntelState
from app.services.langgraph.tools.competitor_tools import (
    get_battlecard,
    get_claim_responses,
)
from app.services.llm.clients import llm_router


class CompetitorIntelAgent:
    """
    Agent for real-time competitor intelligence.

    Flow:
    1. lookup_battlecard - Find competitor battlecard
    2. match_context - Match context to relevant differentiators
    3. generate_response - Generate response using LLM
    """

    def __init__(self):
        """Initialize agent with LLM and graph."""
        self.llm = llm_router.get_model("lookup")  # Fast model for real-time
        self._graph: StateGraph | None = None
        self._compiled: Any = None

    @property
    def graph(self) -> StateGraph:
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

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        graph = StateGraph(CompetitorIntelState)

        # Add nodes
        graph.add_node("lookup_battlecard", self._lookup_battlecard)
        graph.add_node("match_context", self._match_context)
        graph.add_node("generate_response", self._generate_response)

        # Add edges
        graph.set_entry_point("lookup_battlecard")
        graph.add_edge("lookup_battlecard", "match_context")
        graph.add_edge("match_context", "generate_response")
        graph.add_edge("generate_response", END)

        return graph

    async def run(
        self,
        competitor_name: str,
        context: str,
        query_type: str = "claim",
    ) -> dict[str, Any]:
        """
        Run the agent to generate competitor response.

        Args:
            competitor_name: Name of competitor mentioned
            context: What the prospect said
            query_type: Type of query (claim, objection, comparison)

        Returns:
            Dict with response, proof_points, follow_up_question, battlecard
        """
        initial_state: CompetitorIntelState = {
            "competitor_name": competitor_name,
            "context": context,
            "query_type": query_type,
            "battlecard": None,
            "relevant_differentiators": [],
            "response": "",
            "proof_points": [],
            "follow_up_question": None,
        }

        # Run the graph
        final_state = await self.compiled_graph.ainvoke(initial_state)

        return {
            "response": final_state["response"],
            "proof_points": final_state["proof_points"],
            "follow_up_question": final_state["follow_up_question"],
            "battlecard": final_state["battlecard"],
        }

    async def _lookup_battlecard(
        self,
        state: CompetitorIntelState,
    ) -> dict[str, Any]:
        """Look up battlecard for competitor."""
        battlecard = get_battlecard(state["competitor_name"])
        return {"battlecard": battlecard}

    async def _match_context(
        self,
        state: CompetitorIntelState,
    ) -> dict[str, Any]:
        """Match context to relevant differentiators and claims."""
        if not state["battlecard"]:
            return {"relevant_differentiators": [], "proof_points": []}

        competitor_id = state["battlecard"]["id"]
        context_lower = state["context"].lower()

        # Find relevant differentiators by keyword overlap
        differentiators = []
        for diff in state["battlecard"]["key_differentiators"]:
            searchable = f"{diff['feature']} {diff['competitor']} {diff['pearl']}".lower()
            # Check for keyword overlap
            context_words = set(context_lower.split())
            diff_words = set(searchable.split())
            if context_words.intersection(diff_words):
                differentiators.append(diff)

        # Get claim responses if query is about a claim
        proof_points = []
        if state["query_type"] == "claim":
            claims = get_claim_responses(competitor_id)
            for claim in claims:
                if any(word in claim["claim"].lower() for word in context_lower.split()):
                    proof_points.append(claim["response"])

        return {
            "relevant_differentiators": differentiators[:3],  # Top 3
            "proof_points": proof_points[:3],
        }

    async def _generate_response(
        self,
        state: CompetitorIntelState,
    ) -> dict[str, Any]:
        """Generate response using LLM."""
        if not state["battlecard"]:
            return {
                "response": f"I don't have specific battlecard data for {state['competitor_name']}. Let me get back to you with details.",
                "follow_up_question": "Can you tell me more about what they're offering?",
            }

        # Build prompt
        prompt = self._build_prompt(state)

        # Call LLM
        response = await self.llm.ainvoke(prompt)
        response_text = response.content

        # Extract follow-up if present
        follow_up = None
        if "FOLLOW_UP:" in response_text:
            parts = response_text.split("FOLLOW_UP:")
            response_text = parts[0].strip()
            follow_up = parts[1].strip() if len(parts) > 1 else None

        return {
            "response": response_text,
            "follow_up_question": follow_up,
        }

    def _build_prompt(self, state: CompetitorIntelState) -> str:
        """Build prompt for LLM."""
        battlecard = state["battlecard"]

        differentiators_text = ""
        if state["relevant_differentiators"]:
            differentiators_text = "\n".join(
                [
                    f"- {d['feature']}: They have {d['competitor']}, we have {d['pearl']}. {d['why_it_matters']}"
                    for d in state["relevant_differentiators"]
                ]
            )

        proof_points_text = ""
        if state["proof_points"]:
            proof_points_text = "\n".join([f"- {p}" for p in state["proof_points"]])

        return f"""You are a sales rep for Epiphan Video. A prospect mentioned competitor {battlecard['name']}.

COMPETITOR INFO:
- Name: {battlecard['name']}
- Positioning: {battlecard['positioning']}
- Price Range: {battlecard['price_range']}

RELEVANT DIFFERENTIATORS:
{differentiators_text or "No specific differentiators matched."}

EXISTING PROOF POINTS:
{proof_points_text or "No pre-written responses matched."}

PROSPECT SAID: "{state['context']}"

QUERY TYPE: {state['query_type']}

Generate a concise, confident response (2-3 sentences max) that addresses their concern.
Focus on value, not bashing the competitor.
End with FOLLOW_UP: and a discovery question to keep the conversation going.

RESPONSE:"""


# Singleton instance
competitor_intel_agent = CompetitorIntelAgent()
