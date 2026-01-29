"""Apollo.io enrichment client for contact and company data.

Provides contact enrichment, company lookup, and people search
via the Apollo.io API.

Includes tiered enrichment strategy:
- Phase 1 (1 credit): Company verification + persona identification
- Phase 2 (8 credits): Phone enrichment ONLY for ATL decision-makers

Features:
- Rate limit tracking with exponential backoff
- Credit usage auditing
- ATL decision-maker detection

PHONES ARE GOLD - but only for people Tim will actually call.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.services.scoring.atl_detector import ATLMatch, is_atl_decision_maker

logger = logging.getLogger(__name__)


class ApolloAPIError(Exception):
    """Error from Apollo API."""

    pass


@dataclass
class TieredEnrichmentResult:
    """Result of tiered enrichment strategy.

    Tracks credit usage for ROI analysis:
    - Phase 1 only (non-ATL): 1 credit
    - Phase 1 + Phase 2 (ATL): 9 credits (1 + 8)

    PHONES ARE GOLD - but only for ATL decision-makers who Tim will call.
    """

    found: bool
    """Whether the contact was found in Apollo."""

    data: dict[str, Any] | None = None
    """Enriched contact data (includes phones only if ATL)."""

    is_atl: bool = False
    """Whether this contact is an ATL decision-maker."""

    atl_match: ATLMatch | None = None
    """Full ATL detection result with confidence and reason."""

    persona_match: str | None = None
    """Matched persona ID if ATL matched a specific persona."""

    phone_revealed: bool = False
    """Whether phone enrichment was performed (8 credits)."""

    credits_used: int = 0
    """Total Apollo credits consumed (1 for basic, 9 for basic+phone)."""

    error: str | None = None
    """Error message if enrichment failed."""

    rate_limit_hit: bool = False
    """Whether a rate limit was encountered during enrichment."""


class ApolloClient:
    """
    Client for Apollo.io enrichment API.

    Provides:
    - Contact enrichment by email
    - Company enrichment by domain
    - People search by criteria
    - Rate limit tracking and exponential backoff

    Rate Limits (Apollo standard):
    - 50 requests/minute for most plans
    - Phone reveals may have separate limits
    - Rate limit errors return 429 status
    """

    BASE_URL = "https://api.apollo.io/v1"

    # Rate limit configuration
    RATE_LIMIT_REQUESTS_PER_MINUTE = 50
    MAX_RETRIES = 3
    BASE_BACKOFF_SECONDS = 1.0

    def __init__(self, api_key: str | None = None):
        """Initialize client with API key."""
        self.api_key = api_key or settings.apollo_api_key
        self._client: httpx.AsyncClient | None = None

        # Rate limit tracking
        self._requests_this_minute = 0
        self._minute_started: float | None = None
        self._consecutive_rate_limits = 0
        self._total_rate_limits_today = 0

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

    def _track_request(self) -> None:
        """Track request for rate limiting, resetting counter each minute."""
        now = time.time()
        if self._minute_started is None or (now - self._minute_started) >= 60:
            self._requests_this_minute = 0
            self._minute_started = now
        self._requests_this_minute += 1

    def _get_backoff_seconds(self) -> float:
        """Calculate exponential backoff based on consecutive rate limits."""
        if self._consecutive_rate_limits == 0:
            return 0
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 32s
        return min(32, self.BASE_BACKOFF_SECONDS * (2 ** (self._consecutive_rate_limits - 1)))

    def get_rate_limit_status(self) -> dict[str, Any]:
        """Get current rate limit status for monitoring.

        Useful for dashboards and alerting.
        """
        return {
            "requests_this_minute": self._requests_this_minute,
            "consecutive_rate_limits": self._consecutive_rate_limits,
            "total_rate_limits_today": self._total_rate_limits_today,
            "current_backoff_seconds": self._get_backoff_seconds(),
            "approaching_limit": self._requests_this_minute >= (self.RATE_LIMIT_REQUESTS_PER_MINUTE - 10),
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated request to Apollo API with rate limit handling.

        Features:
        - Automatic retry with exponential backoff on rate limits
        - Rate limit tracking for monitoring
        - Proactive pause when approaching limits
        """
        payload = data or {}
        payload["api_key"] = self.api_key

        # Apply backoff if we've hit rate limits recently
        backoff = self._get_backoff_seconds()
        if backoff > 0:
            logger.warning(
                f"Apollo rate limit backoff: waiting {backoff}s "
                f"(consecutive limits: {self._consecutive_rate_limits})"
            )
            await asyncio.sleep(backoff)

        # Track this request
        self._track_request()

        # Warn if approaching rate limit
        if self._requests_this_minute >= (self.RATE_LIMIT_REQUESTS_PER_MINUTE - 10):
            logger.warning(
                f"Approaching Apollo rate limit: {self._requests_this_minute}/{self.RATE_LIMIT_REQUESTS_PER_MINUTE} requests this minute"
            )

        for attempt in range(self.MAX_RETRIES):
            try:
                if method == "GET":
                    response = await self.client.get(endpoint, params=payload)
                else:
                    response = await self.client.post(endpoint, json=payload)

                response.raise_for_status()

                # Success - reset consecutive rate limit counter
                self._consecutive_rate_limits = 0
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limit hit
                    self._consecutive_rate_limits += 1
                    self._total_rate_limits_today += 1

                    if attempt < self.MAX_RETRIES - 1:
                        backoff = self._get_backoff_seconds()
                        logger.warning(
                            f"Apollo rate limit hit, attempt {attempt + 1}/{self.MAX_RETRIES}, "
                            f"backing off {backoff}s"
                        )
                        await asyncio.sleep(backoff)
                        continue

                    raise ApolloAPIError(
                        f"Rate limit exceeded after {self.MAX_RETRIES} retries"
                    ) from e

                elif e.response.status_code == 401:
                    raise ApolloAPIError("Invalid API key") from e
                else:
                    raise ApolloAPIError(f"API error: {e.response.status_code}") from e

            except httpx.RequestError as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Request error, attempt {attempt + 1}/{self.MAX_RETRIES}: {e}")
                    await asyncio.sleep(1)
                    continue
                raise ApolloAPIError(f"Request failed: {e}") from e

        # Should not reach here, but just in case
        raise ApolloAPIError("Max retries exceeded")

    async def enrich_contact(
        self,
        email: str,
        reveal_phone: bool = True,
        webhook_url: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Enrich a contact by email address.

        PHONES ARE GOLD! Phone numbers require reveal_phone_number=true.
        This costs 8 credits (vs 1 for email-only) but is essential for BDR outreach.
        More phones = More dials = More conversations = More deals.

        Args:
            email: Contact email address
            reveal_phone: Request phone number reveal (8 credits, ALWAYS use for qualified leads)
            webhook_url: Optional URL for async phone delivery (Apollo may deliver phones async)

        Returns:
            Enriched contact data with phone numbers or None if not found
        """
        payload: dict[str, Any] = {
            "email": email,
            "reveal_personal_emails": False,
            "reveal_phone_number": reveal_phone,  # CRITICAL: Without this, phones are EMPTY!
        }

        # Apollo may deliver phones async via webhook if provided
        if webhook_url:
            payload["webhook_url"] = webhook_url

        response = await self._make_request("POST", "/people/match", payload)

        person = response.get("person")
        if not person:
            return None

        # Extract phone numbers (Apollo returns array of phone objects)
        # PHONES ARE GOLD - prioritize extraction!
        phone_numbers = person.get("phone_numbers", [])

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
            # PHONE NUMBERS - THE GOLD!
            "phone_numbers": phone_numbers,  # Array: [{sanitized_number, type}, ...]
            "direct_phone": self._extract_phone(phone_numbers, "work_direct"),
            "mobile_phone": self._extract_phone(phone_numbers, "mobile"),
            "work_phone": self._extract_phone(phone_numbers, "work"),
        }

    def _extract_phone(self, phones: list[dict[str, Any]], phone_type: str) -> str | None:
        """
        Extract specific phone type from Apollo phone array.

        PHONES ARE GOLD! This helper prioritizes extraction accuracy.

        Args:
            phones: List of phone objects from Apollo
            phone_type: Type to extract ("work_direct", "mobile", "work")

        Returns:
            Sanitized phone number or None if not found
        """
        for phone in phones:
            ptype = (phone.get("type") or "").lower()
            # Check if this phone matches the requested type
            is_match = (
                (phone_type == "work_direct" and "direct" in ptype)
                or (phone_type == "mobile" and ptype == "mobile")
                or (phone_type == "work" and "work" in ptype and "direct" not in ptype and "hq" not in ptype)
            )
            if is_match:
                return phone.get("sanitized_number") or phone.get("number")
        return None

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

    async def tiered_enrich(
        self,
        email: str,
        title: str | None = None,
        _company: str | None = None,  # Reserved for future company-based filtering
        _industry: str | None = None,  # Reserved for future industry-based filtering
        webhook_url: str | None = None,
    ) -> TieredEnrichmentResult:
        """
        Smart two-phase enrichment that saves Apollo credits.

        The matchmaker strategy: identify ATL decision-makers FAST so Tim can
        call them before distributors/integrators reach them.

        Phase 1 (1 credit): Get company + title verification (reveal_phone=False)
        Phase 2 (8 credits): If ATL, reveal phone numbers (reveal_phone=True)

        Credit Economics:
        - Non-ATL lead: 1 credit (saved 7 credits!)
        - ATL lead: 9 credits (1 + 8)
        - Estimated 67% savings on typical batches (~15-25% ATL rate)

        Args:
            email: Contact email address.
            title: Known title from Harvester (used if Apollo returns None).
            _company: Reserved for future company-based filtering.
            _industry: Reserved for future industry-based filtering.
            webhook_url: Optional URL for async phone delivery.

        Returns:
            TieredEnrichmentResult with contact data, ATL status, and credits.
        """
        # Phase 1: Basic enrichment without phone reveal (1 credit)
        rate_limit_hit = False
        try:
            basic_data = await self.enrich_contact(
                email=email,
                reveal_phone=False,  # Save 7 credits for Phase 1
                webhook_url=None,  # No webhook needed for basic
            )
        except ApolloAPIError as e:
            error_msg = str(e)
            rate_limit_hit = "rate limit" in error_msg.lower()
            return TieredEnrichmentResult(
                found=False,
                credits_used=1,  # Credit still consumed on API error
                error=error_msg,
                rate_limit_hit=rate_limit_hit,
            )

        if not basic_data:
            return TieredEnrichmentResult(
                found=False,
                credits_used=1,
                error="Contact not found in Apollo",
            )

        # Use Apollo's title if available, fall back to provided title
        enriched_title = basic_data.get("title") or title
        enriched_seniority = basic_data.get("seniority")

        # Check if ATL decision-maker
        atl_match = is_atl_decision_maker(
            title=enriched_title,
            seniority=enriched_seniority,
        )

        if not atl_match.is_atl:
            # NOT ATL - return basic data, save 7 credits!
            # Tim won't call this person anyway, so no need for phone
            return TieredEnrichmentResult(
                found=True,
                data=basic_data,
                is_atl=False,
                atl_match=atl_match,
                persona_match=None,
                phone_revealed=False,
                credits_used=1,  # Saved 7 credits!
            )

        # Phase 2: ATL confirmed - reveal phones (8 more credits)
        # PHONES ARE GOLD for decision-makers Tim will actually call!
        try:
            full_data = await self.enrich_contact(
                email=email,
                reveal_phone=True,  # 8 credits for phone reveal
                webhook_url=webhook_url,  # Pass webhook for async delivery
            )
        except ApolloAPIError as e:
            # Phone reveal failed, but we still have basic data
            error_msg = str(e)
            rate_limit_hit = "rate limit" in error_msg.lower()
            return TieredEnrichmentResult(
                found=True,
                data=basic_data,  # Return basic data we got
                is_atl=True,
                atl_match=atl_match,
                persona_match=atl_match.persona_id,
                phone_revealed=False,  # Phone reveal failed
                credits_used=1,  # Only charged for Phase 1
                error=f"Phone reveal failed: {e}",
                rate_limit_hit=rate_limit_hit,
            )

        return TieredEnrichmentResult(
            found=True,
            data=full_data,
            is_atl=True,
            atl_match=atl_match,
            persona_match=atl_match.persona_id,
            phone_revealed=True,
            credits_used=9,  # 1 (basic) + 8 (phone reveal)
        )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
apollo_client = ApolloClient()
