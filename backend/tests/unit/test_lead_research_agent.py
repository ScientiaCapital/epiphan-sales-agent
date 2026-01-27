"""Tests for Lead Research Agent."""

from unittest.mock import AsyncMock, patch

import pytest

from app.data.lead_schemas import Lead


class TestLeadResearchAgent:
    """Tests for LeadResearchAgent."""

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
        )

    def test_agent_initializes(self):
        """Test that agent initializes."""
        from app.services.langgraph.agents.lead_research import LeadResearchAgent

        agent = LeadResearchAgent()
        assert agent is not None

    @pytest.mark.asyncio
    async def test_run_returns_research_brief(self, sample_lead: Lead):
        """Test running agent produces a research brief."""
        from app.services.langgraph.agents.lead_research import LeadResearchAgent

        agent = LeadResearchAgent()

        # Mock all enrichment sources
        with (
            patch(
                "app.services.langgraph.agents.lead_research.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.lead_research.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
            patch(
                "app.services.langgraph.agents.lead_research.scrape_company_website",
                new_callable=AsyncMock,
            ) as mock_scrape,
            patch(
                "app.services.langgraph.agents.lead_research.scrape_company_news",
                new_callable=AsyncMock,
            ) as mock_news,
        ):
            mock_apollo.return_value = {
                "first_name": "Sarah",
                "title": "Director of AV Services",
                "seniority": "director",
            }
            mock_clearbit.return_value = {
                "name": "State University",
                "industry": "Higher Education",
                "employees": 5000,
                "tech_stack": ["Canvas", "Zoom"],
            }
            mock_scrape.return_value = {
                "about_text": "State University is a leading research institution..."
            }
            mock_news.return_value = [
                {"title": "New AV Lab Opens", "date": "2025-01-15"}
            ]

            result = await agent.run(sample_lead)

        assert result is not None
        assert "research_brief" in result
        assert "talking_points" in result

    @pytest.mark.asyncio
    async def test_handles_missing_enrichment_data(self, sample_lead: Lead):
        """Test agent handles when enrichment returns None."""
        from app.services.langgraph.agents.lead_research import LeadResearchAgent

        agent = LeadResearchAgent()

        with (
            patch(
                "app.services.langgraph.agents.lead_research.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.lead_research.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
            patch(
                "app.services.langgraph.agents.lead_research.scrape_company_website",
                new_callable=AsyncMock,
            ) as mock_scrape,
            patch(
                "app.services.langgraph.agents.lead_research.scrape_company_news",
                new_callable=AsyncMock,
            ) as mock_news,
        ):
            # All sources return None/empty
            mock_apollo.return_value = None
            mock_clearbit.return_value = None
            mock_scrape.return_value = None
            mock_news.return_value = []

            result = await agent.run(sample_lead)

        # Should still return a result, even if sparse
        assert result is not None
        assert "talking_points" in result

    @pytest.mark.asyncio
    async def test_quick_research_depth(self, sample_lead: Lead):
        """Test quick research skips web scraping."""
        from app.services.langgraph.agents.lead_research import LeadResearchAgent

        agent = LeadResearchAgent()

        with (
            patch(
                "app.services.langgraph.agents.lead_research.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.lead_research.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
            patch(
                "app.services.langgraph.agents.lead_research.scrape_company_website",
                new_callable=AsyncMock,
            ) as mock_scrape,
            patch(
                "app.services.langgraph.agents.lead_research.scrape_company_news",
                new_callable=AsyncMock,
            ) as mock_news,
        ):
            mock_apollo.return_value = {"title": "AV Director"}
            mock_clearbit.return_value = {"industry": "Higher Education"}
            mock_scrape.return_value = None
            mock_news.return_value = []

            await agent.run(sample_lead, research_depth="quick")

        # Web scraping should not be called for quick
        mock_scrape.assert_not_called()
        mock_news.assert_not_called()

    @pytest.mark.asyncio
    async def test_extracts_talking_points(self, sample_lead: Lead):
        """Test agent extracts relevant talking points."""
        from app.services.langgraph.agents.lead_research import LeadResearchAgent

        agent = LeadResearchAgent()

        with (
            patch(
                "app.services.langgraph.agents.lead_research.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.lead_research.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
            patch(
                "app.services.langgraph.agents.lead_research.scrape_company_website",
                new_callable=AsyncMock,
            ) as mock_scrape,
            patch(
                "app.services.langgraph.agents.lead_research.scrape_company_news",
                new_callable=AsyncMock,
            ) as mock_news,
        ):
            mock_apollo.return_value = {"title": "AV Director"}
            mock_clearbit.return_value = {
                "industry": "Higher Education",
                "employees": 5000,
                "tech_stack": ["Zoom", "Canvas", "Panopto"],
            }
            mock_scrape.return_value = {
                "about_text": "State University recently invested in new lecture capture..."
            }
            mock_news.return_value = [
                {"title": "University Expands Online Learning Program"}
            ]

            result = await agent.run(sample_lead, research_depth="deep")

        # Should extract relevant talking points
        assert len(result.get("talking_points", [])) > 0

    @pytest.mark.asyncio
    async def test_identifies_risk_factors(self, sample_lead: Lead):
        """Test agent identifies potential risk factors."""
        from app.services.langgraph.agents.lead_research import LeadResearchAgent

        agent = LeadResearchAgent()

        with (
            patch(
                "app.services.langgraph.agents.lead_research.enrich_from_apollo",
                new_callable=AsyncMock,
            ) as mock_apollo,
            patch(
                "app.services.langgraph.agents.lead_research.enrich_from_clearbit",
                new_callable=AsyncMock,
            ) as mock_clearbit,
            patch(
                "app.services.langgraph.agents.lead_research.scrape_company_website",
                new_callable=AsyncMock,
            ) as mock_scrape,
            patch(
                "app.services.langgraph.agents.lead_research.scrape_company_news",
                new_callable=AsyncMock,
            ) as mock_news,
        ):
            mock_apollo.return_value = None  # No contact data
            mock_clearbit.return_value = {"employees": 50}  # Small company
            mock_scrape.return_value = None
            mock_news.return_value = []

            result = await agent.run(sample_lead)

        # Should identify risk factors
        assert "risk_factors" in result
