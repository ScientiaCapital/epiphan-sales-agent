"""Tools for Lead Research Agent.

Provides functions to enrich lead data from multiple sources:
- Apollo.io (contact and company enrichment)
- Web scraping (company website, news)
"""

from typing import Any

from langchain_core.tools import ToolException

from app.services.enrichment.apollo import apollo_client
from app.services.enrichment.scraper import web_scraper


async def enrich_from_apollo(email: str) -> dict[str, Any]:
    """
    Enrich a contact using Apollo.io.

    Args:
        email: Contact email address

    Returns:
        Enriched contact data

    Raises:
        ToolException: If enrichment fails or no data found
    """
    try:
        result = await apollo_client.enrich_contact(email)
        if result is None:
            raise ToolException(
                f"No Apollo data found for email: {email}",
            )
        return result
    except ToolException:
        raise
    except Exception as e:
        raise ToolException(
            f"Apollo enrichment failed for {email}: {e}",
        ) from e


async def scrape_company_website(domain: str) -> dict[str, Any]:
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
            # Return empty result instead of raising - scraping often fails gracefully
            return {"domain": domain, "about_text": None, "status": "not_found"}
        return result
    except Exception as e:
        raise ToolException(
            f"Web scraping failed for {domain}: {e}",
        ) from e


async def scrape_company_news(domain: str) -> list[dict[str, Any]]:
    """
    Scrape company news/press releases.

    Args:
        domain: Company domain

    Returns:
        List of news items (empty list if none found)

    Raises:
        ToolException: If all scraping attempts fail with errors
    """
    # Try common news/press paths
    news_paths = ["/news", "/press", "/newsroom", "/press-releases", "/blog"]
    errors: list[str] = []

    for path in news_paths:
        url = f"https://{domain}{path}"
        try:
            news = await web_scraper.extract_news(url)
            if news:
                return news
        except Exception as e:
            errors.append(f"{url}: {e}")
            continue

    # Return empty list if no news found (not an error condition)
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
    scraped_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Combine enrichment data from multiple sources.

    Prioritizes Apollo for contact/company info, scraped for context.

    Args:
        apollo_data: Data from Apollo.io
        scraped_data: Data from web scraping

    Returns:
        Merged enrichment data
    """
    result: dict[str, Any] = {}

    # Contact and company info from Apollo
    if apollo_data:
        for key in [
            "first_name",
            "last_name",
            "title",
            "linkedin_url",
            "seniority",
            "industry",
            "employees",
            "city",
            "state",
            "country",
        ]:
            if apollo_data.get(key):
                result[key] = apollo_data[key]

    # Context from scraping
    if scraped_data:
        if scraped_data.get("about_text"):
            result["about_text"] = scraped_data["about_text"]
        if scraped_data.get("about_url"):
            result["about_url"] = scraped_data["about_url"]

    return result
