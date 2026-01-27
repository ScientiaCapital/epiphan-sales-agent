"""Tests for Clearbit enrichment client."""

from unittest.mock import AsyncMock, patch

import pytest


class TestClearbitClient:
    """Tests for ClearbitClient."""

    def test_client_initializes(self):
        """Test that client initializes with API key."""
        from app.services.enrichment.clearbit import ClearbitClient

        client = ClearbitClient()
        assert client is not None

    @pytest.mark.asyncio
    async def test_enrich_company_returns_data(self):
        """Test enriching a company by domain."""
        from app.services.enrichment.clearbit import ClearbitClient

        client = ClearbitClient()

        mock_response = {
            "name": "State University",
            "legalName": "State University System",
            "domain": "stateuniversity.edu",
            "category": {
                "sector": "Education",
                "industryGroup": "Higher Education",
                "industry": "Universities",
            },
            "metrics": {
                "employees": 5000,
                "employeesRange": "1001-5000",
                "annualRevenue": None,
            },
            "geo": {
                "city": "Springfield",
                "state": "IL",
                "country": "US",
            },
            "description": "A leading public university",
            "linkedin": {"handle": "state-university"},
            "twitter": {"handle": "stateuniv"},
            "tech": ["Salesforce", "Workday", "Canvas"],
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.enrich_company("stateuniversity.edu")

        assert result is not None
        assert result["name"] == "State University"
        assert result["industry"] == "Universities"
        assert result["employees"] == 5000

    @pytest.mark.asyncio
    async def test_enrich_company_handles_not_found(self):
        """Test handling when company not found."""
        from app.services.enrichment.clearbit import ClearbitClient

        client = ClearbitClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = None

            result = await client.enrich_company("unknown-domain-xyz.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_enrich_person_returns_data(self):
        """Test enriching a person by email."""
        from app.services.enrichment.clearbit import ClearbitClient

        client = ClearbitClient()

        mock_response = {
            "person": {
                "name": {"givenName": "Sarah", "familyName": "Johnson"},
                "employment": {
                    "name": "State University",
                    "title": "AV Director",
                    "seniority": "director",
                },
                "linkedin": {"handle": "sarahjohnson"},
            },
            "company": {
                "name": "State University",
                "domain": "stateuniversity.edu",
            },
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.enrich_person("sarah.johnson@stateuniversity.edu")

        assert result is not None
        assert result["first_name"] == "Sarah"
        assert result["title"] == "AV Director"

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        """Test handling API errors gracefully."""
        from app.services.enrichment.clearbit import ClearbitAPIError, ClearbitClient

        client = ClearbitClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = ClearbitAPIError("Rate limit exceeded")

            with pytest.raises(ClearbitAPIError):
                await client.enrich_company("example.com")

    @pytest.mark.asyncio
    async def test_extracts_tech_stack(self):
        """Test extracting technology stack from company data."""
        from app.services.enrichment.clearbit import ClearbitClient

        client = ClearbitClient()

        mock_response = {
            "name": "Tech Corp",
            "domain": "techcorp.com",
            "category": {"industry": "Technology"},
            "metrics": {"employees": 100},
            "tech": ["React", "Node.js", "AWS", "PostgreSQL"],
            "geo": {"country": "US"},
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await client.enrich_company("techcorp.com")

        assert result is not None
        assert "tech_stack" in result
        assert "AWS" in result["tech_stack"]
