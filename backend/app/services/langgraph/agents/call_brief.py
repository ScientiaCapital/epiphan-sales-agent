"""Call Brief Assembler for one-page call preparation.

Composes existing agents (research, qualify, script) in parallel
and enriches with playbook data to produce a complete call brief.

NOT a LangGraph agent — a lightweight composition layer using asyncio.gather
for speed. No review gates, no HubSpot sync, no checkpointing overhead.

Eliminates Tim's manual 5-10 min/lead prep by combining 3 API calls + playbook
lookups into a single response.
"""

import asyncio
import contextlib
import logging
import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.data.competitors import get_competitors_by_vertical
from app.data.discovery import get_questions_by_vertical
from app.data.lead_schemas import Lead
from app.data.personas import get_persona_by_id
from app.data.schemas import (
    Vertical,
)
from app.data.stories import get_best_reference_for_context
from app.services.langgraph.agents.lead_research import LeadResearchAgent
from app.services.langgraph.agents.qualification import QualificationAgent
from app.services.langgraph.agents.script_selection import ScriptSelectionAgent
from app.services.langgraph.states import QualificationTier
from app.services.langgraph.tools.harvester_mapper import enrich_phone_numbers

logger = logging.getLogger(__name__)


# =============================================================================
# Response Models
# =============================================================================


class PhoneInfo(BaseModel):
    """All available phone numbers with priority ranking.

    PHONES ARE GOLD - this surfaces every number we have for the lead.
    """

    direct_phone: str | None = None
    mobile_phone: str | None = None
    work_phone: str | None = None
    company_phone: str | None = None
    best_phone: str | None = Field(default=None, description="Highest priority phone for dialing")
    phone_source: str | None = Field(default=None, description="Where the phone came from")
    has_phone: bool = Field(default=False, description="Whether any phone is available")


class CompanySnapshot(BaseModel):
    """Company intelligence summary."""

    name: str | None = None
    industry: str | None = None
    employees: int | None = None
    overview: str | None = None
    recent_news: list[str] = Field(default_factory=list)


class ContactInfo(BaseModel):
    """Contact details for the lead."""

    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    title: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    persona: str | None = Field(default=None, description="Matched persona ID")
    persona_title: str | None = Field(default=None, description="Persona display name")
    is_atl: bool = Field(default=False, description="Above-the-line decision maker")
    phones: PhoneInfo = Field(default_factory=PhoneInfo)


class QualificationSummary(BaseModel):
    """Qualification result summary for the brief."""

    tier: str | None = None
    tier_label: str | None = None
    score: float = 0.0
    confidence: float = 0.0
    top_strength: str | None = None
    top_gap: str | None = None
    missing_info: list[str] = Field(default_factory=list)


class CallScript(BaseModel):
    """Personalized call script in ACQP framework."""

    personalized_script: str | None = None
    talking_points: list[str] = Field(default_factory=list)
    objection_responses: list[dict[str, str]] = Field(default_factory=list)
    call_type: str = "warm"
    framework: str = "ACQP"


class ObjectionPrepItem(BaseModel):
    """Single objection with response."""

    objection: str
    response: str
    persona_context: str | None = None


class ObjectionPrep(BaseModel):
    """Top objections for this persona with prepared responses."""

    objections: list[ObjectionPrepItem] = Field(default_factory=list)
    source: str | None = Field(default=None, description="persona_profile or warm_script")


class DiscoveryPrepItem(BaseModel):
    """Single SPIN discovery question."""

    question: str
    stage: str
    what_you_learn: str


class DiscoveryPrep(BaseModel):
    """SPIN discovery questions filtered by vertical."""

    questions: list[DiscoveryPrepItem] = Field(default_factory=list)
    vertical: str | None = None


class CompetitorPrepItem(BaseModel):
    """Single competitor summary for call prep."""

    name: str
    company: str
    positioning: str
    key_differentiator: str | None = None
    talk_track_opening: str | None = None


class CompetitorPrep(BaseModel):
    """Likely competitors and differentiators for this context."""

    competitors: list[CompetitorPrepItem] = Field(default_factory=list)
    vertical: str | None = None


class ReferenceStoryBrief(BaseModel):
    """Best matching customer story for this call."""

    customer: str | None = None
    stats: str | None = None
    quote: str | None = None
    quote_person: str | None = None
    challenge: str | None = None
    results: list[str] = Field(default_factory=list)
    vertical: str | None = None


class BriefQuality(str, Enum):
    """Quality assessment of the call brief."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CallBriefRequest(BaseModel):
    """Request for a complete call prep brief."""

    lead: Lead
    trigger: str | None = Field(
        default=None,
        description="Trigger type: content_download, demo_request, pricing_page, etc.",
    )
    call_type: str = Field(default="warm", description="'warm' or 'cold'")
    research_depth: str = Field(
        default="quick",
        description="'quick' (API only, ~2s) or 'deep' (API + web, ~5s)",
    )


class CallBriefResponse(BaseModel):
    """Complete one-page call prep brief.

    Everything Tim needs before dialing — contact, company, qualification,
    script, objections, discovery questions, competitors, and reference story.
    """

    # Persistence
    brief_id: str | None = Field(default=None, description="UUID from call_briefs table")

    # Core sections
    contact: ContactInfo
    company: CompanySnapshot
    qualification: QualificationSummary
    script: CallScript
    objection_prep: ObjectionPrep
    discovery_prep: DiscoveryPrep
    competitor_prep: CompetitorPrep
    reference_story: ReferenceStoryBrief

    # Meta
    brief_quality: BriefQuality = BriefQuality.MEDIUM
    intelligence_gaps: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    call_type: str = "warm"
    trigger: str | None = None


# =============================================================================
# Assembler Service
# =============================================================================


class CallBriefAssembler:
    """Assembles complete call briefs by composing existing agents + playbook data.

    Runs research, qualification, and script agents in parallel via asyncio.gather,
    then enriches with static playbook lookups (persona, discovery, competitors, stories).
    """

    def __init__(self) -> None:
        """Initialize with agent instances."""
        self._research_agent = LeadResearchAgent()
        self._qualification_agent = QualificationAgent()
        self._script_agent = ScriptSelectionAgent()

    async def assemble(self, request: CallBriefRequest) -> CallBriefResponse:
        """Assemble a complete call brief for the given lead.

        Runs 3 agents in parallel, then enriches with playbook data.
        Total time: ~3-5 seconds (parallel agent execution dominates).
        """
        start_time = time.monotonic()
        lead = request.lead

        # Run all agents in parallel (research, qualify, script, user context)
        research_result, qualification_result, script_result, user_context = await self._run_agents(
            lead=lead,
            trigger=request.trigger,
            call_type=request.call_type,
            research_depth=request.research_depth,
        )

        # Extract persona from qualification result
        persona_id = self._get_persona_id(qualification_result, lead)
        vertical = self._get_vertical(qualification_result, lead)

        # Build all brief sections (synchronous lookups, very fast)
        contact = self._build_contact_info(lead, research_result, persona_id)
        company = self._build_company_snapshot(lead, research_result)
        qualification = self._build_qualification_summary(qualification_result)
        script = self._build_call_script(script_result, request.call_type)
        objection_prep = self._build_objection_prep(persona_id)
        discovery_prep = self._build_discovery_prep(vertical)
        competitor_prep = self._build_competitor_prep(vertical)
        reference_story = self._build_reference_story(vertical, persona_id)

        # Assess quality and identify gaps
        brief_quality = self._assess_quality(
            contact, company, qualification, script
        )
        intelligence_gaps = self._identify_intelligence_gaps(
            contact, company, qualification, script
        )

        # Enrich with user memory context if available
        if user_context:
            intelligence_gaps.append(
                f"Prior calls: {user_context['interaction_count']} previous interactions"
            )
            # Add prior objections to objection prep context
            prior_objections = user_context.get("objections_seen", [])
            if prior_objections:
                for obj_text in prior_objections:
                    if obj_text and not any(
                        o.objection == obj_text for o in objection_prep.objections
                    ):
                        objection_prep.objections.append(
                            ObjectionPrepItem(
                                objection=obj_text,
                                response="Previously raised — review prior approach",
                                persona_context="from_user_memory",
                            )
                        )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        return CallBriefResponse(
            contact=contact,
            company=company,
            qualification=qualification,
            script=script,
            objection_prep=objection_prep,
            discovery_prep=discovery_prep,
            competitor_prep=competitor_prep,
            reference_story=reference_story,
            brief_quality=brief_quality,
            intelligence_gaps=intelligence_gaps,
            processing_time_ms=round(elapsed_ms, 1),
            call_type=request.call_type,
            trigger=request.trigger,
        )

    async def _run_agents(
        self,
        lead: Lead,
        trigger: str | None,
        call_type: str,
        research_depth: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        """Run research, qualification, script agents, and user context in parallel.

        Each agent failure is isolated — returns None for that result,
        allowing the brief to degrade gracefully.
        """

        async def _safe_research() -> dict[str, Any] | None:
            try:
                return await self._research_agent.run(
                    lead=lead,
                    research_depth=research_depth,
                )
            except Exception:
                logger.exception("Research agent failed for %s", lead.email)
                return None

        async def _safe_qualify() -> dict[str, Any] | None:
            try:
                return await self._qualification_agent.run(
                    lead=lead,
                    skip_enrichment=False,
                )
            except Exception:
                logger.exception("Qualification agent failed for %s", lead.email)
                return None

        async def _safe_script() -> dict[str, Any] | None:
            try:
                # Need persona for script — extract from lead if available
                persona_match = lead.persona_match
                return await self._script_agent.run(
                    lead=lead,
                    persona_match=persona_match,
                    trigger=trigger,
                    call_type=call_type,
                )
            except Exception:
                logger.exception("Script agent failed for %s", lead.email)
                return None

        async def _safe_user_context() -> dict[str, Any] | None:
            try:
                from app.services.langgraph.memory.user_store import user_memory

                ctx = await user_memory.get_user_context(lead.hubspot_id or lead.email)
                if ctx and ctx.interaction_count > 0:
                    return {
                        "interaction_count": ctx.interaction_count,
                        "last_interaction": ctx.last_interaction.isoformat() if ctx.last_interaction else None,
                        "objections_seen": ctx.objections_seen,
                        "account_notes": ctx.account_notes,
                    }
                return None
            except Exception:
                logger.exception("User memory failed for %s", lead.email)
                return None

        results: tuple[dict[str, Any] | None, ...] = await asyncio.gather(
            _safe_research(),
            _safe_qualify(),
            _safe_script(),
            _safe_user_context(),
        )
        return results[0], results[1], results[2], results[3]

    def _get_persona_id(
        self,
        qualification_result: dict[str, Any] | None,
        lead: Lead,
    ) -> str | None:
        """Extract persona ID from qualification result or lead."""
        if qualification_result and qualification_result.get("persona_match"):
            return str(qualification_result["persona_match"])
        return lead.persona_match

    def _get_vertical(
        self,
        qualification_result: dict[str, Any] | None,
        lead: Lead,
    ) -> str | None:
        """Extract vertical from qualification or lead data."""
        if qualification_result:
            breakdown = qualification_result.get("score_breakdown")
            if breakdown and isinstance(breakdown, dict):
                industry = breakdown.get("industry_vertical", {})
                if isinstance(industry, dict):
                    category = industry.get("category")
                    if category and category != "unknown":
                        return str(category)
        return lead.vertical or lead.industry

    def _build_contact_info(
        self,
        lead: Lead,
        research_result: dict[str, Any] | None,
        persona_id: str | None,
    ) -> ContactInfo:
        """Build contact info with phone extraction from all sources."""
        # Extract phones from research data (Apollo enrichment) + lead record
        apollo_data: dict[str, Any] | None = None
        if research_result:
            brief = research_result.get("research_brief")
            if isinstance(brief, dict):
                apollo_data = brief.get("enrichment_data")

        phone_data = enrich_phone_numbers(
            apollo_data=apollo_data,
            harvester_direct=None,
            harvester_mobile=None,
            harvester_work=None,
            harvester_company=None,
        )

        # If no phones from research, fall back to lead.phone
        best_phone = phone_data.get("best_phone")
        if not best_phone and lead.phone:
            best_phone = lead.phone
            phone_data["best_phone"] = lead.phone
            phone_data["phone_source"] = "lead_record"

        phones = PhoneInfo(
            direct_phone=phone_data.get("direct_phone"),
            mobile_phone=phone_data.get("mobile_phone"),
            work_phone=phone_data.get("work_phone"),
            company_phone=phone_data.get("company_phone"),
            best_phone=best_phone,
            phone_source=phone_data.get("phone_source"),
            has_phone=best_phone is not None,
        )

        # Look up persona display name
        persona_title: str | None = None
        if persona_id:
            profile = get_persona_by_id(persona_id)
            if profile:
                persona_title = profile.title

        # Build name
        name_parts = []
        if lead.first_name:
            name_parts.append(lead.first_name)
        if lead.last_name:
            name_parts.append(lead.last_name)
        full_name = " ".join(name_parts) if name_parts else None

        return ContactInfo(
            name=full_name,
            first_name=lead.first_name,
            last_name=lead.last_name,
            title=lead.title,
            email=lead.email if "@placeholder" not in lead.email else None,
            linkedin_url=lead.linkedin_url,
            persona=persona_id,
            persona_title=persona_title,
            is_atl=persona_id is not None,
            phones=phones,
        )

    def _build_company_snapshot(
        self,
        lead: Lead,
        research_result: dict[str, Any] | None,
    ) -> CompanySnapshot:
        """Build company snapshot from research + lead data."""
        overview: str | None = None
        recent_news: list[str] = []
        employees: int | None = None
        industry: str | None = lead.industry

        if research_result:
            brief = research_result.get("research_brief")
            if isinstance(brief, dict):
                overview = brief.get("company_overview") or brief.get("summary")
                news = brief.get("recent_news", [])
                if isinstance(news, list):
                    recent_news = [str(n) for n in news[:5]]

                enrichment = brief.get("enrichment_data")
                if isinstance(enrichment, dict):
                    employees = enrichment.get("employees")
                    if not industry:
                        industry = enrichment.get("industry")

        return CompanySnapshot(
            name=lead.company,
            industry=industry,
            employees=employees,
            overview=overview,
            recent_news=recent_news,
        )

    def _build_qualification_summary(
        self,
        qualification_result: dict[str, Any] | None,
    ) -> QualificationSummary:
        """Build qualification summary from agent result."""
        if not qualification_result:
            return QualificationSummary()

        tier = qualification_result.get("tier")
        tier_str: str | None = None
        tier_label: str | None = None

        if tier:
            tier_str = tier.value if isinstance(tier, QualificationTier) else str(tier)

            tier_labels = {
                "tier_1": "Tier 1 - Priority Sequence",
                "tier_2": "Tier 2 - Standard Sequence",
                "tier_3": "Tier 3 - Marketing Nurture",
                "not_icp": "Not ICP - Disqualify",
            }
            tier_label = tier_labels.get(tier_str, tier_str)

        # Extract top strength and gap from score breakdown
        top_strength: str | None = None
        top_gap: str | None = None
        breakdown = qualification_result.get("score_breakdown")
        if isinstance(breakdown, dict):
            best_score = -1.0
            worst_score = 11.0
            for dim_name, dim_data in breakdown.items():
                if isinstance(dim_data, dict):
                    raw = dim_data.get("raw_score", 5)
                    reason = dim_data.get("reason", dim_name)
                    if raw > best_score:
                        best_score = raw
                        top_strength = f"{dim_name}: {reason}"
                    if raw < worst_score:
                        worst_score = raw
                        top_gap = f"{dim_name}: {reason}"

        return QualificationSummary(
            tier=tier_str,
            tier_label=tier_label,
            score=float(qualification_result.get("total_score", 0.0)),
            confidence=float(qualification_result.get("confidence", 0.0)),
            top_strength=top_strength,
            top_gap=top_gap,
            missing_info=qualification_result.get("missing_info", []),
        )

    def _build_call_script(
        self,
        script_result: dict[str, Any] | None,
        call_type: str,
    ) -> CallScript:
        """Build call script from agent result."""
        if not script_result:
            return CallScript(call_type=call_type)

        return CallScript(
            personalized_script=script_result.get("personalized_script"),
            talking_points=script_result.get("talking_points", []),
            objection_responses=script_result.get("objection_responses", []),
            call_type=call_type,
            framework="ACQP" if call_type == "warm" else "Pattern Interrupt",
        )

    def _build_objection_prep(self, persona_id: str | None) -> ObjectionPrep:
        """Build objection prep from persona profile."""
        if not persona_id:
            return ObjectionPrep()

        profile = get_persona_by_id(persona_id)
        if not profile:
            return ObjectionPrep()

        items: list[ObjectionPrepItem] = []
        for obj in profile.objections[:3]:
            items.append(
                ObjectionPrepItem(
                    objection=obj.objection,
                    response=obj.response,
                )
            )

        return ObjectionPrep(
            objections=items,
            source="persona_profile",
        )

    def _build_discovery_prep(self, vertical: str | None) -> DiscoveryPrep:
        """Build discovery prep with SPIN questions filtered by vertical."""
        lookup_vertical = vertical or "universal"

        # Map common industry names to Vertical enum values
        vertical_map: dict[str, str] = {
            "higher_ed": "higher_ed",
            "higher education": "higher_ed",
            "education": "higher_ed",
            "corporate": "corporate",
            "enterprise": "corporate",
            "healthcare": "healthcare",
            "hospital": "healthcare",
            "government": "government",
            "legal": "legal",
            "live_events": "live_events",
        }
        mapped_vertical = vertical_map.get(lookup_vertical.lower(), lookup_vertical)

        questions = get_questions_by_vertical(mapped_vertical)

        items: list[DiscoveryPrepItem] = []
        for q in questions[:5]:
            stage_value = q.stage if isinstance(q.stage, str) else q.stage.value
            items.append(
                DiscoveryPrepItem(
                    question=q.question,
                    stage=stage_value,
                    what_you_learn=q.what_you_learn,
                )
            )

        return DiscoveryPrep(
            questions=items,
            vertical=mapped_vertical,
        )

    def _build_competitor_prep(self, vertical: str | None) -> CompetitorPrep:
        """Build competitor prep from vertical lookup."""
        if not vertical:
            return CompetitorPrep()

        # Try to map to Vertical enum
        try:
            vertical_enum = Vertical(vertical)
        except ValueError:
            return CompetitorPrep(vertical=vertical)

        competitors = get_competitors_by_vertical(vertical_enum)

        items: list[CompetitorPrepItem] = []
        for comp in competitors[:3]:
            # Get first key differentiator
            key_diff: str | None = None
            if comp.key_differentiators:
                diff = comp.key_differentiators[0]
                key_diff = f"{diff.feature}: {diff.pearl_capability}"

            items.append(
                CompetitorPrepItem(
                    name=comp.name,
                    company=comp.company,
                    positioning=comp.positioning,
                    key_differentiator=key_diff,
                    talk_track_opening=comp.talk_track.opening if comp.talk_track else None,
                )
            )

        return CompetitorPrep(
            competitors=items,
            vertical=vertical,
        )

    def _build_reference_story(
        self,
        vertical: str | None,
        persona_id: str | None,
    ) -> ReferenceStoryBrief:
        """Build reference story by matching vertical and persona context."""
        vertical_enum: Vertical | None = None
        if vertical:
            with contextlib.suppress(ValueError):
                vertical_enum = Vertical(vertical)

        # Determine use case from persona
        use_case: str | None = None
        persona_use_cases: dict[str, str] = {
            "av_director": "fleet_management",
            "ld_director": "lecture_capture",
            "technical_director": "live_events",
            "simulation_director": "simulation",
            "corp_comms_director": "executive_comms",
        }
        if persona_id:
            use_case = persona_use_cases.get(persona_id)

        story = get_best_reference_for_context(
            vertical=vertical_enum,
            use_case=use_case,
        )

        if not story:
            return ReferenceStoryBrief()

        vertical_value = story.vertical if isinstance(story.vertical, str) else story.vertical.value

        return ReferenceStoryBrief(
            customer=story.customer,
            stats=story.stats,
            quote=story.quote,
            quote_person=story.quote_person,
            challenge=story.challenge,
            results=story.results[:3],
            vertical=vertical_value,
        )

    def _assess_quality(
        self,
        contact: ContactInfo,
        company: CompanySnapshot,
        qualification: QualificationSummary,
        script: CallScript,
    ) -> BriefQuality:
        """Assess brief quality based on data completeness.

        Scoring:
        - Phone available: +3 (PHONES ARE GOLD)
        - Has persona match: +2
        - Has qualification tier: +2
        - Has personalized script: +2
        - Has company overview: +1
        - Has title: +1
        - Has name: +1

        Thresholds: 8+ = HIGH, 4-7 = MEDIUM, <4 = LOW
        """
        score = 0

        if contact.phones.has_phone:
            score += 3
        if contact.persona:
            score += 2
        if qualification.tier:
            score += 2
        if script.personalized_script:
            score += 2
        if company.overview:
            score += 1
        if contact.title:
            score += 1
        if contact.name:
            score += 1

        if score >= 8:
            return BriefQuality.HIGH
        elif score >= 4:
            return BriefQuality.MEDIUM
        else:
            return BriefQuality.LOW

    def _identify_intelligence_gaps(
        self,
        contact: ContactInfo,
        company: CompanySnapshot,
        qualification: QualificationSummary,
        script: CallScript,
    ) -> list[str]:
        """Identify missing intelligence in the brief.

        Missing phone is flagged as CRITICAL — phones are GOLD.
        """
        gaps: list[str] = []

        # CRITICAL gap — no phone
        if not contact.phones.has_phone:
            gaps.append("CRITICAL: No phone number available - manual research needed")

        if not contact.title:
            gaps.append("Missing job title - cannot assess buying authority")
        if not contact.persona:
            gaps.append("No persona match - using generic messaging")
        if not qualification.tier:
            gaps.append("Qualification failed - no tier assignment")
        if not script.personalized_script:
            gaps.append("Script personalization failed - using generic script")
        if not company.overview:
            gaps.append("No company overview - research enrichment may have failed")
        if not contact.email or "@placeholder" in (contact.email or ""):
            gaps.append("No valid email address")

        # Add qualification agent's missing info
        for info in qualification.missing_info:
            gap = f"Missing data: {info}"
            if gap not in gaps:
                gaps.append(gap)

        return gaps


# Singleton instance
call_brief_assembler = CallBriefAssembler()
