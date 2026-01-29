"""Qualification Agent for scoring leads against ICP criteria.

Scores leads using Tim's 5-dimension weighted ICP criteria:
- Company Size (25%)
- Industry Vertical (20%)
- Use Case Fit (25%)
- Tech Stack Signals (15%)
- Buying Authority (15%)

Tier Thresholds (0-100 weighted scale):
- Tier 1 (70+): Priority sequence, AE involvement early
- Tier 2 (50-69): Standard sequence
- Tier 3 (30-49): Light touch, marketing nurture
- Not ICP (<30): Disqualify

Features:
- PostgresSaver checkpointing for state persistence
- Streaming support for progress updates
- Thread ID support for workflow tracking
"""

from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from app.data.lead_schemas import Lead
from app.services.langgraph.checkpointing import get_checkpointer
from app.services.langgraph.states import (
    DimensionScore,
    ICPScoreBreakdown,
    QualificationState,
)
from app.services.langgraph.tools.qualification_tools import (
    WEIGHT_BUYING_AUTHORITY,
    WEIGHT_COMPANY_SIZE,
    WEIGHT_INDUSTRY_VERTICAL,
    WEIGHT_TECH_STACK,
    WEIGHT_USE_CASE_FIT,
    assign_tier,
    calculate_weighted_score,
    classify_buying_authority,
    classify_company_size,
    classify_tech_stack,
    classify_use_case,
    classify_vertical,
    determine_next_action,
)
from app.services.langgraph.tools.research_tools import (
    enrich_from_apollo,
)
from langgraph.graph import END, StateGraph


class QualificationAgent:
    """
    Agent for qualifying leads against ICP criteria.

    Flow: gather_data → [needs_inference?] → score_dimensions → calculate_final → recommend_action

    Uses LangGraph StateGraph for orchestration.
    """

    def __init__(self):
        """Initialize the agent."""
        self._graph: StateGraph | None = None

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        graph = StateGraph(QualificationState)

        # Add nodes
        graph.add_node("gather_data", self._gather_data_node)
        graph.add_node("score_dimensions", self._score_dimensions_node)
        graph.add_node("calculate_final", self._calculate_final_node)
        graph.add_node("recommend_action", self._recommend_action_node)

        # Define edges
        graph.set_entry_point("gather_data")
        graph.add_edge("gather_data", "score_dimensions")
        graph.add_edge("score_dimensions", "calculate_final")
        graph.add_edge("calculate_final", "recommend_action")
        graph.add_edge("recommend_action", END)

        return graph

    async def _gather_data_node(
        self, state: QualificationState
    ) -> dict[str, Any]:
        """
        Gather enrichment data for qualification.

        If skip_enrichment is True, uses provided data.
        Otherwise, calls Apollo API.
        """
        lead = state["lead"]
        skip_enrichment = state.get("skip_enrichment", False)

        # If we already have data or should skip enrichment
        if skip_enrichment:
            return {
                "apollo_data": state.get("apollo_data"),
            }

        # Run Apollo enrichment
        try:
            apollo_data = await enrich_from_apollo(lead.email)
        except Exception:
            apollo_data = None

        # Try to detect persona from title
        persona_match = self._detect_persona(lead, apollo_data)

        return {
            "apollo_data": apollo_data,
            "persona_match": persona_match,
        }

    def _detect_persona(
        self, lead: Lead, apollo_data: dict[str, Any] | None
    ) -> str | None:
        """
        Detect persona match from lead data.

        Maps job titles to known personas.
        """
        title = lead.title or ""
        if apollo_data:
            title = apollo_data.get("title", title)

        title_lower = title.lower()

        # Persona detection based on title keywords
        if any(kw in title_lower for kw in ["av director", "av manager", "audiovisual"]):
            return "AV Director"
        elif any(kw in title_lower for kw in ["l&d", "learning", "training director"]):
            return "L&D Director"
        elif any(kw in title_lower for kw in ["technical director", "td", "broadcast"]):
            return "Technical Director"
        elif any(kw in title_lower for kw in ["simulation", "sim lab", "sim center"]):
            return "Simulation Director"
        elif any(kw in title_lower for kw in ["court", "clerk of court"]):
            return "Court Administrator"
        elif any(kw in title_lower for kw in ["communications", "corporate comm"]):
            return "Corporate Communications Director"
        elif any(kw in title_lower for kw in ["ehs", "safety", "environmental health"]):
            return "EHS Manager"
        elif any(kw in title_lower for kw in ["law firm", "legal it", "legal tech"]):
            return "Law Firm IT"

        return None

    async def _score_dimensions_node(
        self, state: QualificationState
    ) -> dict[str, Any]:
        """
        Score all 5 ICP dimensions.

        Uses qualification tools to classify each dimension.
        """
        lead = state["lead"]
        apollo_data = state.get("apollo_data")
        persona_match = state.get("persona_match")

        # Track missing info
        missing_info: list[str] = []

        # 1. Company Size (from Apollo)
        employees = None
        if apollo_data:
            employees = apollo_data.get("employees")
        if employees is None:
            missing_info.append("company_size")

        size_category, size_score, size_reason = classify_company_size(employees)
        company_size: DimensionScore = {
            "category": size_category,
            "raw_score": size_score,
            "weighted_score": size_score * WEIGHT_COMPANY_SIZE * 10,
            "reason": size_reason,
            "confidence": 1.0 if employees else 0.3,
        }

        # 2. Industry Vertical (from Apollo)
        industry = None
        if apollo_data:
            industry = apollo_data.get("industry")

        vert_category, vert_score, vert_reason = classify_vertical(
            industry, lead.company, inferred=None
        )

        # Boost confidence if we have industry data
        vert_confidence = 1.0 if industry else 0.5
        if not industry:
            missing_info.append("industry_vertical")

        industry_vertical: DimensionScore = {
            "category": vert_category,
            "raw_score": vert_score,
            "weighted_score": vert_score * WEIGHT_INDUSTRY_VERTICAL * 10,
            "reason": vert_reason,
            "confidence": vert_confidence,
        }

        # 3. Use Case Fit
        tech_stack = None
        if apollo_data:
            tech_stack = apollo_data.get("tech_stack")

        use_category, use_score, use_reason = classify_use_case(
            persona=persona_match,
            vertical=vert_category,
            title=lead.title or (apollo_data or {}).get("title"),
            tech_stack=tech_stack,
        )

        use_case_fit: DimensionScore = {
            "category": use_category,
            "raw_score": use_score,
            "weighted_score": use_score * WEIGHT_USE_CASE_FIT * 10,
            "reason": use_reason,
            "confidence": 1.0 if persona_match else 0.6,
        }

        # 4. Tech Stack Signals
        tech_category, tech_score, tech_reason = classify_tech_stack(
            tech_stack, apollo_data
        )

        if not tech_stack:
            missing_info.append("tech_stack")

        tech_stack_signals: DimensionScore = {
            "category": tech_category,
            "raw_score": tech_score,
            "weighted_score": tech_score * WEIGHT_TECH_STACK * 10,
            "reason": tech_reason,
            "confidence": 1.0 if tech_stack else 0.4,
        }

        # 5. Buying Authority
        title = lead.title or (apollo_data or {}).get("title")
        seniority = (apollo_data or {}).get("seniority")

        auth_category, auth_score, auth_reason = classify_buying_authority(
            title, seniority, apollo_data
        )

        if not title and not seniority:
            missing_info.append("buying_authority")

        buying_authority: DimensionScore = {
            "category": auth_category,
            "raw_score": auth_score,
            "weighted_score": auth_score * WEIGHT_BUYING_AUTHORITY * 10,
            "reason": auth_reason,
            "confidence": 1.0 if seniority else (0.7 if title else 0.3),
        }

        # Build score breakdown
        score_breakdown: ICPScoreBreakdown = {
            "company_size": company_size,
            "industry_vertical": industry_vertical,
            "use_case_fit": use_case_fit,
            "tech_stack_signals": tech_stack_signals,
            "buying_authority": buying_authority,
        }

        return {
            "score_breakdown": score_breakdown,
            "missing_info": missing_info,
        }

    async def _calculate_final_node(
        self, state: QualificationState
    ) -> dict[str, Any]:
        """
        Calculate final weighted score and assign tier.
        """
        score_breakdown = state["score_breakdown"]
        missing_info = state.get("missing_info", [])

        # Calculate total weighted score
        total_score = calculate_weighted_score(score_breakdown)

        # Assign tier
        tier = assign_tier(total_score)

        # Calculate overall confidence
        confidences = [
            score_breakdown["company_size"]["confidence"],
            score_breakdown["industry_vertical"]["confidence"],
            score_breakdown["use_case_fit"]["confidence"],
            score_breakdown["tech_stack_signals"]["confidence"],
            score_breakdown["buying_authority"]["confidence"],
        ]
        avg_confidence = sum(confidences) / len(confidences)

        # Penalize confidence if we have missing info
        if missing_info:
            avg_confidence *= 0.8 ** len(missing_info)

        return {
            "total_score": total_score,
            "tier": tier,
            "confidence": min(avg_confidence, 1.0),
        }

    async def _recommend_action_node(
        self, state: QualificationState
    ) -> dict[str, Any]:
        """
        Determine recommended next action based on tier.
        """
        tier = state["tier"]
        missing_info = state.get("missing_info", [])
        confidence = state.get("confidence", 0.5)

        next_action = determine_next_action(tier, missing_info, confidence)

        return {
            "next_action": next_action,
        }

    def _prepare_initial_state(
        self,
        lead: Lead,
        enrichment_data: dict[str, Any] | None = None,
        skip_enrichment: bool = False,
    ) -> QualificationState:
        """Prepare initial state for qualification workflow."""
        apollo_data = None
        if enrichment_data:
            apollo_data = enrichment_data.get("apollo")

        return {
            "lead": lead,
            "skip_enrichment": skip_enrichment,
            "apollo_data": apollo_data,
            "persona_match": None,
            "inferred_company_size": None,
            "inferred_vertical": None,
            "inferred_use_case": None,
            "score_breakdown": None,
            "total_score": 0.0,
            "tier": None,
            "confidence": 0.0,
            "next_action": None,
            "missing_info": [],
        }

    def _extract_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Extract final result from state."""
        return {
            "total_score": result.get("total_score", 0.0),
            "tier": result.get("tier"),
            "score_breakdown": result.get("score_breakdown"),
            "confidence": result.get("confidence", 0.0),
            "next_action": result.get("next_action"),
            "missing_info": result.get("missing_info", []),
            "persona_match": result.get("persona_match"),
        }

    async def run(
        self,
        lead: Lead,
        enrichment_data: dict[str, Any] | None = None,
        skip_enrichment: bool = False,
        thread_id: str | None = None,
        use_checkpointing: bool = False,
    ) -> dict[str, Any]:
        """
        Run lead qualification and return score + tier.

        Args:
            lead: Lead to qualify
            enrichment_data: Optional pre-fetched enrichment data
                {"apollo": {...}}
            skip_enrichment: If True, don't call enrichment APIs
            thread_id: Optional thread ID for checkpointing
            use_checkpointing: If True, enable persistent checkpointing

        Returns:
            Dict with total_score, tier, score_breakdown, confidence, next_action, missing_info
        """
        # Build graph if needed
        if self._graph is None:
            self._graph = self._build_graph()

        # Compile with optional checkpointing
        checkpointer = get_checkpointer() if use_checkpointing else None
        compiled = self._graph.compile(checkpointer=checkpointer)

        # Prepare initial state
        initial_state = self._prepare_initial_state(lead, enrichment_data, skip_enrichment)

        # Prepare config with optional thread_id
        config: dict[str, Any] = {}
        if thread_id:
            config = {"configurable": {"thread_id": thread_id}}

        # Run the graph
        result = await compiled.ainvoke(initial_state, config=config if config else None)

        return self._extract_result(result)

    async def stream(
        self,
        lead: Lead,
        enrichment_data: dict[str, Any] | None = None,
        skip_enrichment: bool = False,
        thread_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream qualification progress updates.

        Yields progress events as each node completes, useful for
        real-time UI updates via SSE.

        Args:
            lead: Lead to qualify
            enrichment_data: Optional pre-fetched enrichment data
            skip_enrichment: If True, don't call enrichment APIs
            thread_id: Optional thread ID for checkpointing

        Yields:
            Progress events with node name, updates, and timestamp
        """
        # Build graph if needed
        if self._graph is None:
            self._graph = self._build_graph()

        # Compile (optionally with checkpointing)
        checkpointer = get_checkpointer() if thread_id else None
        compiled = self._graph.compile(checkpointer=checkpointer)

        # Prepare initial state
        initial_state = self._prepare_initial_state(lead, enrichment_data, skip_enrichment)

        # Prepare config
        config: dict[str, Any] = {}
        if thread_id:
            config = {"configurable": {"thread_id": thread_id}}

        # Stream with updates mode
        async for event in compiled.astream(
            initial_state,
            config=config if config else None,
            stream_mode="updates",
        ):
            # Extract node name from event keys
            node_name = list(event.keys())[0] if event else None

            yield {
                "node": node_name,
                "updates": event.get(node_name, {}) if node_name else {},
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def resume(
        self,
        thread_id: str,
        human_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Resume a paused qualification workflow.

        Used for human-in-the-loop workflows where the agent
        was interrupted waiting for input.

        Args:
            thread_id: Thread ID of paused workflow
            human_input: Optional human input to provide

        Returns:
            Final qualification result
        """
        if self._graph is None:
            self._graph = self._build_graph()

        checkpointer = get_checkpointer()
        compiled = self._graph.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": thread_id}}

        # Resume with human input
        result = await compiled.ainvoke(human_input, config=config)

        return self._extract_result(result)
