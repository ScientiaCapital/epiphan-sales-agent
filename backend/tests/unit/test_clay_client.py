"""Tests for Clay.com enrichment client.

PHONES ARE GOLD! Clay is a fallback enrichment source that fills gaps
when Apollo can't find phones/emails via its 75+ provider waterfall.
"""

from unittest.mock import AsyncMock

import httpx
import pytest

from app.services.enrichment.clay import (
    _CLAY_PHONE_TYPE_MAP,
    ClayAPIError,
    ClayClient,
    clay_client,
)

# =============================================================================
# ClayClient.push_lead_to_clay()
# =============================================================================


class TestPushLeadToClay:
    """Tests for pushing leads to Clay's table webhook."""

    @pytest.fixture()
    def client(self) -> ClayClient:
        return ClayClient(
            webhook_url="https://api.clay.com/v1/tables/abc/webhooks/xyz",
            webhook_secret="test-secret",
            enabled=True,
        )

    @pytest.mark.asyncio()
    async def test_push_lead_success(self, client: ClayClient) -> None:
        """Successful push returns Clay's acknowledgement."""
        mock_response = httpx.Response(
            200,
            json={"status": "queued", "row_id": "row_123"},
            request=httpx.Request("POST", "https://api.clay.com/v1/tables/abc/webhooks/xyz"),
        )
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post.return_value = mock_response
        mock_http.is_closed = False
        client._client = mock_http
        result = await client.push_lead_to_clay({
            "email": "john@acme.com",
            "name": "John Doe",
            "company": "Acme Corp",
        })
        assert result["status"] == "queued"
        mock_http.post.assert_called_once()

    @pytest.mark.asyncio()
    async def test_push_lead_missing_config(self) -> None:
        """Raises ClayAPIError when webhook URL not configured."""
        client = ClayClient(webhook_url="", enabled=True)
        with pytest.raises(ClayAPIError, match="CLAY_TABLE_WEBHOOK_URL not configured"):
            await client.push_lead_to_clay({"email": "test@test.com"})

    @pytest.mark.asyncio()
    async def test_push_lead_api_error(self, client: ClayClient) -> None:
        """HTTP errors are wrapped in ClayAPIError."""
        mock_request = httpx.Request("POST", "https://api.clay.com/v1/tables/abc/webhooks/xyz")
        mock_response = httpx.Response(500, request=mock_request)
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post.side_effect = httpx.HTTPStatusError(
            "Server Error", request=mock_request, response=mock_response
        )
        mock_http.is_closed = False
        client._client = mock_http
        with pytest.raises(ClayAPIError, match="Clay API error: 500"):
            await client.push_lead_to_clay({"email": "test@test.com"})

    @pytest.mark.asyncio()
    async def test_push_lead_timeout(self, client: ClayClient) -> None:
        """Timeout is wrapped in ClayAPIError."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post.side_effect = httpx.TimeoutException("Connection timed out")
        mock_http.is_closed = False
        client._client = mock_http
        with pytest.raises(ClayAPIError, match="Clay webhook timeout"):
            await client.push_lead_to_clay({"email": "test@test.com"})


# =============================================================================
# ClayClient.parse_enrichment_result()
# =============================================================================


class TestParseEnrichmentResult:
    """Tests for parsing Clay callback payloads."""

    def test_parse_full_payload(self) -> None:
        """All fields present are parsed correctly."""
        payload = {
            "lead_id": "lead_123",
            "phones": [
                {"number": "+14155551234", "type": "direct", "provider": "zoominfo"},
                {"number": "+14155555678", "type": "mobile", "provider": "pdl"},
            ],
            "emails": [
                {"email": "john@acme.com", "type": "work", "provider": "contactout"},
            ],
            "company_name": "Acme Corp",
            "industry": "Technology",
            "employee_count": 500,
            "revenue_range": "$50M-$100M",
            "technologies": ["Zoom", "Panopto", "LMS"],
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "funding_info": {"last_round": "Series B", "amount": "$50M"},
        }
        result = ClayClient.parse_enrichment_result(payload)
        assert result.lead_id == "lead_123"
        assert len(result.phones) == 2
        assert result.phones[0]["number"] == "+14155551234"
        assert result.phones[0]["type"] == "work_direct"  # Mapped from "direct"
        assert result.phones[1]["type"] == "mobile"
        assert len(result.emails) == 1
        assert result.company_name == "Acme Corp"
        assert result.employee_count == 500
        assert result.technologies == ["Zoom", "Panopto", "LMS"]
        assert result.funding_info is not None

    def test_parse_phones_only(self) -> None:
        """Partial data (phones but no email) is handled."""
        payload = {
            "lead_id": "lead_456",
            "phones": [{"number": "+14155551234", "type": "work"}],
        }
        result = ClayClient.parse_enrichment_result(payload)
        assert len(result.phones) == 1
        assert result.emails == []
        assert result.company_name is None

    def test_parse_empty_payload(self) -> None:
        """Empty payload produces empty result with defaults."""
        result = ClayClient.parse_enrichment_result({})
        assert result.lead_id == ""
        assert result.phones == []
        assert result.emails == []
        assert result.company_name is None
        assert result.employee_count is None
        assert result.technologies == []

    def test_parse_malformed_phones(self) -> None:
        """Bad phone entries are skipped, valid ones kept."""
        payload = {
            "lead_id": "lead_789",
            "phones": [
                {"number": "", "type": "direct"},       # Empty number — skip
                "not a dict",                            # Wrong type — skip
                {"type": "mobile"},                      # Missing number — skip
                {"number": "+14155559999", "type": "mobile"},  # Valid
            ],
        }
        result = ClayClient.parse_enrichment_result(payload)
        assert len(result.phones) == 1
        assert result.phones[0]["number"] == "+14155559999"

    def test_parse_malformed_employee_count(self) -> None:
        """Non-integer employee_count is handled gracefully."""
        payload = {"lead_id": "x", "employee_count": "not-a-number"}
        result = ClayClient.parse_enrichment_result(payload)
        assert result.employee_count is None

    def test_parse_funding_info_non_dict(self) -> None:
        """Non-dict funding_info is ignored."""
        payload = {"lead_id": "x", "funding_info": "Series B"}
        result = ClayClient.parse_enrichment_result(payload)
        assert result.funding_info is None


# =============================================================================
# ClayClient.is_enabled()
# =============================================================================


class TestIsEnabled:
    """Tests for the feature flag check."""

    def test_enabled_true(self) -> None:
        """Returns True when both flag and URL are set."""
        client = ClayClient(
            webhook_url="https://clay.com/webhook",
            enabled=True,
        )
        assert client.is_enabled() is True

    def test_enabled_false_no_url(self) -> None:
        """Returns False when URL is missing."""
        client = ClayClient(webhook_url="", enabled=True)
        assert client.is_enabled() is False

    def test_enabled_false_flag_off(self) -> None:
        """Returns False when flag is off."""
        client = ClayClient(
            webhook_url="https://clay.com/webhook",
            enabled=False,
        )
        assert client.is_enabled() is False


# =============================================================================
# Phone type mapping
# =============================================================================


class TestPhoneTypeExtraction:
    """Tests for Clay phone type → our phone type mapping."""

    def test_direct_types_map_to_work_direct(self) -> None:
        """All 'direct' variants map to work_direct."""
        for clay_type in ["direct", "direct_dial", "work_direct"]:
            assert _CLAY_PHONE_TYPE_MAP[clay_type] == "work_direct"

    def test_mobile_types(self) -> None:
        """Mobile/cell/personal all map to mobile."""
        for clay_type in ["mobile", "cell", "personal"]:
            assert _CLAY_PHONE_TYPE_MAP[clay_type] == "mobile"

    def test_hq_types(self) -> None:
        """Company/HQ types map to work_hq."""
        for clay_type in ["company", "headquarters", "hq", "switchboard", "main"]:
            assert _CLAY_PHONE_TYPE_MAP[clay_type] == "work_hq"

    def test_unknown_type_defaults_to_work(self) -> None:
        """Unknown phone types default to 'work' in parse logic."""
        payload = {
            "lead_id": "x",
            "phones": [{"number": "+1234", "type": "fax"}],
        }
        result = ClayClient.parse_enrichment_result(payload)
        assert result.phones[0]["type"] == "work"  # Default


# =============================================================================
# Singleton
# =============================================================================


class TestSingleton:
    """Tests for module-level singleton."""

    def test_singleton_exists(self) -> None:
        """Module-level clay_client is importable."""
        assert clay_client is not None
        assert isinstance(clay_client, ClayClient)
