"""Tests for Apollo.io enrichment client.

PHONES ARE GOLD! Tests verify phone number extraction is working correctly.
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestApolloClient:
    """Tests for ApolloClient."""

    def test_client_initializes(self):
        """Test that client initializes with API key."""
        from app.services.enrichment.apollo import ApolloClient

        client = ApolloClient()
        assert client is not None

    @pytest.mark.asyncio
    async def test_enrich_contact_returns_data(self):
        """Test enriching a contact by email."""
        from app.services.enrichment.apollo import ApolloClient

        client = ApolloClient()

        mock_response = {
            "person": {
                "first_name": "Sarah",
                "last_name": "Johnson",
                "title": "AV Director",
                "linkedin_url": "https://linkedin.com/in/sarahjohnson",
                "organization": {
                    "name": "State University",
                    "industry": "Higher Education",
                    "estimated_num_employees": 5000,
                },
                "phone_numbers": [],
            }
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.enrich_contact("sarah.johnson@university.edu")

        assert result is not None
        assert result["first_name"] == "Sarah"
        assert result["title"] == "AV Director"
        assert "organization" in result
        # Verify phone fields exist (PHONES ARE GOLD!)
        assert "phone_numbers" in result
        assert "direct_phone" in result
        assert "mobile_phone" in result
        assert "work_phone" in result

    @pytest.mark.asyncio
    async def test_enrich_contact_sends_reveal_phone_number(self):
        """Test that reveal_phone_number=true is sent to Apollo. PHONES ARE GOLD!"""
        from app.services.enrichment.apollo import ApolloClient

        client = ApolloClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"person": None}

            await client.enrich_contact("test@example.com")

            # Verify the payload includes reveal_phone_number=true
            call_args = mock_req.call_args
            assert call_args is not None
            payload = call_args[0][2]  # Third positional arg is the data dict
            assert payload["reveal_phone_number"] is True

    @pytest.mark.asyncio
    async def test_enrich_contact_extracts_direct_phone(self):
        """Test direct phone extraction. PHONES ARE GOLD!"""
        from app.services.enrichment.apollo import ApolloClient

        client = ApolloClient()

        mock_response = {
            "person": {
                "first_name": "John",
                "phone_numbers": [
                    {"sanitized_number": "+1-555-DIRECT", "type": "work_direct"},
                    {"sanitized_number": "+1-555-MOBILE", "type": "mobile"},
                ],
            }
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.enrich_contact("john@example.com")

        assert result["direct_phone"] == "+1-555-DIRECT"
        assert result["mobile_phone"] == "+1-555-MOBILE"

    @pytest.mark.asyncio
    async def test_enrich_contact_extracts_work_phone(self):
        """Test work phone extraction (not direct, not HQ). PHONES ARE GOLD!"""
        from app.services.enrichment.apollo import ApolloClient

        client = ApolloClient()

        mock_response = {
            "person": {
                "first_name": "Jane",
                "phone_numbers": [
                    {"sanitized_number": "+1-555-WORK", "type": "work"},
                    {"sanitized_number": "+1-555-HQ", "type": "work_hq"},
                ],
            }
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.enrich_contact("jane@example.com")

        assert result["work_phone"] == "+1-555-WORK"
        # HQ phone should not be extracted as work phone
        assert result["direct_phone"] is None

    @pytest.mark.asyncio
    async def test_enrich_contact_uses_number_field_fallback(self):
        """Test fallback to 'number' field if 'sanitized_number' missing."""
        from app.services.enrichment.apollo import ApolloClient

        client = ApolloClient()

        mock_response = {
            "person": {
                "first_name": "Bob",
                "phone_numbers": [
                    {"number": "+1-555-FALLBACK", "type": "mobile"},
                ],
            }
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.enrich_contact("bob@example.com")

        assert result["mobile_phone"] == "+1-555-FALLBACK"

    @pytest.mark.asyncio
    async def test_enrich_contact_webhook_url_parameter(self):
        """Test webhook_url is passed to Apollo for async phone delivery."""
        from app.services.enrichment.apollo import ApolloClient

        client = ApolloClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"person": None}

            await client.enrich_contact(
                "test@example.com",
                webhook_url="https://api.example.com/webhooks/apollo",
            )

            call_args = mock_req.call_args
            payload = call_args[0][2]
            assert payload["webhook_url"] == "https://api.example.com/webhooks/apollo"

    @pytest.mark.asyncio
    async def test_enrich_contact_reveal_phone_disabled(self):
        """Test reveal_phone can be disabled (saves credits for non-ICP leads)."""
        from app.services.enrichment.apollo import ApolloClient

        client = ApolloClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"person": None}

            await client.enrich_contact("test@example.com", reveal_phone=False)

            call_args = mock_req.call_args
            payload = call_args[0][2]
            assert payload["reveal_phone_number"] is False

    @pytest.mark.asyncio
    async def test_enrich_contact_handles_not_found(self):
        """Test handling when contact not found."""
        from app.services.enrichment.apollo import ApolloClient

        client = ApolloClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"person": None}

            result = await client.enrich_contact("unknown@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_enrich_company_returns_data(self):
        """Test enriching a company by domain."""
        from app.services.enrichment.apollo import ApolloClient

        client = ApolloClient()

        mock_response = {
            "organization": {
                "name": "State University",
                "website_url": "https://stateuniversity.edu",
                "industry": "Higher Education",
                "estimated_num_employees": 5000,
                "founded_year": 1850,
                "linkedin_url": "https://linkedin.com/company/state-university",
            }
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.enrich_company("stateuniversity.edu")

        assert result is not None
        assert result["name"] == "State University"
        assert result["industry"] == "Higher Education"

    @pytest.mark.asyncio
    async def test_search_people_returns_list(self):
        """Test searching for people by criteria."""
        from app.services.enrichment.apollo import ApolloClient

        client = ApolloClient()

        mock_response = {
            "people": [
                {
                    "first_name": "Sarah",
                    "last_name": "Johnson",
                    "title": "AV Director",
                    "email": "sarah@university.edu",
                },
                {
                    "first_name": "Mike",
                    "last_name": "Smith",
                    "title": "IT Director",
                    "email": "mike@university.edu",
                },
            ],
            "pagination": {"total_entries": 2},
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.search_people(
                titles=["AV Director", "IT Director"],
                industries=["Higher Education"],
            )

        assert len(result) == 2
        assert result[0]["first_name"] == "Sarah"

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        """Test handling API errors gracefully."""
        from app.services.enrichment.apollo import ApolloAPIError, ApolloClient

        client = ApolloClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = ApolloAPIError("Rate limit exceeded")

            with pytest.raises(ApolloAPIError):
                await client.enrich_contact("test@example.com")
