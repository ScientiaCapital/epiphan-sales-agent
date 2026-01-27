"""Tests for Apollo.io enrichment client."""

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
            }
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.enrich_contact("sarah.johnson@university.edu")

        assert result is not None
        assert result["first_name"] == "Sarah"
        assert result["title"] == "AV Director"
        assert "organization" in result

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
