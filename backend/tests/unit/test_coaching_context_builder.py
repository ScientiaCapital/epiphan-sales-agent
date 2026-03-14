"""Tests for coaching context builder — prompt assembly."""

from app.data.coaching_schemas import (
    AccumulatedState,
    AudienceType,
    BuyerDisc,
    CallStage,
    CrossCallContext,
    DiscConfidence,
    DiscType,
    MeddicTracker,
    PartnerFamiliarity,
    PartnerProgress,
)
from app.services.coaching.context_builder import (
    build_coach_system_prompt,
    format_cross_call_section,
    format_disc_section,
    format_meddic_section,
    format_partner_progress_section,
    format_session_context,
)


class TestBuildCoachSystemPrompt:
    def test_direct_sale_includes_meddic(self) -> None:
        prompt = build_coach_system_prompt(
            stage=CallStage.DISCOVERY,
            audience=AudienceType.DIRECT_SALE,
            acc=AccumulatedState(),
            topics=[],
            objections=[],
        )
        assert "MEDDIC STATUS" in prompt
        assert "PARTNER PROGRESS" not in prompt

    def test_channel_includes_partner_progress(self) -> None:
        prompt = build_coach_system_prompt(
            stage=CallStage.DISCOVERY,
            audience=AudienceType.CHANNEL_PARTNER,
            acc=AccumulatedState(
                partner=PartnerProgress(
                    product_familiarity=PartnerFamiliarity.AWARE,
                    active_projects=2,
                    margin_discussed=True,
                ),
            ),
            topics=[],
            objections=[],
        )
        assert "PARTNER PROGRESS" in prompt
        assert "MEDDIC STATUS" not in prompt
        assert "Active projects mentioned: 2" in prompt

    def test_includes_stage_tactics(self) -> None:
        prompt = build_coach_system_prompt(
            stage=CallStage.DISCOVERY,
            audience=AudienceType.DIRECT_SALE,
            acc=AccumulatedState(),
            topics=[],
            objections=[],
        )
        assert "SPIN Selling" in prompt

    def test_disc_only_when_above_low(self) -> None:
        # Low confidence — no DISC section
        prompt_low = build_coach_system_prompt(
            stage=CallStage.DISCOVERY,
            audience=AudienceType.DIRECT_SALE,
            acc=AccumulatedState(
                disc=BuyerDisc(disc_type=DiscType.DOMINANT, confidence=DiscConfidence.LOW),
            ),
            topics=[],
            objections=[],
        )
        assert "BUYER PROFILE" not in prompt_low

        # Medium confidence — includes DISC section
        prompt_med = build_coach_system_prompt(
            stage=CallStage.DISCOVERY,
            audience=AudienceType.DIRECT_SALE,
            acc=AccumulatedState(
                disc=BuyerDisc(disc_type=DiscType.DOMINANT, confidence=DiscConfidence.MEDIUM),
            ),
            topics=[],
            objections=[],
        )
        assert "BUYER PROFILE" in prompt_med

    def test_cross_call_included_when_provided(self) -> None:
        ctx = CrossCallContext(
            confirmed_pains=["Unreliable capture"],
            total_previous_calls=3,
            last_stage_reached="demo",
        )
        prompt = build_coach_system_prompt(
            stage=CallStage.DISCOVERY,
            audience=AudienceType.DIRECT_SALE,
            acc=AccumulatedState(),
            topics=[],
            objections=[],
            cross_call=ctx,
        )
        assert "CROSS-CALL CONTEXT" in prompt
        assert "Unreliable capture" in prompt

    def test_session_context_included(self) -> None:
        prompt = build_coach_system_prompt(
            stage=CallStage.DISCOVERY,
            audience=AudienceType.DIRECT_SALE,
            acc=AccumulatedState(),
            topics=["budget", "timeline"],
            objections=["price"],
        )
        assert "SESSION STATE" in prompt
        assert "budget" in prompt
        assert "price" in prompt


class TestFormatMeddicSection:
    def test_empty_tracker(self) -> None:
        section = format_meddic_section(MeddicTracker())
        assert "MEDDIC STATUS (0/6)" in section
        assert "\u2717" in section  # cross marks

    def test_partial_tracker(self) -> None:
        t = MeddicTracker()
        t.metrics.confirm("$500k budget")
        t.identify_pain.confirm("Unreliable capture")
        section = format_meddic_section(t)
        assert "MEDDIC STATUS (2/6)" in section
        assert "\u2713 Metrics — $500k budget" in section
        assert "\u2713 Pain — Unreliable capture" in section
        assert "Priority:" in section


class TestFormatPartnerProgressSection:
    def test_empty_progress(self) -> None:
        section = format_partner_progress_section(PartnerProgress())
        assert "PARTNER PROGRESS (0/6)" in section

    def test_with_displacement(self) -> None:
        p = PartnerProgress(
            displacement_opportunities=["Extron → Pearl"],
            active_projects=3,
        )
        section = format_partner_progress_section(p)
        assert "Extron → Pearl" in section
        assert "Active projects mentioned: 3" in section


class TestFormatDiscSection:
    def test_dominant(self) -> None:
        disc = BuyerDisc(disc_type=DiscType.DOMINANT, confidence=DiscConfidence.HIGH)
        section = format_disc_section(disc)
        assert "Dominant" in section
        assert "high confidence" in section
        assert "ROI" in section


class TestFormatSessionContext:
    def test_with_topics_and_objections(self) -> None:
        section = format_session_context(["budget", "timeline"], ["price"])
        assert "Topics discussed: budget, timeline" in section
        assert "Objections raised: price" in section


class TestFormatCrossCallSection:
    def test_with_data(self) -> None:
        ctx = CrossCallContext(
            confirmed_pains=["Unreliable capture"],
            open_commitments=["Send specs"],
            recurring_topics=["budget"],
            last_stage_reached="demo",
            total_previous_calls=3,
        )
        section = format_cross_call_section(ctx)
        assert "Previous calls: 3 calls" in section
        assert "Last stage reached: demo" in section
        assert "Unreliable capture" in section
        assert "Send specs" in section
        assert "budget" in section
