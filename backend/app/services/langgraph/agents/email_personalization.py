"""Email Personalization Agent for generating personalized outreach emails.

Uses LLM to generate compelling, personalized emails based on
research briefs, persona data, and email templates.
"""

import re
from typing import Any

from app.data.lead_schemas import Lead
from app.services.langgraph.states import EmailPersonalizationState, ResearchBrief
from app.services.langgraph.tools.email_tools import (
    build_email_prompt,
    extract_personalization_hooks,
    get_pain_points_for_persona,
)
from app.services.llm.clients import llm_router
from langgraph.graph import END, StateGraph


class EmailPersonalizationAgent:
    """
    Agent for generating personalized sales emails.

    Flow: gather_context → generate_email → parse_output
    """

    def __init__(self):
        """Initialize the agent with LLM."""
        self._llm = llm_router.get_model("personalization")  # Claude for quality
        self._graph: StateGraph | None = None

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        graph = StateGraph(EmailPersonalizationState)

        # Add nodes
        graph.add_node("gather_context", self._gather_context_node)
        graph.add_node("generate_email", self._generate_email_node)
        graph.add_node("parse_output", self._parse_output_node)

        # Define edges
        graph.set_entry_point("gather_context")
        graph.add_edge("gather_context", "generate_email")
        graph.add_edge("generate_email", "parse_output")
        graph.add_edge("parse_output", END)

        return graph

    async def _gather_context_node(
        self, state: EmailPersonalizationState
    ) -> dict[str, Any]:
        """Gather pain points and personalization hooks."""
        research_brief = state.get("research_brief")
        persona = state.get("persona")

        # Get pain points for persona
        persona_id = persona.get("id", "unknown") if persona else "unknown"
        pain_points = get_pain_points_for_persona(persona_id)

        # Extract personalization hooks from research
        hooks: list[dict[str, str]] = []
        if research_brief:
            hooks = extract_personalization_hooks(research_brief)

        # Convert hooks to simple strings
        hook_strings = [h.get("content", "") for h in hooks if h.get("content")]

        return {
            "pain_points": pain_points,
            "personalization_hooks": hook_strings,
        }

    async def _generate_email_node(
        self, state: EmailPersonalizationState
    ) -> dict[str, Any]:
        """Generate email using LLM."""
        lead = state["lead"]
        research_brief = state.get("research_brief") or self._empty_brief()
        email_type = state.get("email_type", "pattern_interrupt")
        sequence_step = state.get("sequence_step", 1)
        pain_points = state.get("pain_points", [])
        hooks = state.get("personalization_hooks", [])

        # Build prompt
        prompt = build_email_prompt(
            lead=lead,
            research_brief=research_brief,
            email_type=email_type,
            sequence_step=sequence_step,
            pain_points=pain_points,
            personalization_hooks=hooks,
        )

        # Generate with LLM (use self._llm to allow mocking)
        response = await self._llm.ainvoke(prompt)
        raw_content = response.content

        # Parse immediately to avoid state issues
        subject_line, email_body = self._parse_email_response(raw_content)

        return {
            "subject_line": subject_line,
            "email_body": email_body,
        }

    async def _parse_output_node(
        self, state: EmailPersonalizationState  # noqa: ARG002
    ) -> dict[str, Any]:
        """Finalize output with follow-up note."""
        return {
            "follow_up_note": None,
        }

    def _parse_email_response(self, raw: str) -> tuple[str, str]:
        """
        Parse raw LLM response into subject and body.

        Args:
            raw: Raw LLM output

        Returns:
            Tuple of (subject_line, email_body)
        """
        lines = raw.strip().split("\n")
        subject_line = ""
        body_lines = []
        found_subject = False

        for line in lines:
            # Look for subject line
            if line.lower().startswith("subject:"):
                subject_line = line.split(":", 1)[1].strip()
                found_subject = True
            elif found_subject:
                # Everything after subject is body
                body_lines.append(line)

        # If no subject found, try to extract from first line
        if not subject_line and lines:
            subject_line = lines[0]
            body_lines = lines[1:]

        # Clean up body
        body = "\n".join(body_lines).strip()

        # Remove common markers
        body = re.sub(r"\[Signature.*?\]", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\[Name\]", "", body)

        return subject_line, body.strip()

    def _empty_brief(self) -> ResearchBrief:
        """Create an empty research brief."""
        return {
            "company_overview": "",
            "recent_news": [],
            "talking_points": [],
            "risk_factors": [],
            "linkedin_summary": None,
        }

    async def run(
        self,
        lead: Lead,
        research_brief: ResearchBrief | None = None,
        persona: dict[str, Any] | None = None,
        email_type: str = "pattern_interrupt",
        sequence_step: int = 1,
    ) -> dict[str, Any]:
        """
        Generate a personalized email.

        Args:
            lead: Target lead
            research_brief: Research intelligence (optional)
            persona: Persona data (optional)
            email_type: Type of email (pattern_interrupt, pain_point, breakup, nurture)
            sequence_step: Current sequence step (1-4)

        Returns:
            Dict with subject_line, email_body, follow_up_note
        """
        # Build graph if needed
        if self._graph is None:
            self._graph = self._build_graph()

        # Compile and run
        compiled = self._graph.compile()

        # Initial state
        initial_state: EmailPersonalizationState = {
            "lead": lead,
            "research_brief": research_brief,
            "persona": persona,
            "sequence_step": sequence_step,
            "email_type": email_type,
            "pain_points": [],
            "personalization_hooks": [],
            "subject_line": "",
            "email_body": "",
            "follow_up_note": None,
        }

        # Run the graph
        result = await compiled.ainvoke(initial_state)

        return {
            "subject_line": result.get("subject_line", ""),
            "email_body": result.get("email_body", ""),
            "follow_up_note": result.get("follow_up_note"),
        }


# Singleton instance
email_personalization_agent = EmailPersonalizationAgent()
