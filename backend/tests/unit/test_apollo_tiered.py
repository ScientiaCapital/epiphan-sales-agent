"""Tests for Apollo.io tiered enrichment strategy.

Tests the credit-saving two-phase approach:
- Phase 1 (1 credit): Basic enrichment to identify ATL
- Phase 2 (8 credits): Phone reveal ONLY for ATL decision-makers

PHONES ARE GOLD - but only for people Tim will actually call.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.enrichment.apollo import (
    ApolloAPIError,
    ApolloClient,
    TieredEnrichmentResult,
)


class TestTieredEnrichmentResult:
    """Tests for TieredEnrichmentResult dataclass."""

    def test_default_values(self):
        """Test default values for TieredEnrichmentResult."""
        result = TieredEnrichmentResult(found=False)

        assert result.found is False
        assert result.data is None
        assert result.is_atl is False
        assert result.atl_match is None
        assert result.persona_match is None
        assert result.phone_revealed is False
        assert result.credits_used == 0
        assert result.error is None

    def test_non_atl_result(self):
        """Test result for non-ATL contact (saved 7 credits)."""
        result = TieredEnrichmentResult(
            found=True,
            data={"title": "Marketing Analyst"},
            is_atl=False,
            phone_revealed=False,
            credits_used=1,  # Only Phase 1
        )

        assert result.found is True
        assert result.is_atl is False
        assert result.phone_revealed is False
        assert result.credits_used == 1

    def test_atl_result(self):
        """Test result for ATL contact (full enrichment)."""
        result = TieredEnrichmentResult(
            found=True,
            data={
                "title": "AV Director",
                "phone_numbers": [{"sanitized_number": "+1-555-1234", "type": "work_direct"}],
            },
            is_atl=True,
            persona_match="av_director",
            phone_revealed=True,
            credits_used=9,  # Phase 1 + Phase 2
        )

        assert result.found is True
        assert result.is_atl is True
        assert result.persona_match == "av_director"
        assert result.phone_revealed is True
        assert result.credits_used == 9


class TestTieredEnrichNonATL:
    """Tests for tiered enrichment with non-ATL contacts."""

    @pytest.mark.asyncio
    async def test_non_atl_skips_phone_reveal(self):
        """Non-ATL contact should NOT get phone reveal (saves 7 credits)."""
        client = ApolloClient()

        # Mock basic enrichment response (non-ATL title)
        mock_basic_response = {
            "person": {
                "first_name": "John",
                "last_name": "Doe",
                "title": "Marketing Analyst",  # Non-ATL
                "seniority": "entry",
                "phone_numbers": [],  # No phones in Phase 1
            }
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_basic_response

            result = await client.tiered_enrich(email="john@example.com")

        assert result.found is True
        assert result.is_atl is False
        assert result.phone_revealed is False
        assert result.credits_used == 1  # Saved 7 credits!

        # Verify only ONE API call was made (no Phase 2)
        assert mock_req.call_count == 1
        call_args = mock_req.call_args[0][2]
        assert call_args["reveal_phone_number"] is False

    @pytest.mark.asyncio
    async def test_non_atl_student_title(self):
        """Student title should be non-ATL and skip phone reveal."""
        client = ApolloClient()

        mock_response = {
            "person": {
                "first_name": "Jane",
                "title": "Graduate Student",
                "seniority": "student",
            }
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.tiered_enrich(email="student@university.edu")

        assert result.is_atl is False
        assert result.phone_revealed is False
        assert result.credits_used == 1
        assert mock_req.call_count == 1

    @pytest.mark.asyncio
    async def test_non_atl_uses_harvester_title_fallback(self):
        """If Apollo returns no title, use Harvester title for ATL check."""
        client = ApolloClient()

        # Apollo returns no title
        mock_response = {
            "person": {
                "first_name": "Bob",
                "title": None,  # No title from Apollo
            }
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.tiered_enrich(
                email="bob@example.com",
                title="Intern",  # Harvester provided non-ATL title
            )

        assert result.is_atl is False
        assert result.credits_used == 1


class TestTieredEnrichATL:
    """Tests for tiered enrichment with ATL contacts."""

    @pytest.mark.asyncio
    async def test_atl_gets_phone_reveal(self):
        """ATL decision-maker should get phone reveal (9 credits total)."""
        client = ApolloClient()

        # Phase 1: Basic enrichment
        mock_basic_response = {
            "person": {
                "first_name": "Sarah",
                "last_name": "Johnson",
                "title": "AV Director",  # ATL!
                "seniority": "director",
                "phone_numbers": [],
            }
        }

        # Phase 2: Full enrichment with phones
        mock_full_response = {
            "person": {
                "first_name": "Sarah",
                "last_name": "Johnson",
                "title": "AV Director",
                "seniority": "director",
                "phone_numbers": [
                    {"sanitized_number": "+1-555-DIRECT", "type": "work_direct"},
                    {"sanitized_number": "+1-555-MOBILE", "type": "mobile"},
                ],
            }
        }

        call_count = 0

        async def mock_request(_method, _endpoint, _data=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Phase 1 (basic)
                return mock_basic_response
            else:
                # Phase 2 (with phones)
                return mock_full_response

        with patch.object(client, "_make_request", side_effect=mock_request):
            result = await client.tiered_enrich(email="sarah@university.edu")

        assert result.found is True
        assert result.is_atl is True
        assert result.persona_match == "av_director"
        assert result.phone_revealed is True
        assert result.credits_used == 9  # 1 + 8
        assert call_count == 2  # Two API calls

        # Verify phone data is in result
        assert result.data is not None
        assert result.data["direct_phone"] == "+1-555-DIRECT"
        assert result.data["mobile_phone"] == "+1-555-MOBILE"

    @pytest.mark.asyncio
    async def test_atl_director_keyword(self):
        """Director title (not persona match) should still be ATL."""
        client = ApolloClient()

        mock_basic = {"person": {"title": "Director of Marketing", "seniority": "director"}}
        mock_full = {
            "person": {
                "title": "Director of Marketing",
                "phone_numbers": [{"sanitized_number": "+1-555-1234", "type": "work_direct"}],
            }
        }

        calls = []

        async def mock_request(_method, _endpoint, data=None):
            calls.append(data)
            return mock_basic if len(calls) == 1 else mock_full

        with patch.object(client, "_make_request", side_effect=mock_request):
            result = await client.tiered_enrich(email="director@company.com")

        assert result.is_atl is True
        assert result.phone_revealed is True
        assert result.credits_used == 9

    @pytest.mark.asyncio
    async def test_atl_vp_title(self):
        """VP title should be ATL."""
        client = ApolloClient()

        mock_response = {"person": {"title": "VP of Sales", "seniority": "vp"}}

        call_count = 0

        async def mock_request(_method, _endpoint, _data=None):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch.object(client, "_make_request", side_effect=mock_request):
            result = await client.tiered_enrich(email="vp@company.com")

        assert result.is_atl is True
        assert result.phone_revealed is True
        assert call_count == 2  # Phase 1 + Phase 2


class TestTieredEnrichErrorHandling:
    """Tests for error handling in tiered enrichment."""

    @pytest.mark.asyncio
    async def test_contact_not_found(self):
        """Handle contact not found in Apollo."""
        client = ApolloClient()

        mock_response = {"person": None}

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.tiered_enrich(email="unknown@example.com")

        assert result.found is False
        assert result.credits_used == 1  # Still costs 1 credit
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_phase1_api_error(self):
        """Handle API error in Phase 1."""
        client = ApolloClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = ApolloAPIError("Rate limit exceeded")

            result = await client.tiered_enrich(email="test@example.com")

        assert result.found is False
        assert result.credits_used == 1
        assert "rate limit" in result.error.lower()

    @pytest.mark.asyncio
    async def test_phase2_api_error_returns_basic_data(self):
        """If Phase 2 fails, return basic data from Phase 1."""
        client = ApolloClient()

        mock_basic = {"person": {"title": "AV Director", "seniority": "director"}}
        call_count = 0

        async def mock_request(_method, _endpoint, _data=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_basic
            else:
                raise ApolloAPIError("Rate limit exceeded")

        with patch.object(client, "_make_request", side_effect=mock_request):
            result = await client.tiered_enrich(email="av@university.edu")

        assert result.found is True
        assert result.is_atl is True
        assert result.phone_revealed is False  # Phase 2 failed
        assert result.credits_used == 1  # Only Phase 1 charged
        assert result.data is not None  # Still have basic data
        assert "rate limit" in result.error.lower()


class TestTieredEnrichWebhook:
    """Tests for webhook URL handling in tiered enrichment."""

    @pytest.mark.asyncio
    async def test_webhook_passed_to_phase2(self):
        """Webhook URL should be passed to Phase 2 for async phone delivery."""
        client = ApolloClient()

        mock_basic = {"person": {"title": "AV Director", "seniority": "director"}}
        mock_full = {
            "person": {
                "title": "AV Director",
                "phone_numbers": [{"sanitized_number": "+1-555-1234", "type": "mobile"}],
            }
        }

        calls = []

        async def mock_request(_method, _endpoint, data=None):
            calls.append(data)
            return mock_basic if len(calls) == 1 else mock_full

        with patch.object(client, "_make_request", side_effect=mock_request):
            result = await client.tiered_enrich(
                email="av@example.com",
                webhook_url="https://api.example.com/webhooks/apollo",
            )

        assert result.phone_revealed is True
        assert len(calls) == 2

        # Phase 1 should NOT have webhook
        assert "webhook_url" not in calls[0] or calls[0].get("webhook_url") is None

        # Phase 2 should have webhook
        assert calls[1].get("webhook_url") == "https://api.example.com/webhooks/apollo"

    @pytest.mark.asyncio
    async def test_no_webhook_for_non_atl(self):
        """Non-ATL should not make Phase 2 call, so no webhook needed."""
        client = ApolloClient()

        mock_response = {"person": {"title": "Intern", "seniority": "intern"}}

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.tiered_enrich(
                email="intern@example.com",
                webhook_url="https://api.example.com/webhooks/apollo",
            )

        assert result.is_atl is False
        assert result.phone_revealed is False
        assert mock_req.call_count == 1  # Only Phase 1


class TestCreditCalculations:
    """Tests verifying credit calculations are correct."""

    @pytest.mark.asyncio
    async def test_credit_math_non_atl(self):
        """Non-ATL lead: 1 credit (saves 7 vs legacy)."""
        client = ApolloClient()

        mock_response = {"person": {"title": "Analyst"}}

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.tiered_enrich(email="analyst@example.com")

        assert result.credits_used == 1
        # Legacy would have used 8 credits
        credits_saved = 8 - result.credits_used
        assert credits_saved == 7

    @pytest.mark.asyncio
    async def test_credit_math_atl(self):
        """ATL lead: 9 credits (1 basic + 8 phone)."""
        client = ApolloClient()

        mock_response = {"person": {"title": "VP of Engineering", "seniority": "vp"}}

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.tiered_enrich(email="vp@example.com")

        assert result.credits_used == 9
        # Legacy would have used 8 credits, so tiered is slightly more
        # But we get smarter decisions on WHO gets phones

    @pytest.mark.asyncio
    async def test_credit_math_not_found(self):
        """Not found: 1 credit (can't recover)."""
        client = ApolloClient()

        mock_response = {"person": None}

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.tiered_enrich(email="unknown@example.com")

        assert result.credits_used == 1

    @pytest.mark.asyncio
    async def test_batch_credit_savings(self):
        """Simulate batch to verify credit savings math."""
        # Typical batch: 75% non-ATL, 25% ATL
        non_atl_count = 75
        atl_count = 25
        total = non_atl_count + atl_count

        # Tiered approach
        tiered_credits = (non_atl_count * 1) + (atl_count * 9)
        # = 75 + 225 = 300

        # Legacy approach (8 per lead)
        legacy_credits = total * 8
        # = 800

        credits_saved = legacy_credits - tiered_credits
        savings_percent = (credits_saved / legacy_credits) * 100

        assert tiered_credits == 300
        assert legacy_credits == 800
        assert credits_saved == 500
        assert savings_percent == 62.5


class TestATLMatchTracking:
    """Tests for ATL match tracking in results."""

    @pytest.mark.asyncio
    async def test_atl_match_included_for_atl(self):
        """ATL match should be included in result for ATL contacts."""
        client = ApolloClient()

        mock_response = {"person": {"title": "AV Director", "seniority": "director"}}

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.tiered_enrich(email="av@example.com")

        assert result.atl_match is not None
        assert result.atl_match.is_atl is True
        assert result.atl_match.persona_id == "av_director"
        assert result.atl_match.confidence == 1.0
        assert "exact match" in result.atl_match.reason.lower()

    @pytest.mark.asyncio
    async def test_atl_match_included_for_non_atl(self):
        """ATL match should be included in result for non-ATL contacts too."""
        client = ApolloClient()

        mock_response = {"person": {"title": "Intern", "seniority": "intern"}}

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.tiered_enrich(email="intern@example.com")

        assert result.atl_match is not None
        assert result.atl_match.is_atl is False
        assert result.atl_match.reason is not None
