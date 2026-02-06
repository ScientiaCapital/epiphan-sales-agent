"""Tests for Clay integration in the enrichment pipeline.

Verifies Clay is triggered as a fallback when Apollo finds no phone,
and that Clay failures never block the pipeline.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.enrichment.pipeline import _process_harvester_batch


def _make_lead(
    external_id: str = "ext_001",
    email: str = "john@acme.com",
    title: str = "AV Director",
    **kwargs: object,
) -> dict:
    """Build a minimal lead dict for pipeline testing."""
    return {
        "external_id": external_id,
        "contact_email": email,
        "contact_title": title,
        "contact_name": kwargs.get("contact_name", "John Doe"),
        "company_name": kwargs.get("company_name", "Acme Corp"),
    }


@pytest.fixture()
def _mock_monitoring() -> None:
    """Silence the monitoring module during tests."""


class TestClayPipelineFallback:
    """Tests for Clay fallback trigger in the enrichment pipeline."""

    @pytest.mark.asyncio()
    @patch("app.services.enrichment.pipeline.complete_batch")
    @patch("app.services.enrichment.pipeline.get_batch", return_value=MagicMock())
    @patch("app.services.enrichment.pipeline.get_rate_limit_tracker")
    @patch("app.services.enrichment.pipeline.apollo_client")
    async def test_clay_triggered_when_no_phone(
        self,
        mock_apollo: MagicMock,
        mock_rate_tracker: MagicMock,
        _mock_get_batch: MagicMock,
        _mock_complete: MagicMock,
    ) -> None:
        """Clay push is called when Apollo returns no phone."""
        mock_rate_tracker.return_value = MagicMock()

        # Apollo returns data but no phones
        mock_tiered = MagicMock()
        mock_tiered.data = {"phone_numbers": []}
        mock_tiered.credits_used = 1
        mock_tiered.is_atl = True
        mock_tiered.persona_match = "av_director"
        mock_tiered.phone_revealed = False
        mock_tiered.atl_match = MagicMock(confidence=0.9, reason="Title match")
        mock_apollo.tiered_enrich = AsyncMock(return_value=mock_tiered)

        mock_clay = AsyncMock()
        mock_clay.is_enabled.return_value = True
        mock_clay.push_lead_to_clay = AsyncMock(return_value={"status": "queued"})

        with patch("app.services.enrichment.clay.clay_client", mock_clay):
            await _process_harvester_batch(
                batch_id="test_001",
                leads=[_make_lead()],
                concurrency=1,
                tiered_enrichment=True,
            )

        mock_clay.push_lead_to_clay.assert_called_once()
        call_data = mock_clay.push_lead_to_clay.call_args.args[0]
        assert call_data["email"] == "john@acme.com"
        assert call_data["lead_id"] == "ext_001"

    @pytest.mark.asyncio()
    @patch("app.services.enrichment.pipeline.complete_batch")
    @patch("app.services.enrichment.pipeline.get_batch", return_value=MagicMock())
    @patch("app.services.enrichment.pipeline.get_rate_limit_tracker")
    @patch("app.services.enrichment.pipeline.apollo_client")
    async def test_clay_not_triggered_when_phone_exists(
        self,
        mock_apollo: MagicMock,
        mock_rate_tracker: MagicMock,
        _mock_get_batch: MagicMock,
        _mock_complete: MagicMock,
    ) -> None:
        """Clay is NOT called when Apollo already found a phone."""
        mock_rate_tracker.return_value = MagicMock()

        # Apollo returns a phone
        mock_tiered = MagicMock()
        mock_tiered.data = {
            "phone_numbers": [{"number": "+14155551234", "type": "mobile"}],
        }
        mock_tiered.credits_used = 9
        mock_tiered.is_atl = True
        mock_tiered.persona_match = "av_director"
        mock_tiered.phone_revealed = True
        mock_tiered.atl_match = MagicMock(confidence=0.9, reason="Title match")
        mock_apollo.tiered_enrich = AsyncMock(return_value=mock_tiered)

        mock_clay = AsyncMock()
        mock_clay.is_enabled.return_value = True

        with patch("app.services.enrichment.clay.clay_client", mock_clay):
            await _process_harvester_batch(
                batch_id="test_002",
                leads=[_make_lead()],
                concurrency=1,
                tiered_enrichment=True,
            )

        mock_clay.push_lead_to_clay.assert_not_called()

    @pytest.mark.asyncio()
    @patch("app.services.enrichment.pipeline.complete_batch")
    @patch("app.services.enrichment.pipeline.get_batch", return_value=MagicMock())
    @patch("app.services.enrichment.pipeline.get_rate_limit_tracker")
    @patch("app.services.enrichment.pipeline.apollo_client")
    async def test_clay_disabled_skips(
        self,
        mock_apollo: MagicMock,
        mock_rate_tracker: MagicMock,
        _mock_get_batch: MagicMock,
        _mock_complete: MagicMock,
    ) -> None:
        """Clay is not called when CLAY_ENABLED=false."""
        mock_rate_tracker.return_value = MagicMock()

        mock_tiered = MagicMock()
        mock_tiered.data = {"phone_numbers": []}
        mock_tiered.credits_used = 1
        mock_tiered.is_atl = True
        mock_tiered.persona_match = "av_director"
        mock_tiered.phone_revealed = False
        mock_tiered.atl_match = MagicMock(confidence=0.9, reason="Title match")
        mock_apollo.tiered_enrich = AsyncMock(return_value=mock_tiered)

        mock_clay = MagicMock()
        mock_clay.is_enabled.return_value = False

        with patch("app.services.enrichment.clay.clay_client", mock_clay):
            await _process_harvester_batch(
                batch_id="test_003",
                leads=[_make_lead()],
                concurrency=1,
                tiered_enrichment=True,
            )

        mock_clay.push_lead_to_clay.assert_not_called()

    @pytest.mark.asyncio()
    @patch("app.services.enrichment.pipeline.complete_batch")
    @patch("app.services.enrichment.pipeline.get_batch", return_value=MagicMock())
    @patch("app.services.enrichment.pipeline.get_rate_limit_tracker")
    @patch("app.services.enrichment.pipeline.apollo_client")
    async def test_clay_failure_doesnt_block_pipeline(
        self,
        mock_apollo: MagicMock,
        mock_rate_tracker: MagicMock,
        _mock_get_batch: MagicMock,
        mock_complete: MagicMock,  # Used in assertion below
    ) -> None:
        """Clay error is logged but pipeline continues successfully."""
        mock_rate_tracker.return_value = MagicMock()

        mock_tiered = MagicMock()
        mock_tiered.data = {"phone_numbers": []}
        mock_tiered.credits_used = 1
        mock_tiered.is_atl = True
        mock_tiered.persona_match = "av_director"
        mock_tiered.phone_revealed = False
        mock_tiered.atl_match = MagicMock(confidence=0.9, reason="Title match")
        mock_apollo.tiered_enrich = AsyncMock(return_value=mock_tiered)

        mock_clay = AsyncMock()
        mock_clay.is_enabled.return_value = True
        mock_clay.push_lead_to_clay.side_effect = Exception("Clay is down")

        with patch("app.services.enrichment.clay.clay_client", mock_clay):
            await _process_harvester_batch(
                batch_id="test_004",
                leads=[_make_lead()],
                concurrency=1,
                tiered_enrichment=True,
            )

        # Pipeline completed (complete_batch was called)
        mock_complete.assert_called_once_with("test_004")
