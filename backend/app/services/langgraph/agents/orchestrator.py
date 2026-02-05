"""Master Orchestrator Agent for coordinating all sub-agents.

This agent implements the two-phase parallel execution pattern:
1. Research Phase: Run research, qualification, enrichment IN PARALLEL
2. Outreach Phase: Run script, email, competitor intel IN PARALLEL

Architecture based on:
- Anthropic's two-agent system pattern (harnesses blog)
- DeepAgents task delegation model
- Claude 4 parallel tool execution best practices
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any, Literal, cast

from app.data.lead_schemas import Lead
from app.services.langgraph.agents.email_personalization import (
    email_personalization_agent,
)
from app.services.langgraph.agents.lead_research import lead_research_agent
from app.services.langgraph.agents.qualification import QualificationAgent
from app.services.langgraph.agents.script_selection import script_selection_agent
from app.services.langgraph.memory import semantic_memory
from app.services.langgraph.states import (
    GateDecision,
    OrchestratorState,
    PhaseResult,
    QualificationTier,
    ResearchBrief,
    SynthesisResult,
)
from app.services.langgraph.tracing import trace_agent, tracing_metrics
from langgraph.graph import END, StateGraph


class MasterOrchestratorAgent:
    """
    Master agent that coordinates all sub-agents through parallel phases.

    Execution Flow:
    1. parallel_research: Run 3 agents concurrently (research, qualify, enrich)
    2. review_gate_1: Validate data completeness and quality
    3. Route based on tier:
       - Tier 1/2: Continue to outreach
       - Not ICP: Archive (skip outreach)
    4. parallel_outreach: Run 3 agents concurrently (script, email, competitor)
    5. review_gate_2: Final quality check
    6. sync: Push results to HubSpot

    Benefits:
    - 50-70% time reduction via parallel execution
    - Quality gates prevent wasted effort on bad data
    - Tier-based routing optimizes resource allocation
    """

    def __init__(self) -> None:
        """Initialize the orchestrator with sub-agents and memory."""
        self._graph: StateGraph[OrchestratorState] | None = None
        self._research_agent = lead_research_agent
        self._qualification_agent = QualificationAgent()
        self._script_agent = script_selection_agent
        self._email_agent = email_personalization_agent
        self._memory = semantic_memory

    def _build_graph(self) -> StateGraph[OrchestratorState]:
        """Build the LangGraph state graph with parallel nodes."""
        graph: StateGraph[OrchestratorState] = StateGraph(OrchestratorState)

        # === Phase 1: Parallel Research ===
        graph.add_node("parallel_research", self._parallel_research_node)

        # === Synthesis Node (NEW): Analyze research and identify gaps ===
        graph.add_node("synthesis", self._synthesis_node)

        # === Gate 1: Data Quality ===
        graph.add_node("review_gate_1", self._review_gate_1_node)

        # === Phase 2: Parallel Outreach (conditional) ===
        graph.add_node("parallel_outreach", self._parallel_outreach_node)

        # === Gate 2: Output Quality ===
        graph.add_node("review_gate_2", self._review_gate_2_node)

        # === Phase 3: Sync ===
        graph.add_node("sync_to_hubspot", self._sync_node)

        # === Archive (for not ICP) ===
        graph.add_node("archive", self._archive_node)

        # === Define Edges ===
        graph.set_entry_point("parallel_research")
        graph.add_edge("parallel_research", "synthesis")
        graph.add_edge("synthesis", "review_gate_1")

        # Conditional routing based on tier after gate 1
        graph.add_conditional_edges(
            "review_gate_1",
            self._route_by_tier,
            {
                "tier_1": "parallel_outreach",
                "tier_2": "parallel_outreach",
                "tier_3": "parallel_outreach",  # Light touch but still process
                "not_icp": "archive",
            },
        )

        graph.add_edge("parallel_outreach", "review_gate_2")

        # Conditional routing after gate 2
        graph.add_conditional_edges(
            "review_gate_2",
            self._route_after_gate_2,
            {
                "proceed": "sync_to_hubspot",
                "skip_sync": END,
            },
        )

        graph.add_edge("sync_to_hubspot", END)
        graph.add_edge("archive", END)

        return graph

    # =========================================================================
    # Phase Nodes
    # =========================================================================

    async def _parallel_research_node(
        self, state: OrchestratorState
    ) -> dict[str, Any]:
        """
        Run research, qualification, enrichment IN PARALLEL.

        This is the key throughput optimization - these 3 operations
        are independent and can execute concurrently.

        Also queries semantic memory for similar lead patterns to
        inform research and qualification strategies.
        """
        start_time = time.time()
        lead = state["lead"]
        errors: list[str] = []

        # Query semantic memory for similar lead patterns
        # This helps identify successful approaches for similar leads
        similar_patterns: list[dict[str, Any]] = []
        try:
            query = f"{lead.company or ''} {lead.title or ''} {lead.industry or ''}".strip()
            if query:
                similar_patterns = await self._memory.find_similar_patterns(
                    query=query,
                    limit=3,
                )
        except Exception:
            # Memory query failure is non-fatal
            pass

        # Launch all 3 tasks in parallel
        research_task = self._run_research_agent(lead)
        qualification_task = self._run_qualification_agent(lead)
        # Note: enrichment is handled within research agent

        results = await asyncio.gather(
            research_task,
            qualification_task,
            return_exceptions=True,
        )

        raw_research, raw_qualification = results

        # Handle exceptions with proper typing
        research_result: dict[str, Any] | None = None
        qualification_result: dict[str, Any] | None = None

        if isinstance(raw_research, BaseException):
            errors.append(f"Research failed: {raw_research}")
        elif isinstance(raw_research, dict):
            research_result = raw_research

        if isinstance(raw_qualification, BaseException):
            errors.append(f"Qualification failed: {raw_qualification}")
        elif isinstance(raw_qualification, dict):
            qualification_result = raw_qualification

        # Extract tier and key flags
        tier = self._extract_tier(qualification_result)
        has_phone = self._check_has_phone(research_result)
        is_atl = self._check_is_atl(qualification_result)

        duration_ms = (time.time() - start_time) * 1000

        phase_result: PhaseResult = {
            "phase_name": "parallel_research",
            "status": "success" if not errors else "partial",
            "duration_ms": duration_ms,
            "errors": errors,
            "data": {
                "research": bool(research_result),
                "qualification": bool(qualification_result),
                "similar_patterns_found": len(similar_patterns),
            },
        }

        return {
            "research_brief": research_result.get("research_brief") if research_result else None,
            "qualification_result": qualification_result,
            "enrichment_data": research_result.get("enrichment_data") if research_result else None,
            "tier": tier,
            "has_phone": has_phone,
            "is_atl": is_atl,
            "current_phase": "gate_1",
            "phase_results": [phase_result],
            "errors": errors,
        }

    async def _synthesis_node(
        self, state: OrchestratorState
    ) -> dict[str, Any]:
        """
        Synthesize research findings and identify intelligence gaps.

        This node runs after parallel research to:
        1. Consolidate findings from research and qualification
        2. Identify missing information (gaps)
        3. Assess contact quality
        4. Calculate confidence score

        The synthesis helps prioritize outreach approach and identifies
        data gaps that may need manual research.
        """
        start_time = time.time()

        research_brief = state.get("research_brief")
        qualification_result = state.get("qualification_result")
        enrichment_data = state.get("enrichment_data")
        tier = state.get("tier")
        has_phone = state.get("has_phone")

        # Identify intelligence gaps
        intelligence_gaps: list[str] = []

        if not research_brief:
            intelligence_gaps.append("missing_research_brief")
        elif not research_brief.get("company_overview"):
            intelligence_gaps.append("missing_company_overview")

        if not qualification_result:
            intelligence_gaps.append("missing_qualification")
        elif not qualification_result.get("persona_match"):
            intelligence_gaps.append("missing_persona_match")

        if not enrichment_data:
            intelligence_gaps.append("missing_enrichment_data")
        else:
            if not enrichment_data.get("title"):
                intelligence_gaps.append("missing_title")
            if not enrichment_data.get("industry"):
                intelligence_gaps.append("missing_industry")

        # PHONES ARE GOLD - flag missing phone prominently
        if not has_phone:
            intelligence_gaps.append("missing_phone_critical")

        # Assess contact quality
        contact_quality = self._assess_contact_quality(
            enrichment_data=enrichment_data,
            qualification_result=qualification_result,
            has_phone=has_phone,
        )

        # Calculate confidence score based on data completeness
        confidence_score = self._calculate_synthesis_confidence(
            research_brief=research_brief,
            qualification_result=qualification_result,
            enrichment_data=enrichment_data,
            intelligence_gaps=intelligence_gaps,
        )

        # Generate recommended actions based on gaps
        recommended_actions = self._generate_recommended_actions(
            intelligence_gaps=intelligence_gaps,
            tier=tier,
            contact_quality=contact_quality,
        )

        synthesis: SynthesisResult = {
            "company_summary": (
                research_brief.get("company_overview", "")[:500]
                if research_brief else None
            ),
            "qualification_tier": tier.value if tier else None,
            "contact_quality": contact_quality,
            "intelligence_gaps": intelligence_gaps,
            "confidence_score": confidence_score,
            "recommended_actions": recommended_actions,
        }

        duration_ms = (time.time() - start_time) * 1000

        phase_result: PhaseResult = {
            "phase_name": "synthesis",
            "status": "success",
            "duration_ms": duration_ms,
            "errors": [],
            "data": {
                "gaps_count": len(intelligence_gaps),
                "contact_quality": contact_quality,
                "confidence": confidence_score,
            },
        }

        existing_phases = state.get("phase_results", [])

        return {
            "synthesis": synthesis,
            "current_phase": "gate_1",
            "phase_results": existing_phases + [phase_result],
        }

    def _assess_contact_quality(
        self,
        enrichment_data: dict[str, Any] | None,
        qualification_result: dict[str, Any] | None,
        has_phone: bool,
    ) -> str:
        """
        Assess contact quality based on available data.

        Returns: "high", "medium", or "low"
        """
        score = 0

        # Enrichment data quality
        if enrichment_data:
            if enrichment_data.get("title"):
                score += 2
            if enrichment_data.get("linkedin_url"):
                score += 1
            if enrichment_data.get("company"):
                score += 1

        # Phone is critical for sales
        if has_phone:
            score += 3

        # Qualification data
        if qualification_result:
            if qualification_result.get("persona_match"):
                score += 2
            tier = qualification_result.get("tier")
            if tier and tier != "not_icp":
                score += 1

        # Score thresholds
        if score >= 8:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"

    def _calculate_synthesis_confidence(
        self,
        research_brief: ResearchBrief | None,
        qualification_result: dict[str, Any] | None,
        enrichment_data: dict[str, Any] | None,
        intelligence_gaps: list[str],
    ) -> float:
        """
        Calculate overall confidence in synthesized data.

        Returns: 0.0 to 1.0 confidence score
        """
        # Start with base confidence
        confidence = 0.5

        # Research brief adds confidence
        if research_brief:
            confidence += 0.15
            if research_brief.get("talking_points"):
                confidence += 0.1

        # Qualification adds confidence
        if qualification_result:
            confidence += 0.15

        # Enrichment adds confidence
        if enrichment_data:
            confidence += 0.1

        # Deduct for each gap
        gap_penalty = len(intelligence_gaps) * 0.05
        confidence -= gap_penalty

        # Clamp to valid range
        return max(0.0, min(1.0, confidence))

    def _generate_recommended_actions(
        self,
        intelligence_gaps: list[str],
        tier: QualificationTier | None,
        contact_quality: str,
    ) -> list[str]:
        """
        Generate recommended next actions based on synthesis.
        """
        actions: list[str] = []

        # Phone-related actions (PHONES ARE GOLD!)
        if "missing_phone_critical" in intelligence_gaps:
            actions.append("Manual phone lookup via LinkedIn/company website")
            actions.append("Use Apollo phone reveal if budget permits")

        # Title-related actions
        if "missing_title" in intelligence_gaps:
            actions.append("Verify job title via LinkedIn")

        # Research gaps
        if "missing_research_brief" in intelligence_gaps:
            actions.append("Conduct manual company research")

        # Contact quality actions
        if contact_quality == "low":
            actions.append("Consider re-enrichment with alternative sources")

        # Tier-based actions
        if tier == QualificationTier.TIER_1:
            actions.insert(0, "PRIORITY: Fast-track to outreach sequence")
        elif tier == QualificationTier.TIER_2:
            actions.append("Standard sequence - good fit")
        elif tier == QualificationTier.NOT_ICP:
            actions.append("Archive - does not meet ICP criteria")

        return actions

    async def _review_gate_1_node(
        self, state: OrchestratorState
    ) -> dict[str, Any]:
        """
        Review Gate 1: Validate data completeness before outreach.

        Checks:
        - Has qualification result
        - Has research brief OR enrichment data
        - Phone number available (CRITICAL for sales)
        """
        passed_checks: list[str] = []
        failed_checks: list[str] = []

        # Check 1: Qualification completed
        if state.get("qualification_result"):
            passed_checks.append("qualification_completed")
        else:
            failed_checks.append("qualification_missing")

        # Check 2: Has research or enrichment data
        if state.get("research_brief") or state.get("enrichment_data"):
            passed_checks.append("research_data_available")
        else:
            failed_checks.append("no_research_data")

        # Check 3: Phone available (important but not blocking)
        if state.get("has_phone"):
            passed_checks.append("phone_available")
        else:
            # Warning but not a failed check - phones are GOLD but we can still proceed
            passed_checks.append("phone_missing_warning")

        # Gate passes if we have qualification and some research data
        gate_passes = (
            "qualification_completed" in passed_checks
            and "research_data_available" in passed_checks
        )

        tier = state.get("tier")
        next_phase = (
            "archive" if tier == QualificationTier.NOT_ICP else "outreach"
        ) if gate_passes else None

        gate_decision: GateDecision = {
            "proceed": gate_passes,
            "gate_name": "review_gate_1",
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "remediation": "Re-run enrichment" if not gate_passes else None,
            "next_phase": next_phase,
        }

        return {
            "gate_1_decision": gate_decision,
            "current_phase": "outreach" if gate_passes and tier != QualificationTier.NOT_ICP else "archive",
        }

    async def _parallel_outreach_node(
        self, state: OrchestratorState
    ) -> dict[str, Any]:
        """
        Run script selection, email generation, competitor intel IN PARALLEL.

        Only runs for qualified leads (Tier 1-3).
        """
        start_time = time.time()
        lead = state["lead"]
        research_brief = state.get("research_brief")
        qualification = state.get("qualification_result")
        errors: list[str] = []

        # Determine persona from qualification
        persona = self._extract_persona(qualification)

        # Launch all 3 tasks in parallel
        script_task = self._run_script_agent(lead, persona, research_brief)
        email_task = self._run_email_agent(lead, research_brief, persona)
        competitor_task = self._run_competitor_check(lead, research_brief)

        results = await asyncio.gather(
            script_task,
            email_task,
            competitor_task,
            return_exceptions=True,
        )

        script_result, email_result, competitor_result = results

        # Handle exceptions
        if isinstance(script_result, Exception):
            errors.append(f"Script selection failed: {script_result}")
            script_result = None

        if isinstance(email_result, Exception):
            errors.append(f"Email generation failed: {email_result}")
            email_result = None

        if isinstance(competitor_result, Exception):
            errors.append(f"Competitor intel failed: {competitor_result}")
            competitor_result = None

        duration_ms = (time.time() - start_time) * 1000

        phase_result: PhaseResult = {
            "phase_name": "parallel_outreach",
            "status": "success" if not errors else "partial",
            "duration_ms": duration_ms,
            "errors": errors,
            "data": {
                "script": bool(script_result),
                "email": bool(email_result),
                "competitor": bool(competitor_result),
            },
        }

        existing_phases = state.get("phase_results", [])

        return {
            "script_result": script_result,
            "email_result": email_result,
            "competitor_intel": competitor_result,
            "current_phase": "gate_2",
            "phase_results": existing_phases + [phase_result],
            "errors": state.get("errors", []) + errors,
        }

    async def _review_gate_2_node(
        self, state: OrchestratorState
    ) -> dict[str, Any]:
        """
        Review Gate 2: Final quality check before sync.

        Checks:
        - At least one outreach asset generated
        - Script or email available for sales use
        """
        passed_checks: list[str] = []
        failed_checks: list[str] = []

        # Check 1: Script generated
        if state.get("script_result"):
            passed_checks.append("script_generated")
        else:
            failed_checks.append("script_missing")

        # Check 2: Email generated
        if state.get("email_result"):
            passed_checks.append("email_generated")
        else:
            failed_checks.append("email_missing")

        # Gate passes if we have at least a script OR email
        gate_passes = "script_generated" in passed_checks or "email_generated" in passed_checks

        gate_decision: GateDecision = {
            "proceed": gate_passes,
            "gate_name": "review_gate_2",
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "remediation": "Generate outreach content manually" if not gate_passes else None,
            "next_phase": "sync" if gate_passes else None,
        }

        return {
            "gate_2_decision": gate_decision,
            "current_phase": "sync" if gate_passes else "complete",
        }

    async def _sync_node(self, state: OrchestratorState) -> dict[str, Any]:
        """
        Sync results to HubSpot CRM and store successful patterns.

        Note: Actual HubSpot sync is handled by the caller or a separate
        service - this node prepares the data for sync.

        For Tier 1 and Tier 2 leads, stores the qualification pattern
        in semantic memory for future pattern matching.
        """
        start_time = time.time()

        # Prepare HubSpot update payload
        tier = state.get("tier")
        persona = self._extract_persona(state.get("qualification_result"))

        sync_result = {
            "lead_id": state["lead"].hubspot_id,
            "updates": {
                "tier": tier.value if tier else None,
                "is_atl": state.get("is_atl"),
                "has_phone": state.get("has_phone"),
                "persona": persona,
            },
            "assets": {
                "has_script": bool(state.get("script_result")),
                "has_email": bool(state.get("email_result")),
                "has_competitor_intel": bool(state.get("competitor_intel")),
            },
            "status": "ready_for_sync",
        }

        # Store successful patterns in semantic memory for learning
        # Only store Tier 1 and Tier 2 as successful patterns
        if tier in (QualificationTier.TIER_1, QualificationTier.TIER_2):
            try:
                qualification_result = state.get("qualification_result")
                score_breakdown = qualification_result.get("score_breakdown", {}) if qualification_result else {}

                # Identify success indicators based on what we know
                success_indicators: list[str] = []
                if state.get("has_phone"):
                    success_indicators.append("has_phone")
                if state.get("is_atl"):
                    success_indicators.append("is_atl_decision_maker")
                if state.get("email_result"):
                    success_indicators.append("email_generated")
                if state.get("script_result"):
                    success_indicators.append("script_generated")

                await self._memory.save_qualification_pattern(
                    tier=tier.value,
                    persona=persona or "unknown",
                    score_breakdown=score_breakdown,
                    success_indicators=success_indicators,
                )
            except Exception:
                # Memory save failure is non-fatal
                pass

        duration_ms = (time.time() - start_time) * 1000

        phase_result: PhaseResult = {
            "phase_name": "sync",
            "status": "success",
            "duration_ms": duration_ms,
            "errors": [],
            "data": sync_result,
        }

        existing_phases = state.get("phase_results", [])

        return {
            "hubspot_sync_result": sync_result,
            "current_phase": "complete",
            "phase_results": existing_phases + [phase_result],
        }

    async def _archive_node(self, state: OrchestratorState) -> dict[str, Any]:
        """Archive lead as not ICP - no outreach needed."""
        return {
            "current_phase": "complete",
            "hubspot_sync_result": {
                "lead_id": state["lead"].hubspot_id,
                "status": "archived",
                "reason": "not_icp",
            },
        }

    # =========================================================================
    # Routing Functions
    # =========================================================================

    def _route_by_tier(
        self, state: OrchestratorState
    ) -> Literal["tier_1", "tier_2", "tier_3", "not_icp"]:
        """Route based on qualification tier."""
        gate_decision = state.get("gate_1_decision")
        tier = state.get("tier")

        # If gate didn't pass, default to not_icp
        if not gate_decision or not gate_decision.get("proceed"):
            return "not_icp"

        if tier == QualificationTier.TIER_1:
            return "tier_1"
        elif tier == QualificationTier.TIER_2:
            return "tier_2"
        elif tier == QualificationTier.TIER_3:
            return "tier_3"
        else:
            return "not_icp"

    def _route_after_gate_2(
        self, state: OrchestratorState
    ) -> Literal["proceed", "skip_sync"]:
        """Route after gate 2 - proceed to sync or skip."""
        gate_decision = state.get("gate_2_decision")
        if gate_decision and gate_decision.get("proceed"):
            return "proceed"
        return "skip_sync"

    # =========================================================================
    # Sub-Agent Runners
    # =========================================================================

    async def _run_research_agent(self, lead: Lead) -> dict[str, Any]:
        """Run the lead research agent."""
        return await self._research_agent.run(lead, research_depth="deep")

    async def _run_qualification_agent(self, lead: Lead) -> dict[str, Any]:
        """Run the qualification agent."""
        return await self._qualification_agent.run(lead)

    async def _run_script_agent(
        self,
        lead: Lead,
        persona: str | None,
        _research_brief: ResearchBrief | None,
    ) -> dict[str, Any]:
        """Run the script selection agent."""
        return await self._script_agent.run(
            lead=lead,
            persona_match=persona,
            trigger="content_download",
            call_type="warm",
        )

    async def _run_email_agent(
        self,
        lead: Lead,
        research_brief: ResearchBrief | None,
        persona: str | None,
    ) -> dict[str, Any]:
        """Run the email personalization agent."""
        return await self._email_agent.run(
            lead=lead,
            research_brief=research_brief,
            persona={"name": persona} if persona else None,
            sequence_step=1,
            email_type="pattern_interrupt",
        )

    async def _run_competitor_check(
        self,
        _lead: Lead,
        research_brief: ResearchBrief | None,
    ) -> dict[str, Any] | None:
        """
        Check for competitor signals and gather intel.

        Returns None if no competitor signals detected.
        """
        # Simplified competitor check - look for tech stack signals
        tech_signals: list[str] = []
        if research_brief:
            talking_points = research_brief.get("talking_points", [])
            for point in talking_points:
                point_lower = point.lower() if isinstance(point, str) else ""
                if any(
                    comp in point_lower
                    for comp in ["zoom", "panopto", "kaltura", "teams", "vimeo"]
                ):
                    tech_signals.append(point)

        if tech_signals:
            return {
                "has_competitor": True,
                "signals": tech_signals,
                "recommendation": "Prepare competitive positioning",
            }
        return None

    # =========================================================================
    # Helper Functions
    # =========================================================================

    def _extract_tier(
        self, qualification_result: dict[str, Any] | None
    ) -> QualificationTier | None:
        """Extract tier from qualification result."""
        if not qualification_result:
            return None
        tier_value = qualification_result.get("tier")
        if isinstance(tier_value, QualificationTier):
            return tier_value
        if isinstance(tier_value, str):
            try:
                return QualificationTier(tier_value)
            except ValueError:
                return None
        return None

    def _check_has_phone(
        self, research_result: dict[str, Any] | None
    ) -> bool:
        """Check if phone number was enriched."""
        if not research_result:
            return False
        enrichment = research_result.get("enrichment_data", {})
        if not enrichment:
            return False
        # Check for any phone type
        return bool(
            enrichment.get("phone")
            or enrichment.get("mobile_phone")
            or enrichment.get("direct_dial")
        )

    def _check_is_atl(
        self, qualification_result: dict[str, Any] | None
    ) -> bool:
        """Check if lead is above-the-line decision maker."""
        if not qualification_result:
            return False
        return bool(qualification_result.get("is_atl", False))

    def _extract_persona(
        self, qualification_result: dict[str, Any] | None
    ) -> str | None:
        """Extract persona match from qualification result."""
        if not qualification_result:
            return None
        return qualification_result.get("persona_match")

    # =========================================================================
    # Public Interface
    # =========================================================================

    @trace_agent("master_orchestrator", metadata={"version": "1.0"})
    async def run(
        self,
        lead: Lead,
        process_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run the full orchestration pipeline for a lead.

        Args:
            lead: Lead to process
            process_config: Optional processing configuration

        Returns:
            Complete processing result with all phase outputs
        """
        start_time = time.time()

        # Build graph if needed
        if self._graph is None:
            self._graph = self._build_graph()

        # Compile the graph
        compiled = self._graph.compile()

        # Initial state
        initial_state: OrchestratorState = {
            "lead": lead,
            "process_config": process_config or {},
            "research_brief": None,
            "qualification_result": None,
            "enrichment_data": None,
            "synthesis": None,
            "gate_1_decision": None,
            "script_result": None,
            "email_result": None,
            "competitor_intel": None,
            "gate_2_decision": None,
            "hubspot_sync_result": None,
            "current_phase": "research",
            "phase_results": [],
            "total_duration_ms": 0.0,
            "errors": [],
            "tier": None,
            "has_phone": False,
            "is_atl": False,
        }

        # Run the graph
        result = await compiled.ainvoke(cast(Any, initial_state))

        # Calculate total duration
        total_duration_ms = (time.time() - start_time) * 1000

        result_tier = result.get("tier")
        tier_value = result_tier.value if result_tier else None

        # Record metrics for observability
        tracing_metrics.record(
            agent_name="master_orchestrator",
            duration_ms=total_duration_ms,
            success=not result.get("errors"),
            tier=tier_value,
        )

        return {
            "lead_id": lead.hubspot_id,
            "tier": tier_value,
            "is_atl": result.get("is_atl"),
            "has_phone": result.get("has_phone"),
            "research_brief": result.get("research_brief"),
            "qualification_result": result.get("qualification_result"),
            "synthesis": result.get("synthesis"),
            "script_result": result.get("script_result"),
            "email_result": result.get("email_result"),
            "competitor_intel": result.get("competitor_intel"),
            "hubspot_sync_result": result.get("hubspot_sync_result"),
            "gate_decisions": {
                "gate_1": result.get("gate_1_decision"),
                "gate_2": result.get("gate_2_decision"),
            },
            "phase_results": result.get("phase_results", []),
            "total_duration_ms": total_duration_ms,
            "errors": result.get("errors", []),
        }

    async def stream(
        self,
        lead: Lead,
        process_config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream orchestration progress with node-level updates.

        Yields progress events as each node completes, useful for
        real-time UI updates via SSE.

        Args:
            lead: Lead to process
            process_config: Optional processing configuration

        Yields:
            Progress events with node name, updates, and timestamp
        """
        from datetime import datetime, timezone

        # Build graph if needed
        if self._graph is None:
            self._graph = self._build_graph()

        # Compile the graph
        compiled = self._graph.compile()

        # Initial state
        initial_state: OrchestratorState = {
            "lead": lead,
            "process_config": process_config or {},
            "research_brief": None,
            "qualification_result": None,
            "enrichment_data": None,
            "synthesis": None,
            "gate_1_decision": None,
            "script_result": None,
            "email_result": None,
            "competitor_intel": None,
            "gate_2_decision": None,
            "hubspot_sync_result": None,
            "current_phase": "research",
            "phase_results": [],
            "total_duration_ms": 0.0,
            "errors": [],
            "tier": None,
            "has_phone": False,
            "is_atl": False,
        }

        # Stream with updates mode for node-level events
        async for event in compiled.astream(
            cast(Any, initial_state),
            stream_mode="updates",
        ):
            # Extract node name from event keys
            node_name = list(event.keys())[0] if event else None

            yield {
                "event_type": "node_update",
                "node": node_name,
                "updates": event.get(node_name, {}) if node_name else {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def stream_tokens(
        self,
        lead: Lead,
        process_config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream orchestration with token-level granularity.

        Uses astream_events(version="v2") for fine-grained events including:
        - on_chat_model_stream: Individual LLM tokens
        - on_chain_start/end: Chain execution events
        - on_tool_start/end: Tool execution events
        - on_custom_event: Developer-defined events

        This is useful for real-time UI with typing indicators and
        progress animations during LLM generation.

        Args:
            lead: Lead to process
            process_config: Optional processing configuration

        Yields:
            Granular events including tokens, tool calls, and custom events
        """
        from datetime import datetime, timezone

        # Build graph if needed
        if self._graph is None:
            self._graph = self._build_graph()

        # Compile the graph
        compiled = self._graph.compile()

        # Initial state
        initial_state: OrchestratorState = {
            "lead": lead,
            "process_config": process_config or {},
            "research_brief": None,
            "qualification_result": None,
            "enrichment_data": None,
            "synthesis": None,
            "gate_1_decision": None,
            "script_result": None,
            "email_result": None,
            "competitor_intel": None,
            "gate_2_decision": None,
            "hubspot_sync_result": None,
            "current_phase": "research",
            "phase_results": [],
            "total_duration_ms": 0.0,
            "errors": [],
            "tier": None,
            "has_phone": False,
            "is_atl": False,
        }

        # Use astream_events for token-level streaming
        async for event in compiled.astream_events(
            cast(Any, initial_state),
            version="v2",
        ):
            event_type = event.get("event", "")
            timestamp = datetime.now(timezone.utc).isoformat()

            if event_type == "on_chat_model_stream":
                # Token-level streaming from LLM
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content"):
                    yield {
                        "event_type": "token",
                        "content": chunk.content,
                        "run_id": event.get("run_id"),
                        "timestamp": timestamp,
                    }

            elif event_type == "on_chain_start":
                # Node/chain started
                yield {
                    "event_type": "chain_start",
                    "name": event.get("name"),
                    "run_id": event.get("run_id"),
                    "parent_ids": event.get("parent_ids", []),
                    "timestamp": timestamp,
                }

            elif event_type == "on_chain_end":
                # Node/chain completed
                yield {
                    "event_type": "chain_end",
                    "name": event.get("name"),
                    "run_id": event.get("run_id"),
                    "timestamp": timestamp,
                }

            elif event_type == "on_tool_start":
                # Tool execution started
                yield {
                    "event_type": "tool_start",
                    "name": event.get("name"),
                    "run_id": event.get("run_id"),
                    "input": event.get("data", {}).get("input"),
                    "timestamp": timestamp,
                }

            elif event_type == "on_tool_end":
                # Tool execution completed
                yield {
                    "event_type": "tool_end",
                    "name": event.get("name"),
                    "run_id": event.get("run_id"),
                    "output": event.get("data", {}).get("output"),
                    "timestamp": timestamp,
                }

            elif event_type == "on_custom_event":
                # Custom developer-defined events
                yield {
                    "event_type": "custom",
                    "name": event.get("name"),
                    "data": event.get("data"),
                    "run_id": event.get("run_id"),
                    "timestamp": timestamp,
                }


# Singleton instance
master_orchestrator_agent = MasterOrchestratorAgent()
