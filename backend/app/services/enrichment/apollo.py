"""Apollo.io enrichment client for contact and company data.

Provides contact enrichment, company lookup, and people search
via the Apollo.io API.
"""

from typing import Any

import httpx

from app.core.config import settings


class ApolloAPIError(Exception):
    """Error from Apollo API."""

    pass


class ApolloClient:
    """
    Client for Apollo.io enrichment API.

    Provides:
    - Contact enrichment by email
    - Company enrichment by domain
    - People search by criteria
    """

    BASE_URL = "https://api.apollo.io/v1"

    def __init__(self, api_key: str | None = None):
        """Initialize client with API key."""
        self.api_key = api_key or settings.apollo_api_key
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                },
                timeout=30.0,
            )
        return self._client

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated request to Apollo API."""
        payload = data or {}
        payload["api_key"] = self.api_key

        try:
            if method == "GET":
                response = await self.client.get(endpoint, params=payload)
            else:
                response = await self.client.post(endpoint, json=payload)

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise ApolloAPIError("Rate limit exceeded") from e
            elif e.response.status_code == 401:
                raise ApolloAPIError("Invalid API key") from e
            else:
                raise ApolloAPIError(f"API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise ApolloAPIError(f"Request failed: {e}") from e

    async def enrich_contact(self, email: str) -> dict[str, Any] | None:
        """
        Enrich a contact by email address.

        Args:
            email: Contact email address

        Returns:
            Enriched contact data or None if not found
        """
        response = await self._make_request(
            "POST",
            "/people/match",
            {"email": email, "reveal_personal_emails": False},
        )

        person = response.get("person")
        if not person:
            return None

        return {
            "first_name": person.get("first_name"),
            "last_name": person.get("last_name"),
            "title": person.get("title"),
            "headline": person.get("headline"),
            "linkedin_url": person.get("linkedin_url"),
            "photo_url": person.get("photo_url"),
            "email": person.get("email"),
            "organization": person.get("organization"),
            "seniority": person.get("seniority"),
            "departments": person.get("departments"),
        }

    async def enrich_company(self, domain: str) -> dict[str, Any] | None:
        """
        Enrich a company by domain.

        Args:
            domain: Company domain (e.g., 'company.com')

        Returns:
            Enriched company data or None if not found
        """
        response = await self._make_request(
            "POST",
            "/organizations/enrich",
            {"domain": domain},
        )

        org = response.get("organization")
        if not org:
            return None

        return {
            "name": org.get("name"),
            "website_url": org.get("website_url"),
            "industry": org.get("industry"),
            "estimated_num_employees": org.get("estimated_num_employees"),
            "founded_year": org.get("founded_year"),
            "linkedin_url": org.get("linkedin_url"),
            "description": org.get("short_description"),
            "technologies": org.get("technologies", []),
            "keywords": org.get("keywords", []),
            "city": org.get("city"),
            "state": org.get("state"),
            "country": org.get("country"),
        }

    async def search_people(
        self,
        titles: list[str] | None = None,
        industries: list[str] | None = None,
        company_domains: list[str] | None = None,
        seniorities: list[str] | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> list[dict[str, Any]]:
        """
        Search for people by criteria.

        Args:
            titles: List of job titles to search
            industries: List of industries
            company_domains: List of company domains
            seniorities: List of seniority levels
            page: Page number
            per_page: Results per page

        Returns:
            List of matching people
        """
        data: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
        }

        if titles:
            data["person_titles"] = titles
        if industries:
            data["organization_industry_tag_ids"] = industries
        if company_domains:
            data["q_organization_domains"] = "\n".join(company_domains)
        if seniorities:
            data["person_seniorities"] = seniorities

        response = await self._make_request("POST", "/mixed_people/search", data)

        people = response.get("people", [])
        return [
            {
                "first_name": p.get("first_name"),
                "last_name": p.get("last_name"),
                "title": p.get("title"),
                "email": p.get("email"),
                "linkedin_url": p.get("linkedin_url"),
                "organization_name": p.get("organization", {}).get("name"),
            }
            for p in people
        ]

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
apollo_client = ApolloClient()
