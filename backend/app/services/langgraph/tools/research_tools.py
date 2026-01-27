"""Tools for Lead Research Agent.

Provides functions to enrich lead data from multiple sources:
- Apollo.io (contact enrichment)
- Clearbit (company firmographics)
- Web scraping (company website, news)
"""

from typing import Any

from app.services.enrichment.apollo import apollo_client
from app.services.enrichment.clearbit import clearbit_client
from app.services.enrichment.scraper import web_scraper


async def enrich_from_apollo(email: str) -> dict[str, Any] | None:
    """
    Enrich a contact using Apollo.io.

    Args:
        email: Contact email address

    Returns:
        Enriched contact data or None if not found
    """
    return await apollo_client.enrich_contact(email)


async def enrich_from_clearbit(domain: str) -> dict[str, Any] | None:
    """
    Enrich a company using Clearbit.

    Args:
        domain: Company domain (e.g., 'company.com')

    Returns:
        Enriched company data or None if not found
    """
    return await clearbit_client.enrich_company(domain)


async def scrape_company_website(domain: str) -> dict[str, Any] | None:
    """
    Scrape company website for about/overview info.

    Args:
        domain: Company domain

    Returns:
        Dict with about_text or None if not found
    """
    return await web_scraper.scrape_company_info(domain)


async def scrape_company_news(domain: str) -> list[dict[str, Any]]:
    """
    Scrape company news/press releases.

    Args:
        domain: Company domain

    Returns:
        List of news items
    """
    # Try common news/press paths
    news_paths = ["/news", "/press", "/newsroom", "/press-releases", "/blog"]

    for path in news_paths:
        url = f"https://{domain}{path}"
        try:
            news = await web_scraper.extract_news(url)
            if news:
                return news
        except Exception:
            continue

    return []


def get_company_domain(email: str) -> str:
    """
    Extract company domain from email address.

    Args:
        email: Email address

    Returns:
        Domain portion of email
    """
    if "@" not in email:
        return email

    return email.split("@")[1].lower()


def combine_enrichment_data(
    apollo_data: dict[str, Any] | None,
    clearbit_data: dict[str, Any] | None,
    scraped_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Combine enrichment data from multiple sources.

    Prioritizes Apollo for contact info, Clearbit for company,
    and scraped for context.

    Args:
        apollo_data: Data from Apollo.io
        clearbit_data: Data from Clearbit
        scraped_data: Data from web scraping

    Returns:
        Merged enrichment data
    """
    result: dict[str, Any] = {}

    # Contact info from Apollo (priority)
    if apollo_data:
        for key in ["first_name", "last_name", "title", "linkedin_url", "seniority"]:
            if apollo_data.get(key):
                result[key] = apollo_data[key]

    # Company info from Clearbit (priority)
    if clearbit_data:
        for key in [
            "industry",
            "sector",
            "employees",
            "employees_range",
            "city",
            "state",
            "country",
            "tech_stack",
            "linkedin_handle",
        ]:
            if clearbit_data.get(key):
                result[key] = clearbit_data[key]

    # Context from scraping
    if scraped_data:
        if scraped_data.get("about_text"):
            result["about_text"] = scraped_data["about_text"]
        if scraped_data.get("about_url"):
            result["about_url"] = scraped_data["about_url"]

    return result
