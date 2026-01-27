"""Clearbit enrichment client for company and person data.

Provides company firmographics, tech stack detection, and person
enrichment via the Clearbit API.
"""

from typing import Any

import httpx

from app.core.config import settings


class ClearbitAPIError(Exception):
    """Error from Clearbit API."""

    pass


class ClearbitClient:
    """
    Client for Clearbit enrichment API.

    Provides:
    - Company enrichment by domain (firmographics, tech stack)
    - Person enrichment by email
    """

    COMPANY_URL = "https://company.clearbit.com/v2/companies/find"
    PERSON_URL = "https://person.clearbit.com/v2/combined/find"

    def __init__(self, api_key: str | None = None):
        """Initialize client with API key."""
        self.api_key = api_key or settings.clearbit_api_key
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def _make_request(
        self,
        url: str,
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Make authenticated request to Clearbit API."""
        try:
            response = await self.client.get(url, params=params)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise ClearbitAPIError("Rate limit exceeded") from e
            elif e.response.status_code == 401:
                raise ClearbitAPIError("Invalid API key") from e
            else:
                raise ClearbitAPIError(f"API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise ClearbitAPIError(f"Request failed: {e}") from e

    async def enrich_company(self, domain: str) -> dict[str, Any] | None:
        """
        Enrich a company by domain.

        Args:
            domain: Company domain (e.g., 'company.com')

        Returns:
            Enriched company data or None if not found
        """
        response = await self._make_request(
            self.COMPANY_URL,
            {"domain": domain},
        )

        if not response:
            return None

        # Extract nested data into flat structure
        category = response.get("category", {})
        metrics = response.get("metrics", {})
        geo = response.get("geo", {})

        return {
            "name": response.get("name"),
            "legal_name": response.get("legalName"),
            "domain": response.get("domain"),
            "description": response.get("description"),
            "industry": category.get("industry"),
            "sector": category.get("sector"),
            "industry_group": category.get("industryGroup"),
            "employees": metrics.get("employees"),
            "employees_range": metrics.get("employeesRange"),
            "annual_revenue": metrics.get("annualRevenue"),
            "city": geo.get("city"),
            "state": geo.get("state"),
            "country": geo.get("country"),
            "linkedin_handle": (response.get("linkedin") or {}).get("handle"),
            "twitter_handle": (response.get("twitter") or {}).get("handle"),
            "tech_stack": response.get("tech", []),
        }

    async def enrich_person(self, email: str) -> dict[str, Any] | None:
        """
        Enrich a person by email address.

        Args:
            email: Person's email address

        Returns:
            Enriched person data or None if not found
        """
        response = await self._make_request(
            self.PERSON_URL,
            {"email": email},
        )

        if not response:
            return None

        person = response.get("person", {})
        if not person:
            return None

        name = person.get("name", {})
        employment = person.get("employment", {})
        company = response.get("company", {})

        return {
            "first_name": name.get("givenName"),
            "last_name": name.get("familyName"),
            "full_name": name.get("fullName"),
            "title": employment.get("title"),
            "seniority": employment.get("seniority"),
            "company_name": employment.get("name") or company.get("name"),
            "company_domain": company.get("domain"),
            "linkedin_handle": (person.get("linkedin") or {}).get("handle"),
        }

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
clearbit_client = ClearbitClient()
