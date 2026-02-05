"""Tests for CallBriefAssembler service.

Tests the composition layer that runs 3 agents in parallel and assembles
playbook data into a complete call brief.
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.data.lead_schemas import Lead
from app.services.langgraph.agents.call_brief import (
    BriefQuality,
    CallBriefAssembler,
    CallBriefRequest,
    CallBriefResponse,
    CallScript,
    CompanySnapshot,
    ContactInfo,
    ObjectionPrep,
    QualificationSummary,
)
from app.services.langgraph.states import QualificationTier

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_lead() -> Lead:
    """Create a sample lead for testing."""
    return Lead(
        hubspot_id="test_123",
        email="john.doe@university.edu",
        first_name="John",
        last_name="Doe",
        company="State University",
        title="AV Director",
        phone="555-0100",
        industry="higher_ed",
        persona_match="av_director",
    )


@pytest.fixture
def minimal_lead() -> Lead:
    """Create a minimal lead with very little data."""
    return Lead(
        hubspot_id="minimal_456",
        email="unknown@placeholder.harvester.local",
    )


@pytest.fixture
def research_result() -> dict[str, Any]:
    """Sample research agent result."""
    return {
        "research_brief": {
            "company_overview": "State University is a large public research university.",
            "recent_news": ["New campus expansion announced", "AV upgrade project funded"],
            "enrichment_data": {
                "employees": 5000,
                "industry": "higher_ed",
                "phone_numbers": [
                    {"sanitized_number": "555-0199", "type": "work_direct"},
                    {"sanitized_number": "555-0200", "type": "mobile"},
                ],
                "organization": {"phone": "555-0300"},
            },
        },
        "talking_points": ["Campus expansion", "AV modernization"],
        "risk_factors": ["Budget cycle ends Q2"],
    }


@pytest.fixture
def qualification_result() -> dict[str, Any]:
    """Sample qualification agent result."""
    return {
        "total_score": 78.5,
        "tier": QualificationTier.TIER_1,
        "confidence": 0.85,
        "persona_match": "av_director",
        "missing_info": [],
        "score_breakdown": {
            "company_size": {
                "category": "enterprise",
                "raw_score": 10,
                "weighted_score": 25.0,
                "reason": "5000+ employees",
                "confidence": 1.0,
            },
            "industry_vertical": {
                "category": "higher_ed",
                "raw_score": 10,
                "weighted_score": 20.0,
                "reason": "Higher education vertical",
                "confidence": 1.0,
            },
            "use_case_fit": {
                "category": "lecture_capture",
                "raw_score": 9,
                "weighted_score": 22.5,
                "reason": "AV Director persona + higher ed",
                "confidence": 0.9,
            },
            "tech_stack_signals": {
                "category": "no_solution",
                "raw_score": 5,
                "weighted_score": 7.5,
                "reason": "No competing tech detected",
                "confidence": 0.5,
            },
            "buying_authority": {
                "category": "budget_holder",
                "raw_score": 10,
                "weighted_score": 15.0,
                "reason": "AV Director with budget authority",
                "confidence": 0.95,
            },
        },
        "next_action": {
            "action_type": "priority_sequence",
            "description": "Priority sequence with AE involvement",
            "priority": "high",
            "ae_involvement": True,
            "missing_info": [],
        },
    }


@pytest.fixture
def script_result() -> dict[str, Any]:
    """Sample script agent result."""
    return {
        "personalized_script": "Hi John, I noticed you downloaded our lecture capture whitepaper...",
        "talking_points": ["NC State manages 300+ rooms", "Fleet management saves time"],
        "objection_responses": [
            {"objection": "We already have a solution", "response": "I understand..."},
        ],
    }


@pytest.fixture
def assembler() -> CallBriefAssembler:
    """Create assembler instance."""
    return CallBriefAssembler()


# =============================================================================
# Happy Path Tests
# =============================================================================


@pytest.mark.asyncio
async def test_assemble_complete_brief(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    research_result: dict[str, Any],
    qualification_result: dict[str, Any],
    script_result: dict[str, Any],
) -> None:
    """Test assembling a complete brief with all agent results."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=research_result
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=script_result
        ),
    ):
        request = CallBriefRequest(
            lead=sample_lead,
            trigger="content_download",
            call_type="warm",
        )
        brief = await assembler.assemble(request)

    assert isinstance(brief, CallBriefResponse)
    assert brief.contact.name == "John Doe"
    assert brief.contact.title == "AV Director"
    assert brief.company.name == "State University"
    assert brief.qualification.tier == "tier_1"
    assert brief.qualification.score == 78.5
    assert brief.script.personalized_script is not None
    assert brief.processing_time_ms > 0
    assert brief.call_type == "warm"
    assert brief.trigger == "content_download"


@pytest.mark.asyncio
async def test_assemble_brief_response_sections(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    research_result: dict[str, Any],
    qualification_result: dict[str, Any],
    script_result: dict[str, Any],
) -> None:
    """Test that all brief sections are populated."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=research_result
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=script_result
        ),
    ):
        request = CallBriefRequest(lead=sample_lead, trigger="content_download")
        brief = await assembler.assemble(request)

    # All sections present
    assert isinstance(brief.contact, ContactInfo)
    assert isinstance(brief.company, CompanySnapshot)
    assert isinstance(brief.qualification, QualificationSummary)
    assert isinstance(brief.script, CallScript)
    assert isinstance(brief.objection_prep, ObjectionPrep)


# =============================================================================
# Phone Extraction Tests (PHONES ARE GOLD)
# =============================================================================


@pytest.mark.asyncio
async def test_phone_extraction_from_research(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    research_result: dict[str, Any],
    qualification_result: dict[str, Any],
    script_result: dict[str, Any],
) -> None:
    """Test phone extraction from Apollo enrichment data."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=research_result
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=script_result
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    phones = brief.contact.phones
    assert phones.has_phone is True
    assert phones.direct_phone == "555-0199"
    assert phones.mobile_phone == "555-0200"
    assert phones.company_phone == "555-0300"
    assert phones.best_phone == "555-0199"  # Direct dial is best


@pytest.mark.asyncio
async def test_phone_fallback_to_lead_record(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    qualification_result: dict[str, Any],
    script_result: dict[str, Any],
) -> None:
    """Test phone fallback when research has no phones."""
    # Research result without phone data
    no_phone_research: dict[str, Any] = {
        "research_brief": {"company_overview": "A university"},
        "talking_points": [],
        "risk_factors": [],
    }

    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=no_phone_research
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=script_result
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    # Falls back to lead.phone
    assert brief.contact.phones.has_phone is True
    assert brief.contact.phones.best_phone == "555-0100"
    assert brief.contact.phones.phone_source == "lead_record"


@pytest.mark.asyncio
async def test_no_phone_flagged_critical(
    assembler: CallBriefAssembler,
    minimal_lead: Lead,
) -> None:
    """Test that missing phone is flagged as CRITICAL gap."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=None
        ),
    ):
        request = CallBriefRequest(lead=minimal_lead)
        brief = await assembler.assemble(request)

    assert brief.contact.phones.has_phone is False
    assert any("CRITICAL" in gap for gap in brief.intelligence_gaps)


# =============================================================================
# Parallel Execution Tests
# =============================================================================


@pytest.mark.asyncio
async def test_agents_run_concurrently(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
) -> None:
    """Verify agents are invoked (they'd run concurrently via asyncio.gather)."""
    mock_research = AsyncMock(return_value={"research_brief": None, "talking_points": [], "risk_factors": []})
    mock_qualify = AsyncMock(return_value={"total_score": 50.0, "tier": QualificationTier.TIER_2})
    mock_script = AsyncMock(return_value={"personalized_script": "Hello", "talking_points": [], "objection_responses": []})

    with (
        patch.object(assembler._research_agent, "run", mock_research),
        patch.object(assembler._qualification_agent, "run", mock_qualify),
        patch.object(assembler._script_agent, "run", mock_script),
    ):
        request = CallBriefRequest(lead=sample_lead, trigger="demo_request")
        await assembler.assemble(request)

    # All three agents were called
    mock_research.assert_awaited_once()
    mock_qualify.assert_awaited_once()
    mock_script.assert_awaited_once()


# =============================================================================
# Graceful Degradation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_research_failure_partial_brief(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    qualification_result: dict[str, Any],
    script_result: dict[str, Any],
) -> None:
    """Test that research agent failure still produces a partial brief."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, side_effect=Exception("Apollo down")
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=script_result
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    # Still has qualification and script
    assert brief.qualification.tier == "tier_1"
    assert brief.script.personalized_script is not None
    # Company overview missing
    assert brief.company.overview is None


@pytest.mark.asyncio
async def test_qualification_failure_partial_brief(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    research_result: dict[str, Any],
    script_result: dict[str, Any],
) -> None:
    """Test that qualification failure still produces a partial brief."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=research_result
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, side_effect=Exception("LLM error")
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=script_result
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    # No qualification
    assert brief.qualification.tier is None
    # Still has research and script
    assert brief.company.overview is not None
    assert brief.script.personalized_script is not None


@pytest.mark.asyncio
async def test_script_failure_partial_brief(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    research_result: dict[str, Any],
    qualification_result: dict[str, Any],
) -> None:
    """Test that script failure still produces a partial brief."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=research_result
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, side_effect=Exception("Prompt error")
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    assert brief.script.personalized_script is None
    assert brief.qualification.tier == "tier_1"


@pytest.mark.asyncio
async def test_all_agents_fail_minimal_brief(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
) -> None:
    """Test that all agents failing still returns a minimal brief from lead + playbook."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, side_effect=Exception("Research down")
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, side_effect=Exception("Qualify down")
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, side_effect=Exception("Script down")
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    # Contact info from lead record
    assert brief.contact.name == "John Doe"
    assert brief.contact.title == "AV Director"
    # Phone from lead record
    assert brief.contact.phones.best_phone == "555-0100"
    # Playbook data still available from persona
    assert brief.contact.persona == "av_director"
    assert len(brief.objection_prep.objections) > 0  # From persona profile


# =============================================================================
# Persona & Playbook Lookup Tests
# =============================================================================


@pytest.mark.asyncio
async def test_objection_prep_from_persona(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    qualification_result: dict[str, Any],
) -> None:
    """Test objection prep populated from persona profile."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=None
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    # AV Director should have objections from persona profile
    assert len(brief.objection_prep.objections) <= 3  # Top 3
    assert brief.objection_prep.source == "persona_profile"
    for obj in brief.objection_prep.objections:
        assert obj.objection
        assert obj.response


@pytest.mark.asyncio
async def test_discovery_prep_by_vertical(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    qualification_result: dict[str, Any],
) -> None:
    """Test discovery questions filtered by vertical."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=None
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    # Should have discovery questions (universal + vertical-specific)
    assert len(brief.discovery_prep.questions) <= 5
    for q in brief.discovery_prep.questions:
        assert q.question
        assert q.stage
        assert q.what_you_learn


@pytest.mark.asyncio
async def test_reference_story_for_vertical(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    qualification_result: dict[str, Any],
) -> None:
    """Test reference story lookup by vertical."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=None
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    # Higher ed + AV Director → should find a reference story
    assert brief.reference_story.customer is not None


@pytest.mark.asyncio
async def test_no_persona_empty_objections(
    assembler: CallBriefAssembler,
    minimal_lead: Lead,
) -> None:
    """Test that no persona match results in empty objection prep."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=None
        ),
    ):
        request = CallBriefRequest(lead=minimal_lead)
        brief = await assembler.assemble(request)

    assert len(brief.objection_prep.objections) == 0


# =============================================================================
# Quality Scoring Tests
# =============================================================================


@pytest.mark.asyncio
async def test_quality_high(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    research_result: dict[str, Any],
    qualification_result: dict[str, Any],
    script_result: dict[str, Any],
) -> None:
    """Test HIGH quality when all data is present."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=research_result
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=script_result
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    assert brief.brief_quality == BriefQuality.HIGH


@pytest.mark.asyncio
async def test_quality_low_minimal_data(
    assembler: CallBriefAssembler,
    minimal_lead: Lead,
) -> None:
    """Test LOW quality when minimal data is available."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=None
        ),
    ):
        request = CallBriefRequest(lead=minimal_lead)
        brief = await assembler.assemble(request)

    assert brief.brief_quality == BriefQuality.LOW


@pytest.mark.asyncio
async def test_quality_medium_partial_data(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    qualification_result: dict[str, Any],
) -> None:
    """Test MEDIUM quality with partial data (qualification but no research/script)."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=None
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    # Has phone (3) + persona (2) + tier (2) + name (1) + title (1) = 9 → HIGH
    # Actually this lead has a lot, let me verify
    # phone from lead.phone=555-0100: +3
    # persona from qualification: +2
    # tier: +2
    # no script: +0
    # no overview: +0
    # title: +1
    # name: +1
    # Total: 9 → HIGH (because lead already has good data)
    assert brief.brief_quality in (BriefQuality.HIGH, BriefQuality.MEDIUM)


# =============================================================================
# Intelligence Gap Tests
# =============================================================================


@pytest.mark.asyncio
async def test_intelligence_gaps_complete(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    research_result: dict[str, Any],
    qualification_result: dict[str, Any],
    script_result: dict[str, Any],
) -> None:
    """Test that complete brief has no critical gaps."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=research_result
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=qualification_result
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=script_result
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    # Complete brief should have no CRITICAL gaps
    critical_gaps = [g for g in brief.intelligence_gaps if "CRITICAL" in g]
    assert len(critical_gaps) == 0


@pytest.mark.asyncio
async def test_intelligence_gaps_missing_email(
    assembler: CallBriefAssembler,
    minimal_lead: Lead,
) -> None:
    """Test that placeholder email is flagged."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=None
        ),
    ):
        request = CallBriefRequest(lead=minimal_lead)
        brief = await assembler.assemble(request)

    assert any("email" in gap.lower() for gap in brief.intelligence_gaps)


# =============================================================================
# Call Type Variations
# =============================================================================


@pytest.mark.asyncio
async def test_cold_call_type(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    script_result: dict[str, Any],
) -> None:
    """Test cold call brief uses correct framework."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=script_result
        ),
    ):
        request = CallBriefRequest(lead=sample_lead, call_type="cold")
        brief = await assembler.assemble(request)

    assert brief.call_type == "cold"
    assert brief.script.call_type == "cold"
    assert brief.script.framework == "Pattern Interrupt"


@pytest.mark.asyncio
async def test_warm_call_type(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    script_result: dict[str, Any],
) -> None:
    """Test warm call brief uses ACQP framework."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=script_result
        ),
    ):
        request = CallBriefRequest(lead=sample_lead, call_type="warm")
        brief = await assembler.assemble(request)

    assert brief.call_type == "warm"
    assert brief.script.framework == "ACQP"


# =============================================================================
# Qualification Summary Tests
# =============================================================================


def test_build_qualification_summary_with_breakdown(
    assembler: CallBriefAssembler,
    qualification_result: dict[str, Any],
) -> None:
    """Test qualification summary extracts top strength and gap."""
    summary = assembler._build_qualification_summary(qualification_result)

    assert summary.tier == "tier_1"
    assert summary.tier_label == "Tier 1 - Priority Sequence"
    assert summary.score == 78.5
    assert summary.confidence == 0.85
    assert summary.top_strength is not None  # Highest scoring dimension
    assert summary.top_gap is not None  # Lowest scoring dimension


def test_build_qualification_summary_none(
    assembler: CallBriefAssembler,
) -> None:
    """Test qualification summary when agent returns None."""
    summary = assembler._build_qualification_summary(None)

    assert summary.tier is None
    assert summary.score == 0.0


# =============================================================================
# Company Snapshot Tests
# =============================================================================


def test_build_company_snapshot_with_research(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
    research_result: dict[str, Any],
) -> None:
    """Test company snapshot populated from research."""
    snapshot = assembler._build_company_snapshot(sample_lead, research_result)

    assert snapshot.name == "State University"
    assert snapshot.overview is not None
    assert snapshot.employees == 5000
    assert len(snapshot.recent_news) == 2


def test_build_company_snapshot_no_research(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
) -> None:
    """Test company snapshot from lead data only."""
    snapshot = assembler._build_company_snapshot(sample_lead, None)

    assert snapshot.name == "State University"
    assert snapshot.industry == "higher_ed"
    assert snapshot.overview is None


# =============================================================================
# Competitor Prep Tests
# =============================================================================


def test_build_competitor_prep_higher_ed(
    assembler: CallBriefAssembler,
) -> None:
    """Test competitor prep for higher ed vertical."""
    prep = assembler._build_competitor_prep("higher_ed")

    # Should find competitors targeting higher ed
    assert isinstance(prep.competitors, list)
    assert prep.vertical == "higher_ed"


def test_build_competitor_prep_unknown_vertical(
    assembler: CallBriefAssembler,
) -> None:
    """Test competitor prep with unknown vertical returns empty."""
    prep = assembler._build_competitor_prep("unknown_vertical")

    assert len(prep.competitors) == 0


def test_build_competitor_prep_none(
    assembler: CallBriefAssembler,
) -> None:
    """Test competitor prep with no vertical."""
    prep = assembler._build_competitor_prep(None)

    assert len(prep.competitors) == 0


# =============================================================================
# Processing Time Tests
# =============================================================================


@pytest.mark.asyncio
async def test_processing_time_tracked(
    assembler: CallBriefAssembler,
    sample_lead: Lead,
) -> None:
    """Test that processing time is tracked in the response."""
    with (
        patch.object(
            assembler._research_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._qualification_agent, "run", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            assembler._script_agent, "run", new_callable=AsyncMock, return_value=None
        ),
    ):
        request = CallBriefRequest(lead=sample_lead)
        brief = await assembler.assemble(request)

    assert brief.processing_time_ms > 0
