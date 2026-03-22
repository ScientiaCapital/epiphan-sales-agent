"""Tests for autonomous pipeline runner."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.autonomous.runner import AutonomousBDRRunner
from app.services.autonomous.schemas import DraftEmail, LeadSource, RawLead, RunConfig, RunStatus


@pytest.fixture
def runner() -> AutonomousBDRRunner:
    return AutonomousBDRRunner()


def _make_raw_lead(email: str = "test@example.com") -> RawLead:
    return RawLead(
        email=email,
        first_name="Jane",
        last_name="Doe",
        title="Director of AV",
        company="State University",
        industry="higher education",
        source=LeadSource.APOLLO,
    )


class TestRun:
    @pytest.mark.asyncio
    async def test_full_run_with_mocked_components(self, runner: AutonomousBDRRunner) -> None:
        raw_leads = [_make_raw_lead("jane@uni.edu"), _make_raw_lead("john@corp.com")]
        mock_draft = DraftEmail(
            subject="Quick question",
            body="Hi, noticed your team records manually.",
            pain_point="manual_recording",
        )

        with (
            patch.object(runner, "_source_leads", new_callable=AsyncMock, return_value=raw_leads),
            patch.object(runner, "_create_run_record", new_callable=AsyncMock),
            patch.object(runner, "_update_run_record", new_callable=AsyncMock),
            patch.object(runner, "_insert_queue_item", new_callable=AsyncMock),
            patch.object(runner, "_safe_research", new_callable=AsyncMock, return_value=None),
            patch.object(runner, "_safe_qualify", new_callable=AsyncMock, return_value={
                "tier": MagicMock(value="tier_1"),
                "total_score": 85.0,
                "confidence": 0.9,
                "persona_match": "av_director",
            }),
            patch.object(runner, "_safe_draft", new_callable=AsyncMock, return_value=mock_draft),
            patch("app.services.autonomous.dedup.deduplicator") as mock_dedup,
        ):
            mock_dedup.deduplicate = AsyncMock(return_value=raw_leads)
            summary = await runner.run(RunConfig(prospect_limit=25))

        assert summary.status == RunStatus.COMPLETED
        assert summary.total_processed == 2

    @pytest.mark.asyncio
    async def test_handles_run_failure(self, runner: AutonomousBDRRunner) -> None:
        with (
            patch.object(runner, "_source_leads", new_callable=AsyncMock, side_effect=Exception("Source failed")),
            patch.object(runner, "_create_run_record", new_callable=AsyncMock),
            patch.object(runner, "_update_run_record", new_callable=AsyncMock),
        ):
            summary = await runner.run()

        assert summary.status == RunStatus.FAILED
        assert len(summary.errors) > 0


class TestProcessLead:
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, runner: AutonomousBDRRunner) -> None:
        """All agents fail, lead still gets queued with defaults."""
        import asyncio

        lead = _make_raw_lead()
        semaphore = asyncio.Semaphore(5)

        with (
            patch.object(runner, "_safe_research", new_callable=AsyncMock, return_value=None),
            patch.object(runner, "_safe_qualify", new_callable=AsyncMock, return_value=None),
            patch.object(runner, "_safe_draft", new_callable=AsyncMock, return_value=None),
            patch.object(runner, "_insert_queue_item", new_callable=AsyncMock) as mock_insert,
        ):
            result = await runner._process_lead(lead, "run-123", semaphore)

        assert result["tier"] == "not_icp"
        mock_insert.assert_called_once()


class TestSafeWrappers:
    @pytest.mark.asyncio
    async def test_safe_research_returns_none_on_failure(self, runner: AutonomousBDRRunner) -> None:
        from app.data.lead_schemas import Lead

        lead = Lead(hubspot_id="123", email="test@example.com")

        # Patch at the source module (lazy import inside _safe_research)
        with patch("app.services.langgraph.agents.lead_research.LeadResearchAgent") as mock_cls:
            mock_cls.return_value.run = AsyncMock(side_effect=Exception("fail"))
            result = await runner._safe_research(lead)

        assert result is None

    @pytest.mark.asyncio
    async def test_safe_qualify_returns_none_on_failure(self, runner: AutonomousBDRRunner) -> None:
        from app.data.lead_schemas import Lead

        lead = Lead(hubspot_id="123", email="test@example.com")

        with patch("app.services.langgraph.agents.qualification.QualificationAgent") as mock_cls:
            mock_cls.return_value.run = AsyncMock(side_effect=Exception("fail"))
            result = await runner._safe_qualify(lead)

        assert result is None

    @pytest.mark.asyncio
    async def test_safe_draft_returns_none_on_failure(self, runner: AutonomousBDRRunner) -> None:
        with patch("app.services.autonomous.drafter.outreach_drafter") as mock_drafter:
            mock_drafter.draft_email = AsyncMock(side_effect=Exception("fail"))
            result = await runner._safe_draft("Jane", "Dir", "Acme", "tech", None, None)

        assert result is None
