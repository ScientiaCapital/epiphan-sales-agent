"""Tests for Lead Research Agent tools."""

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.tools import ToolException

from app.data.lead_schemas import Lead


class TestResearchTools:
    """Tests for research enrichment tools."""

    @pytest.fixture
    def sample_lead(self) -> Lead:
        """Create a sample lead for testing."""
        return Lead(
            hubspot_id="hs-lead-123",
            email="sarah.johnson@stateuniversity.edu",
            first_name="Sarah",
            last_name="Johnson",
            company="State University",
            title="AV Director",
            phone="+1-555-123-4567",
        )

    @pytest.mark.asyncio
    async def test_enrich_from_apollo(self, sample_lead: Lead):
        """Test Apollo enrichment tool."""
        from app.services.langgraph.tools.research_tools import enrich_from_apollo

        mock_result = {
            "first_name": "Sarah",
            "last_name": "Johnson",
            "title": "Director of AV Services",
            "organization": {"name": "State University"},
        }

        with patch(
            "app.services.langgraph.tools.research_tools.apollo_client.enrich_contact",
            new_callable=AsyncMock,
        ) as mock_enrich:
            mock_enrich.return_value = mock_result

            result = await enrich_from_apollo(sample_lead.email)

        assert result is not None
        assert result["first_name"] == "Sarah"
        mock_enrich.assert_called_once_with("sarah.johnson@stateuniversity.edu")

    @pytest.mark.asyncio
    async def test_enrich_from_apollo_raises_on_not_found(self, sample_lead: Lead):
        """Test Apollo enrichment raises ToolException when not found."""
        from app.services.langgraph.tools.research_tools import enrich_from_apollo

        with patch(
            "app.services.langgraph.tools.research_tools.apollo_client.enrich_contact",
            new_callable=AsyncMock,
        ) as mock_enrich:
            mock_enrich.return_value = None

            with pytest.raises(ToolException) as exc_info:
                await enrich_from_apollo(sample_lead.email)

        assert "No Apollo data found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_scrape_company_website(self):
        """Test web scraping tool for company info."""
        from app.services.langgraph.tools.research_tools import scrape_company_website

        mock_about = {
            "about_url": "https://stateuniversity.edu/about",
            "about_text": "State University is a leading research institution...",
        }

        with patch(
            "app.services.langgraph.tools.research_tools.web_scraper.scrape_company_info",
            new_callable=AsyncMock,
        ) as mock_scrape:
            mock_scrape.return_value = mock_about

            result = await scrape_company_website("stateuniversity.edu")

        assert result is not None
        assert "about_text" in result
        assert "research institution" in result["about_text"]

    @pytest.mark.asyncio
    async def test_scrape_company_news(self):
        """Test web scraping tool for company news."""
        from app.services.langgraph.tools.research_tools import scrape_company_news

        mock_news = [
            {
                "title": "State University Receives $10M Grant",
                "date": "2025-01-15",
                "summary": "For new AV equipment...",
            }
        ]

        with patch(
            "app.services.langgraph.tools.research_tools.web_scraper.extract_news",
            new_callable=AsyncMock,
        ) as mock_news_extract:
            mock_news_extract.return_value = mock_news

            result = await scrape_company_news("stateuniversity.edu")

        assert result is not None
        assert len(result) == 1
        assert "Grant" in result[0]["title"]

    @pytest.mark.asyncio
    async def test_get_company_domain_from_email(self):
        """Test extracting domain from email."""
        from app.services.langgraph.tools.research_tools import get_company_domain

        domain = get_company_domain("sarah.johnson@stateuniversity.edu")
        assert domain == "stateuniversity.edu"

    @pytest.mark.asyncio
    async def test_get_company_domain_handles_subdomains(self):
        """Test domain extraction handles subdomains."""
        from app.services.langgraph.tools.research_tools import get_company_domain

        # Should keep full subdomain for .edu domains
        domain = get_company_domain("user@mail.company.com")
        assert domain == "mail.company.com" or domain == "company.com"

    @pytest.mark.asyncio
    async def test_combine_enrichment_data(self):
        """Test combining data from multiple sources."""
        from app.services.langgraph.tools.research_tools import combine_enrichment_data

        apollo = {"first_name": "Sarah", "title": "AV Director", "industry": "Higher Education"}
        scraped = {"about_text": "Leading institution..."}

        result = combine_enrichment_data(apollo, scraped)

        assert result["first_name"] == "Sarah"
        assert result["industry"] == "Higher Education"
        assert result["about_text"] == "Leading institution..."
