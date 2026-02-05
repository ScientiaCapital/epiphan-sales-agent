"""Centralized Tool Registry for LangGraph Agents.

This module provides the EpiphanToolKit class that wraps all agent tools
using LangChain's StructuredTool pattern for consistent input/output validation
and better LLM integration.

Based on patterns from:
- LangChain ToolKit documentation
- Anthropic's context engineering best practices
"""

from typing import Any

from langchain_core.tools import StructuredTool, ToolException
from pydantic import BaseModel, Field

from app.services.enrichment.apollo import apollo_client
from app.services.enrichment.scraper import web_scraper

# =============================================================================
# Input Schemas for Tools
# =============================================================================


class ApolloEnrichmentInput(BaseModel):
    """Input schema for Apollo enrichment tool."""

    email: str = Field(..., description="Contact email address to enrich")
    reveal_phone: bool = Field(
        default=True,
        description="Whether to reveal phone numbers (costs 8 credits per phone)",
    )


class WebScraperInput(BaseModel):
    """Input schema for web scraper tool."""

    domain: str = Field(..., description="Company domain to scrape (e.g., 'company.com')")


class CompanyNewsInput(BaseModel):
    """Input schema for company news scraper."""

    domain: str = Field(..., description="Company domain to scrape news from")
    max_articles: int = Field(default=5, description="Maximum number of articles to return")


class QualificationInput(BaseModel):
    """Input schema for lead qualification tool."""

    title: str = Field(..., description="Contact's job title")
    seniority: str | None = Field(default=None, description="Contact's seniority level")
    industry: str | None = Field(default=None, description="Company industry")
    employee_count: int | None = Field(default=None, description="Company employee count")


# =============================================================================
# Tool Implementation Functions
# =============================================================================


async def _enrich_from_apollo(email: str, reveal_phone: bool = True) -> dict[str, Any]:
    """
    Enrich a contact using Apollo.io.

    Args:
        email: Contact email address
        reveal_phone: Whether to reveal phone numbers

    Returns:
        Enriched contact data

    Raises:
        ToolException: If enrichment fails
    """
    try:
        result = await apollo_client.enrich_contact(email, reveal_phone=reveal_phone)
        if result is None:
            raise ToolException(f"No data found for email: {email}")
        return result
    except Exception as e:
        raise ToolException(f"Apollo enrichment failed: {e}") from e


async def _scrape_company_website(domain: str) -> dict[str, Any]:
    """
    Scrape company website for about/overview info.

    Args:
        domain: Company domain

    Returns:
        Dict with about_text and other scraped info

    Raises:
        ToolException: If scraping fails
    """
    try:
        result = await web_scraper.scrape_company_info(domain)
        if result is None:
            return {"domain": domain, "about_text": None, "status": "not_found"}
        return result
    except Exception as e:
        raise ToolException(f"Web scraping failed for {domain}: {e}") from e


async def _scrape_company_news(domain: str, max_articles: int = 5) -> list[dict[str, Any]]:
    """
    Scrape company news/press releases.

    Args:
        domain: Company domain
        max_articles: Maximum articles to return

    Returns:
        List of news items
    """
    news_paths = ["/news", "/press", "/newsroom", "/press-releases", "/blog"]

    for path in news_paths:
        url = f"https://{domain}{path}"
        try:
            news = await web_scraper.extract_news(url)
            if news:
                return news[:max_articles]
        except Exception:
            continue

    return []


# =============================================================================
# EpiphanToolKit - Centralized Tool Registry
# =============================================================================


class EpiphanToolKit:
    """
    Centralized tool registry for all LangGraph agents.

    Provides organized access to tools by category:
    - Enrichment tools: Apollo, web scraping
    - Research tools: News scraping, domain extraction
    - Qualification tools: ICP scoring helpers

    Usage:
        toolkit = EpiphanToolKit()
        enrichment_tools = toolkit.get_enrichment_tools()
        all_tools = toolkit.get_all_tools()
    """

    @staticmethod
    def get_enrichment_tools() -> list[StructuredTool]:
        """
        Get tools for lead/contact enrichment.

        Returns:
            List of StructuredTools for enrichment operations
        """
        return [
            StructuredTool.from_function(
                coroutine=_enrich_from_apollo,
                name="apollo_enrichment",
                description=(
                    "Enrich a contact using Apollo.io. Returns name, title, seniority, "
                    "company info, and optionally phone numbers. Use this to get verified "
                    "business data for a lead."
                ),
                args_schema=ApolloEnrichmentInput,
            ),
            StructuredTool.from_function(
                coroutine=_scrape_company_website,
                name="web_scraper",
                description=(
                    "Scrape a company's website for their about page and overview info. "
                    "Returns company description and context. Use when you need to understand "
                    "what the company does beyond basic Apollo data."
                ),
                args_schema=WebScraperInput,
            ),
        ]

    @staticmethod
    def get_research_tools() -> list[StructuredTool]:
        """
        Get tools for lead research.

        Returns:
            List of StructuredTools for research operations
        """
        return [
            StructuredTool.from_function(
                coroutine=_scrape_company_news,
                name="company_news",
                description=(
                    "Scrape recent news and press releases from a company's website. "
                    "Returns article titles, dates, and summaries. Use this to find "
                    "talking points and recent company developments."
                ),
                args_schema=CompanyNewsInput,
            ),
        ]

    @classmethod
    def get_all_tools(cls) -> list[StructuredTool]:
        """
        Get all available tools.

        Returns:
            Combined list of all StructuredTools
        """
        return cls.get_enrichment_tools() + cls.get_research_tools()

    @staticmethod
    def get_tool_names() -> list[str]:
        """
        Get names of all available tools.

        Returns:
            List of tool names
        """
        return ["apollo_enrichment", "web_scraper", "company_news"]
