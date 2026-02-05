"""Tests for EpiphanToolKit.

Tests the centralized tool registry pattern and StructuredTool integration.
"""

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.tools import StructuredTool, ToolException

from app.services.langgraph.tools.toolkit import (
    ApolloEnrichmentInput,
    CompanyNewsInput,
    EpiphanToolKit,
    WebScraperInput,
    _enrich_from_apollo,
    _scrape_company_news,
    _scrape_company_website,
)


class TestInputSchemas:
    """Tests for Pydantic input schemas."""

    def test_apollo_enrichment_input_defaults(self) -> None:
        """Test ApolloEnrichmentInput has correct defaults."""
        input_model = ApolloEnrichmentInput(email="test@example.com")
        assert input_model.email == "test@example.com"
        assert input_model.reveal_phone is True

    def test_apollo_enrichment_input_phone_override(self) -> None:
        """Test ApolloEnrichmentInput can disable phone reveal."""
        input_model = ApolloEnrichmentInput(email="test@example.com", reveal_phone=False)
        assert input_model.reveal_phone is False

    def test_web_scraper_input(self) -> None:
        """Test WebScraperInput validation."""
        input_model = WebScraperInput(domain="company.com")
        assert input_model.domain == "company.com"

    def test_company_news_input_defaults(self) -> None:
        """Test CompanyNewsInput has correct defaults."""
        input_model = CompanyNewsInput(domain="company.com")
        assert input_model.max_articles == 5

    def test_company_news_input_custom_max(self) -> None:
        """Test CompanyNewsInput accepts custom max_articles."""
        input_model = CompanyNewsInput(domain="company.com", max_articles=10)
        assert input_model.max_articles == 10


class TestToolImplementations:
    """Tests for underlying tool functions."""

    @pytest.mark.asyncio
    async def test_enrich_from_apollo_success(self) -> None:
        """Test Apollo enrichment returns data."""
        mock_data = {
            "first_name": "John",
            "last_name": "Doe",
            "title": "VP of Engineering",
        }

        with patch(
            "app.services.langgraph.tools.toolkit.apollo_client.enrich_contact",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            result = await _enrich_from_apollo("john@company.com")
            assert result == mock_data
            assert result["title"] == "VP of Engineering"

    @pytest.mark.asyncio
    async def test_enrich_from_apollo_not_found(self) -> None:
        """Test Apollo enrichment raises ToolException when not found."""
        with patch(
            "app.services.langgraph.tools.toolkit.apollo_client.enrich_contact",
            new_callable=AsyncMock,
            return_value=None,
        ), pytest.raises(ToolException, match="No data found"):
            await _enrich_from_apollo("unknown@company.com")

    @pytest.mark.asyncio
    async def test_enrich_from_apollo_api_error(self) -> None:
        """Test Apollo enrichment raises ToolException on API error."""
        with patch(
            "app.services.langgraph.tools.toolkit.apollo_client.enrich_contact",
            new_callable=AsyncMock,
            side_effect=Exception("API rate limited"),
        ), pytest.raises(ToolException, match="Apollo enrichment failed"):
            await _enrich_from_apollo("test@company.com")

    @pytest.mark.asyncio
    async def test_scrape_company_website_success(self) -> None:
        """Test web scraping returns data."""
        mock_data = {"about_text": "We are a video company", "about_url": "https://example.com/about"}

        with patch(
            "app.services.langgraph.tools.toolkit.web_scraper.scrape_company_info",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            result = await _scrape_company_website("example.com")
            assert result["about_text"] == "We are a video company"

    @pytest.mark.asyncio
    async def test_scrape_company_website_not_found(self) -> None:
        """Test web scraping returns status when not found."""
        with patch(
            "app.services.langgraph.tools.toolkit.web_scraper.scrape_company_info",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await _scrape_company_website("unknown-domain.com")
            assert result["status"] == "not_found"
            assert result["domain"] == "unknown-domain.com"

    @pytest.mark.asyncio
    async def test_scrape_company_website_error(self) -> None:
        """Test web scraping raises ToolException on error."""
        with patch(
            "app.services.langgraph.tools.toolkit.web_scraper.scrape_company_info",
            new_callable=AsyncMock,
            side_effect=Exception("Connection timeout"),
        ), pytest.raises(ToolException, match="Web scraping failed"):
            await _scrape_company_website("error-domain.com")

    @pytest.mark.asyncio
    async def test_scrape_company_news_success(self) -> None:
        """Test news scraping returns articles."""
        mock_news = [
            {"title": "Company raises Series B", "date": "2025-01-01"},
            {"title": "New product launch", "date": "2025-01-15"},
        ]

        with patch(
            "app.services.langgraph.tools.toolkit.web_scraper.extract_news",
            new_callable=AsyncMock,
            return_value=mock_news,
        ):
            result = await _scrape_company_news("example.com", max_articles=5)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_scrape_company_news_respects_max_articles(self) -> None:
        """Test news scraping respects max_articles limit."""
        mock_news = [
            {"title": "Article 1"},
            {"title": "Article 2"},
            {"title": "Article 3"},
            {"title": "Article 4"},
            {"title": "Article 5"},
        ]

        with patch(
            "app.services.langgraph.tools.toolkit.web_scraper.extract_news",
            new_callable=AsyncMock,
            return_value=mock_news,
        ):
            result = await _scrape_company_news("example.com", max_articles=3)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_scrape_company_news_tries_multiple_paths(self) -> None:
        """Test news scraping tries multiple paths until finding news."""
        call_count = 0

        async def mock_extract_news(url: str) -> list:
            nonlocal call_count
            call_count += 1
            # First few paths fail, then succeed
            if "/newsroom" in url:
                return [{"title": "Found in newsroom"}]
            return []

        with patch(
            "app.services.langgraph.tools.toolkit.web_scraper.extract_news",
            side_effect=mock_extract_news,
        ):
            result = await _scrape_company_news("example.com")
            assert len(result) == 1
            assert result[0]["title"] == "Found in newsroom"

    @pytest.mark.asyncio
    async def test_scrape_company_news_returns_empty_when_none_found(self) -> None:
        """Test news scraping returns empty list when no news found."""
        with patch(
            "app.services.langgraph.tools.toolkit.web_scraper.extract_news",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await _scrape_company_news("no-news.com")
            assert result == []


class TestEpiphanToolKit:
    """Tests for the centralized tool registry."""

    def test_get_enrichment_tools_returns_structured_tools(self) -> None:
        """Test get_enrichment_tools returns StructuredTool instances."""
        tools = EpiphanToolKit.get_enrichment_tools()
        assert len(tools) == 2
        for tool in tools:
            assert isinstance(tool, StructuredTool)

    def test_get_enrichment_tools_has_correct_names(self) -> None:
        """Test enrichment tools have expected names."""
        tools = EpiphanToolKit.get_enrichment_tools()
        names = [tool.name for tool in tools]
        assert "apollo_enrichment" in names
        assert "web_scraper" in names

    def test_get_research_tools_returns_structured_tools(self) -> None:
        """Test get_research_tools returns StructuredTool instances."""
        tools = EpiphanToolKit.get_research_tools()
        assert len(tools) == 1
        assert isinstance(tools[0], StructuredTool)

    def test_get_research_tools_has_correct_names(self) -> None:
        """Test research tools have expected names."""
        tools = EpiphanToolKit.get_research_tools()
        names = [tool.name for tool in tools]
        assert "company_news" in names

    def test_get_all_tools_combines_all_categories(self) -> None:
        """Test get_all_tools returns tools from all categories."""
        all_tools = EpiphanToolKit.get_all_tools()
        enrichment_tools = EpiphanToolKit.get_enrichment_tools()
        research_tools = EpiphanToolKit.get_research_tools()

        assert len(all_tools) == len(enrichment_tools) + len(research_tools)

    def test_get_tool_names_returns_all_names(self) -> None:
        """Test get_tool_names returns all tool names."""
        names = EpiphanToolKit.get_tool_names()
        assert "apollo_enrichment" in names
        assert "web_scraper" in names
        assert "company_news" in names

    def test_tools_have_descriptions(self) -> None:
        """Test all tools have meaningful descriptions."""
        tools = EpiphanToolKit.get_all_tools()
        for tool in tools:
            assert tool.description is not None
            assert len(tool.description) > 20  # Non-trivial description

    def test_tools_have_args_schemas(self) -> None:
        """Test all tools have Pydantic args schemas."""
        tools = EpiphanToolKit.get_all_tools()
        for tool in tools:
            assert tool.args_schema is not None

    def test_apollo_tool_schema_fields(self) -> None:
        """Test Apollo tool has correct schema fields."""
        tools = EpiphanToolKit.get_enrichment_tools()
        apollo_tool = next(t for t in tools if t.name == "apollo_enrichment")

        schema = apollo_tool.args_schema
        assert schema is not None
        fields = schema.model_fields
        assert "email" in fields
        assert "reveal_phone" in fields

    def test_web_scraper_tool_schema_fields(self) -> None:
        """Test web scraper tool has correct schema fields."""
        tools = EpiphanToolKit.get_enrichment_tools()
        scraper_tool = next(t for t in tools if t.name == "web_scraper")

        schema = scraper_tool.args_schema
        assert schema is not None
        fields = schema.model_fields
        assert "domain" in fields

    def test_news_tool_schema_fields(self) -> None:
        """Test news tool has correct schema fields."""
        tools = EpiphanToolKit.get_research_tools()
        news_tool = next(t for t in tools if t.name == "company_news")

        schema = news_tool.args_schema
        assert schema is not None
        fields = schema.model_fields
        assert "domain" in fields
        assert "max_articles" in fields


class TestToolKitIntegration:
    """Integration tests for using tools through the toolkit."""

    @pytest.mark.asyncio
    async def test_apollo_tool_invocation(self) -> None:
        """Test invoking Apollo tool through StructuredTool interface."""
        mock_data = {"first_name": "Test", "title": "CEO"}

        with patch(
            "app.services.langgraph.tools.toolkit.apollo_client.enrich_contact",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            tools = EpiphanToolKit.get_enrichment_tools()
            apollo_tool = next(t for t in tools if t.name == "apollo_enrichment")

            # Invoke through the tool interface
            result = await apollo_tool.ainvoke({"email": "test@company.com"})
            assert result == mock_data

    @pytest.mark.asyncio
    async def test_web_scraper_tool_invocation(self) -> None:
        """Test invoking web scraper tool through StructuredTool interface."""
        mock_data = {"about_text": "Test company info"}

        with patch(
            "app.services.langgraph.tools.toolkit.web_scraper.scrape_company_info",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            tools = EpiphanToolKit.get_enrichment_tools()
            scraper_tool = next(t for t in tools if t.name == "web_scraper")

            result = await scraper_tool.ainvoke({"domain": "test.com"})
            assert result == mock_data

    @pytest.mark.asyncio
    async def test_news_tool_invocation(self) -> None:
        """Test invoking news tool through StructuredTool interface."""
        mock_news = [{"title": "News article"}]

        with patch(
            "app.services.langgraph.tools.toolkit.web_scraper.extract_news",
            new_callable=AsyncMock,
            return_value=mock_news,
        ):
            tools = EpiphanToolKit.get_research_tools()
            news_tool = next(t for t in tools if t.name == "company_news")

            result = await news_tool.ainvoke({"domain": "test.com", "max_articles": 5})
            assert result == mock_news
