"""Tests for outreach email drafter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.autonomous.drafter import OutreachDrafter


@pytest.fixture
def drafter() -> OutreachDrafter:
    return OutreachDrafter()


class TestDraftEmail:
    @pytest.mark.asyncio
    async def test_drafts_email_with_valid_response(self, drafter: OutreachDrafter) -> None:
        mock_response = MagicMock()
        mock_response.content = '{"subject": "Quick question about lecture capture", "body": "Hi Jane, most universities lose 40% of lecture content because recording is opt-in.", "pain_point": "content_loss"}'

        with patch.object(drafter, "_llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            result = await drafter.draft_email(
                lead_name="Jane",
                lead_title="Director of AV",
                lead_company="State University",
                lead_industry="higher education",
            )

        assert result.subject == "Quick question about lecture capture"
        assert "Jane" in result.body
        assert result.pain_point == "content_loss"
        assert result.methodology == "challenger"

    @pytest.mark.asyncio
    async def test_handles_malformed_json(self, drafter: OutreachDrafter) -> None:
        mock_response = MagicMock()
        mock_response.content = "This is not JSON at all"

        with patch.object(drafter, "_llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            result = await drafter.draft_email(
                lead_name="Jane",
                lead_title="Director",
                lead_company="Acme",
                lead_industry=None,
            )

        assert result.pain_point == "parse_error"
        assert result.subject is not None

    @pytest.mark.asyncio
    async def test_handles_llm_failure(self, drafter: OutreachDrafter) -> None:
        with patch.object(drafter, "_llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM down"))
            result = await drafter.draft_email(
                lead_name="Jane",
                lead_title="Director",
                lead_company="Acme",
                lead_industry=None,
            )

        assert result.pain_point == "generic_fallback"
        assert "Acme" in result.subject

    @pytest.mark.asyncio
    async def test_strips_markdown_fences(self, drafter: OutreachDrafter) -> None:
        mock_response = MagicMock()
        mock_response.content = '```json\n{"subject": "Test", "body": "Hello", "pain_point": "test"}\n```'

        with patch.object(drafter, "_llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            result = await drafter.draft_email(
                lead_name="Jane",
                lead_title=None,
                lead_company=None,
                lead_industry=None,
            )

        assert result.subject == "Test"


class TestBuildUserPrompt:
    def test_includes_all_fields(self, drafter: OutreachDrafter) -> None:
        prompt = drafter._build_user_prompt(
            lead_name="Jane",
            lead_title="Director of AV",
            lead_company="State University",
            lead_industry="higher education",
            research_summary="They recently expanded campus",
            qualification_summary="Tier 1, Score: 85",
        )

        assert "Jane" in prompt
        assert "Director of AV" in prompt
        assert "State University" in prompt
        assert "recently expanded" in prompt
        assert "Tier 1" in prompt

    def test_handles_none_fields(self, drafter: OutreachDrafter) -> None:
        prompt = drafter._build_user_prompt(
            lead_name=None,
            lead_title=None,
            lead_company=None,
            lead_industry=None,
            research_summary=None,
            qualification_summary=None,
        )

        assert "Write a cold outreach email" in prompt
