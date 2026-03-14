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
from typing import Any, cast

from langchain_core.messages import HumanMessage, SystemMessage

from app.data.lead_schemas import Lead
from app.services.langgraph.checkpointing import get_checkpointer
from app.services.langgraph.states import (
    DimensionScore,
    ICPScoreBreakdown,
    QualificationState,
    QualificationTier,
    TierDecision,
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
from app.services.llm.clients import get_llm_router
from langgraph.graph import END, StateGraph


class QualificationAgent:
    """
    Agent for qualifying leads against ICP criteria.

    Flow: gather_data → [needs_inference?] → score_dimensions → calculate_final → recommend_action

    Uses LangGraph StateGraph for orchestration.
    Extended thinking is used for edge cases with low confidence or borderline scores.
    """

    # Borderline score ranges that warrant extended thinking
    BORDERLINE_RANGES = [
        (28, 32),   # Not ICP / Tier 3 boundary
        (48, 52),   # Tier 3 / Tier 2 boundary
        (68, 72),   # Tier 2 / Tier 1 boundary
    ]

    # Confidence threshold below which extended thinking is used
    LOW_CONFIDENCE_THRESHOLD = 0.6

    def __init__(self) -> None:
        """Initialize the agent."""
        self._graph: StateGraph[QualificationState] | None = None
        self._router = get_llm_router()

    def _is_edge_case(self, total_score: float, confidence: float) -> bool:
        """
        Determine if this qualification requires extended thinking.

        Edge cases include:
        - Borderline scores near tier thresholds
        - Low overall confidence in classification

        Args:
            total_score: The weighted qualification score (0-100)
            confidence: The confidence level (0.0-1.0)

        Returns:
            True if extended thinking should be used
        """
        # Low confidence always triggers extended thinking
        if confidence < self.LOW_CONFIDENCE_THRESHOLD:
            return True

        # Check if score is in a borderline range
        return any(low <= total_score <= high for low, high in self.BORDERLINE_RANGES)

    def _build_graph(self) -> StateGraph[QualificationState]:
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

    async def _apply_extended_thinking(
        self,
        lead: Lead,
        score_breakdown: ICPScoreBreakdown,
        total_score: float,
        initial_tier: QualificationTier,
        confidence: float,
    ) -> tuple[QualificationTier, str]:
        """
        Use extended thinking model for nuanced tier decision on edge cases.

        Extended thinking gives Claude a reasoning scratchpad to work through
        ambiguous signals before making a final determination. Uses
        with_structured_output() for reliable tier extraction.

        Args:
            lead: The lead being qualified
            score_breakdown: Dimension scores
            total_score: Calculated weighted score
            initial_tier: Tier from simple threshold assignment
            confidence: Overall confidence level

        Returns:
            Tuple of (final_tier, reasoning_summary)
        """
        model = self._router.claude_with_thinking

        system_prompt = """You are an ICP qualification expert for Epiphan Video.
Your task is to make a nuanced tier determination for a borderline lead.

Consider:
1. Which dimensions have low confidence and why
2. Patterns that suggest higher/lower fit than the score indicates
3. Missing information that would change the classification
4. Industry and persona signals that may not be captured in raw scores

Tier definitions:
- Tier 1 (70+): Priority sequence, AE involvement early - strong fit
- Tier 2 (50-69): Standard sequence - good fit with some gaps
- Tier 3 (30-49): Light touch, marketing nurture - potential fit needs development
- Not ICP (<30): Disqualify - poor fit"""

        # Build context about the lead and scores
        lead_context = f"""
Lead: {lead.email}
Company: {lead.company or 'Unknown'}
Title: {lead.title or 'Unknown'}
Current Score: {total_score:.1f}
Initial Tier: {initial_tier.value}
Confidence: {confidence:.2f}

Score Breakdown:
- Company Size: {score_breakdown['company_size']['raw_score']}/10 ({score_breakdown['company_size']['category']}) - {score_breakdown['company_size']['reason']}
- Industry: {score_breakdown['industry_vertical']['raw_score']}/10 ({score_breakdown['industry_vertical']['category']}) - {score_breakdown['industry_vertical']['reason']}
- Use Case: {score_breakdown['use_case_fit']['raw_score']}/10 ({score_breakdown['use_case_fit']['category']}) - {score_breakdown['use_case_fit']['reason']}
- Tech Stack: {score_breakdown['tech_stack_signals']['raw_score']}/10 ({score_breakdown['tech_stack_signals']['category']}) - {score_breakdown['tech_stack_signals']['reason']}
- Authority: {score_breakdown['buying_authority']['raw_score']}/10 ({score_breakdown['buying_authority']['category']}) - {score_breakdown['buying_authority']['reason']}
"""

        try:
            structured_model = model.with_structured_output(TierDecision)
            decision = cast(TierDecision, await structured_model.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=lead_context),
            ]))

            return decision.tier, decision.reasoning

        except Exception:
            # On any error, fall back to initial tier
            return initial_tier, ""

    async def _calculate_final_node(
        self, state: QualificationState
    ) -> dict[str, Any]:
        """
        Calculate final weighted score and assign tier.

        Uses extended thinking for edge cases with borderline scores
        or low confidence to improve accuracy.
        """
        score_breakdown = state["score_breakdown"]
        missing_info = state.get("missing_info", [])
        lead = state["lead"]

        # Ensure score_breakdown exists
        if not score_breakdown:
            return {
                "total_score": 0.0,
                "tier": QualificationTier.NOT_ICP,
                "confidence": 0.0,
            }

        # Calculate total weighted score
        total_score = calculate_weighted_score(score_breakdown)

        # Assign initial tier
        initial_tier = assign_tier(total_score)

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

        final_confidence = min(avg_confidence, 1.0)

        # Use extended thinking for edge cases
        final_tier = initial_tier
        extended_reasoning = None

        if self._is_edge_case(total_score, final_confidence):
            final_tier, extended_reasoning = await self._apply_extended_thinking(
                lead=lead,
                score_breakdown=score_breakdown,
                total_score=total_score,
                initial_tier=initial_tier,
                confidence=final_confidence,
            )

        result: dict[str, Any] = {
            "total_score": total_score,
            "tier": final_tier,
            "confidence": final_confidence,
        }

        # Include extended reasoning if tier was changed
        if extended_reasoning and final_tier != initial_tier:
            result["extended_reasoning"] = extended_reasoning
            result["tier_adjusted"] = True

        return result

    async def _recommend_action_node(
        self, state: QualificationState
    ) -> dict[str, Any]:
        """
        Determine recommended next action based on tier.
        """
        tier = state["tier"] or QualificationTier.NOT_ICP
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
        result = await compiled.ainvoke(cast(Any, initial_state), config=cast(Any, config) if config else None)

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
            cast(Any, initial_state),
            config=cast(Any, config) if config else None,
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
        result = await compiled.ainvoke(cast(Any, human_input), config=cast(Any, config))

        return self._extract_result(result)
