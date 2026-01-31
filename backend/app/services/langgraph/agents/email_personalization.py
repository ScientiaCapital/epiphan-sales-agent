"""Email Personalization Agent for generating personalized outreach emails.

Uses LLM to generate compelling, personalized emails based on
research briefs, persona data, and email templates.

Features:
- Human-in-the-loop approval workflow
- PostgresSaver checkpointing for state persistence
- Thread ID support for workflow tracking
"""

import re
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any, cast

from app.data.lead_schemas import Lead
from app.services.langgraph.checkpointing import get_checkpointer
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

    def __init__(self) -> None:
        """Initialize the agent with LLM."""
        self._llm = llm_router.get_model("personalization")  # Claude for quality
        self._graph: StateGraph[EmailPersonalizationState] | None = None

    def _build_graph(self) -> StateGraph[EmailPersonalizationState]:
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
        raw_content = str(response.content) if response.content else ""

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

    def _prepare_initial_state(
        self,
        lead: Lead,
        research_brief: ResearchBrief | None = None,
        persona: dict[str, Any] | None = None,
        email_type: str = "pattern_interrupt",
        sequence_step: int = 1,
    ) -> EmailPersonalizationState:
        """Prepare initial state for email generation."""
        return {
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

    def _extract_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Extract email result from state."""
        return {
            "subject_line": result.get("subject_line", ""),
            "email_body": result.get("email_body", ""),
            "follow_up_note": result.get("follow_up_note"),
        }

    async def run(
        self,
        lead: Lead,
        research_brief: ResearchBrief | None = None,
        persona: dict[str, Any] | None = None,
        email_type: str = "pattern_interrupt",
        sequence_step: int = 1,
        thread_id: str | None = None,
        use_checkpointing: bool = False,
    ) -> dict[str, Any]:
        """
        Generate a personalized email.

        Args:
            lead: Target lead
            research_brief: Research intelligence (optional)
            persona: Persona data (optional)
            email_type: Type of email (pattern_interrupt, pain_point, breakup, nurture)
            sequence_step: Current sequence step (1-4)
            thread_id: Optional thread ID for checkpointing
            use_checkpointing: If True, enable persistent checkpointing

        Returns:
            Dict with subject_line, email_body, follow_up_note
        """
        # Build graph if needed
        if self._graph is None:
            self._graph = self._build_graph()

        # Compile with optional checkpointing
        checkpointer = get_checkpointer() if use_checkpointing else None
        compiled = self._graph.compile(checkpointer=checkpointer)

        # Initial state
        initial_state = self._prepare_initial_state(
            lead, research_brief, persona, email_type, sequence_step
        )

        # Prepare config with optional thread_id
        config: dict[str, Any] = {}
        if thread_id:
            config = {"configurable": {"thread_id": thread_id}}

        # Run the graph
        result = await compiled.ainvoke(cast(Any, initial_state), config=cast(Any, config) if config else None)

        return self._extract_result(result)

    async def run_with_approval(
        self,
        lead: Lead,
        research_brief: ResearchBrief | None = None,
        persona: dict[str, Any] | None = None,
        email_type: str = "pattern_interrupt",
        sequence_step: int = 1,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate email and pause for human approval.

        This creates a draft email and pauses execution, allowing
        a human to review and approve/reject before finalizing.

        Args:
            lead: Target lead
            research_brief: Research intelligence (optional)
            persona: Persona data (optional)
            email_type: Type of email
            sequence_step: Current sequence step (1-4)
            thread_id: Thread ID for tracking (generated if not provided)

        Returns:
            Dict with thread_id, email_preview, subject_preview, status
        """
        # Generate thread_id if not provided
        if not thread_id:
            thread_id = f"email_{lead.hubspot_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Build graph if needed
        if self._graph is None:
            self._graph = self._build_graph()

        # Compile with checkpointing (required for approval workflow)
        checkpointer = get_checkpointer()
        compiled = self._graph.compile(
            checkpointer=checkpointer,
            interrupt_before=["parse_output"],  # Pause before finalizing
        )

        # Initial state
        initial_state = self._prepare_initial_state(
            lead, research_brief, persona, email_type, sequence_step
        )

        config = {"configurable": {"thread_id": thread_id}}

        # Run until interrupt
        result = await compiled.ainvoke(cast(Any, initial_state), config=cast(Any, config))

        return {
            "thread_id": thread_id,
            "email_preview": result.get("email_body", ""),
            "subject_preview": result.get("subject_line", ""),
            "lead_email": lead.email,
            "lead_company": lead.company,
            "status": "pending_approval",
        }

    async def approve(
        self,
        thread_id: str,
        approved: bool = True,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        """
        Approve or reject a pending email.

        Args:
            thread_id: Thread ID of the pending email
            approved: Whether the email is approved
            feedback: Optional feedback for rejection

        Returns:
            Final result with approval status
        """
        if self._graph is None:
            self._graph = self._build_graph()

        checkpointer = get_checkpointer()
        compiled = self._graph.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": thread_id}}

        if approved:
            # Resume and complete the workflow
            result = await compiled.ainvoke(cast(Any, None), config=cast(Any, config))
            return {
                **self._extract_result(result),
                "approved": True,
                "thread_id": thread_id,
            }
        else:
            # Return rejection without completing
            return {
                "subject_line": "",
                "email_body": "",
                "follow_up_note": None,
                "approved": False,
                "rejection_reason": feedback,
                "thread_id": thread_id,
            }

    async def stream(
        self,
        lead: Lead,
        research_brief: ResearchBrief | None = None,
        persona: dict[str, Any] | None = None,
        email_type: str = "pattern_interrupt",
        sequence_step: int = 1,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream email generation progress.

        Yields progress events as each node completes.

        Args:
            lead: Target lead
            research_brief: Research intelligence (optional)
            persona: Persona data (optional)
            email_type: Type of email
            sequence_step: Current sequence step (1-4)

        Yields:
            Progress events with node name, updates, and timestamp
        """
        if self._graph is None:
            self._graph = self._build_graph()

        compiled = self._graph.compile()
        initial_state = self._prepare_initial_state(
            lead, research_brief, persona, email_type, sequence_step
        )

        async for event in compiled.astream(
            cast(Any, initial_state),
            stream_mode="updates",
        ):
            node_name = list(event.keys())[0] if event else None

            yield {
                "node": node_name,
                "updates": event.get(node_name, {}) if node_name else {},
                "timestamp": datetime.utcnow().isoformat(),
            }


# Singleton instance
email_personalization_agent = EmailPersonalizationAgent()
