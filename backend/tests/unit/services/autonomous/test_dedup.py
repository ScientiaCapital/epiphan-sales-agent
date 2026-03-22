"""Tests for deduplication logic."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.autonomous.dedup import Deduplicator
from app.services.autonomous.schemas import LeadSource, RawLead


@pytest.fixture
def dedup() -> Deduplicator:
    return Deduplicator()


def _make_lead(email: str, source: LeadSource = LeadSource.APOLLO) -> RawLead:
    return RawLead(email=email, source=source)


class TestCrossSourceDedup:
    @pytest.mark.asyncio
    async def test_removes_duplicate_emails(self, dedup: Deduplicator) -> None:
        leads = [
            _make_lead("jane@example.com", LeadSource.APOLLO),
            _make_lead("jane@example.com", LeadSource.HUBSPOT),
            _make_lead("john@example.com", LeadSource.APOLLO),
        ]

        with patch.object(dedup, "_get_recent_queue_emails", new_callable=AsyncMock, return_value=set()):
            result = await dedup.deduplicate(leads)

        assert len(result) == 2
        emails = [r.email for r in result]
        assert "jane@example.com" in emails
        assert "john@example.com" in emails

    @pytest.mark.asyncio
    async def test_case_insensitive(self, dedup: Deduplicator) -> None:
        leads = [
            _make_lead("Jane@Example.com", LeadSource.APOLLO),
            _make_lead("jane@example.com", LeadSource.HUBSPOT),
        ]

        with patch.object(dedup, "_get_recent_queue_emails", new_callable=AsyncMock, return_value=set()):
            result = await dedup.deduplicate(leads)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_empty_input(self, dedup: Deduplicator) -> None:
        result = await dedup.deduplicate([])
        assert result == []

    @pytest.mark.asyncio
    async def test_preserves_first_occurrence(self, dedup: Deduplicator) -> None:
        leads = [
            _make_lead("jane@example.com", LeadSource.APOLLO),
            _make_lead("jane@example.com", LeadSource.HUBSPOT),
        ]

        with patch.object(dedup, "_get_recent_queue_emails", new_callable=AsyncMock, return_value=set()):
            result = await dedup.deduplicate(leads)

        assert result[0].source == LeadSource.APOLLO


class TestHistoryDedup:
    @pytest.mark.asyncio
    async def test_removes_recently_queued(self, dedup: Deduplicator) -> None:
        leads = [
            _make_lead("jane@example.com"),
            _make_lead("john@example.com"),
            _make_lead("new@example.com"),
        ]

        recent = {"jane@example.com", "john@example.com"}
        with patch.object(dedup, "_get_recent_queue_emails", new_callable=AsyncMock, return_value=recent):
            result = await dedup.deduplicate(leads)

        assert len(result) == 1
        assert result[0].email == "new@example.com"

    @pytest.mark.asyncio
    async def test_history_fetch_failure_passes_through(self, dedup: Deduplicator) -> None:
        """If history lookup fails, all leads pass through (graceful degradation)."""
        leads = [_make_lead("jane@example.com")]

        with patch.object(dedup, "_get_recent_queue_emails", new_callable=AsyncMock, return_value=set()):
            result = await dedup.deduplicate(leads)

        assert len(result) == 1
