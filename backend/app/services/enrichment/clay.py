"""Clay.com enrichment client — fallback enrichment via 75+ provider waterfall.

Clay doesn't have a traditional REST API. Instead:
1. We POST lead data to a Clay table webhook URL
2. Clay enriches through its provider waterfall (ZoomInfo, PDL, ContactOut, Lusha, etc.)
3. Clay POSTs results back to our webhook endpoint

Phone priority: Apollo (primary) > Harvester (secondary) > Clay (tertiary fallback)

PHONES ARE GOLD!
"""

import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClayAPIError(Exception):
    """Raised when Clay API calls fail."""


@dataclass
class ClayEnrichmentData:
    """Parsed enrichment result from Clay callback.

    Contains all data Clay can provide from its 75+ provider waterfall.
    """

    lead_id: str
    phones: list[dict[str, str]] = field(default_factory=list)
    emails: list[dict[str, str]] = field(default_factory=list)
    company_name: str | None = None
    industry: str | None = None
    employee_count: int | None = None
    revenue_range: str | None = None
    technologies: list[str] = field(default_factory=list)
    linkedin_url: str | None = None
    funding_info: dict[str, Any] | None = None


# Mapping from Clay phone type labels to our standard types
_CLAY_PHONE_TYPE_MAP: dict[str, str] = {
    "direct": "work_direct",
    "direct_dial": "work_direct",
    "work_direct": "work_direct",
    "mobile": "mobile",
    "cell": "mobile",
    "personal": "mobile",
    "work": "work",
    "office": "work",
    "company": "work_hq",
    "headquarters": "work_hq",
    "hq": "work_hq",
    "switchboard": "work_hq",
    "main": "work_hq",
}


class ClayClient:
    """Client for Clay.com webhook-based enrichment.

    Mirrors the ApolloClient pattern: singleton, httpx async, error handling.
    Clay is a FALLBACK source — only used when Apollo can't find phones.
    """

    TIMEOUT_SECONDS = 30

    def __init__(
        self,
        webhook_url: str | None = None,
        webhook_secret: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        self.webhook_url = webhook_url or settings.clay_table_webhook_url
        self.webhook_secret = webhook_secret or settings.clay_webhook_secret
        self._enabled = enabled if enabled is not None else settings.clay_enabled
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-init httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS)
        return self._client

    def is_enabled(self) -> bool:
        """Check if Clay enrichment is enabled and configured."""
        return bool(self._enabled and self.webhook_url)

    async def push_lead_to_clay(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """Push a lead to Clay's table webhook for enrichment.

        Clay will enrich the lead through its provider waterfall and POST
        the results back to our webhook endpoint.

        Args:
            lead_data: Lead fields to enrich (email, name, company, etc.)

        Returns:
            Clay's acknowledgement response

        Raises:
            ClayAPIError: If the push fails
        """
        if not self.webhook_url:
            raise ClayAPIError("CLAY_TABLE_WEBHOOK_URL not configured")

        try:
            response = await self.client.post(
                self.webhook_url,
                json=lead_data,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.TimeoutException as e:
            raise ClayAPIError(f"Clay webhook timeout: {e}") from e
        except httpx.HTTPStatusError as e:
            raise ClayAPIError(
                f"Clay API error: {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise ClayAPIError(f"Clay request failed: {e}") from e

    @staticmethod
    def parse_enrichment_result(
        payload: dict[str, Any],
    ) -> ClayEnrichmentData:
        """Parse Clay's callback payload into structured data.

        Clay payloads vary by table configuration. We extract what we can
        and gracefully handle missing fields.

        Args:
            payload: Raw JSON from Clay's webhook callback

        Returns:
            Parsed enrichment data
        """
        lead_id = payload.get("lead_id", "")

        # Parse phones — PHONES ARE GOLD!
        raw_phones = payload.get("phones", [])
        phones: list[dict[str, str]] = []
        if isinstance(raw_phones, list):
            for p in raw_phones:
                if not isinstance(p, dict):
                    continue
                number = p.get("number", "").strip()
                if not number:
                    continue
                raw_type = (p.get("type") or "").lower().strip()
                mapped_type = _CLAY_PHONE_TYPE_MAP.get(raw_type, "work")
                phones.append({
                    "number": number,
                    "type": mapped_type,
                    "provider": p.get("provider", "clay"),
                })

        # Parse emails
        raw_emails = payload.get("emails", [])
        emails: list[dict[str, str]] = []
        if isinstance(raw_emails, list):
            for e in raw_emails:
                if not isinstance(e, dict):
                    continue
                email = e.get("email", "").strip()
                if not email:
                    continue
                emails.append({
                    "email": email,
                    "type": e.get("type", "work"),
                    "provider": e.get("provider", "clay"),
                })

        # Parse technologies
        raw_tech = payload.get("technologies", [])
        technologies = (
            [str(t) for t in raw_tech if t]
            if isinstance(raw_tech, list)
            else []
        )

        # Parse employee count
        raw_employees = payload.get("employee_count")
        employee_count: int | None = None
        if raw_employees is not None:
            with contextlib.suppress(ValueError, TypeError):
                employee_count = int(raw_employees)

        return ClayEnrichmentData(
            lead_id=lead_id,
            phones=phones,
            emails=emails,
            company_name=payload.get("company_name"),
            industry=payload.get("industry"),
            employee_count=employee_count,
            revenue_range=payload.get("revenue_range"),
            technologies=technologies,
            linkedin_url=payload.get("linkedin_url"),
            funding_info=payload.get("funding_info")
            if isinstance(payload.get("funding_info"), dict)
            else None,
        )

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton (safe to import even when Clay is not configured)
try:
    clay_client = ClayClient()
except Exception:
    clay_client = ClayClient(webhook_url="", enabled=False)
