"""Enrichment Audit Logger for Apollo credit tracking and ROI analysis.

Tracks every enrichment operation for:
- Credit usage analysis and optimization
- Rate limit monitoring
- ATL detection accuracy
- HubSpot handoff preparation

PHONES ARE GOLD - but we need to track how much gold we're spending!
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EnrichmentType(str, Enum):
    """Type of enrichment operation."""

    TIERED = "tiered"  # Two-phase ATL-aware enrichment
    LEGACY = "legacy"  # Always-reveal-phones approach
    BASIC = "basic"  # No phone reveal
    COMPANY = "company"  # Company enrichment only
    CLAY = "clay"  # Clay.com fallback enrichment (75+ providers)  # Company enrichment only


class EnrichmentStatus(str, Enum):
    """Status of enrichment operation."""

    SUCCESS = "success"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    API_ERROR = "api_error"
    SKIPPED = "skipped"  # No valid email


@dataclass
class EnrichmentAuditEntry:
    """Single enrichment audit entry for persistence and analysis.

    Captures everything needed for:
    - Credit ROI analysis
    - Rate limit monitoring
    - HubSpot field population
    - ATL detection accuracy tracking
    """

    # Identifiers
    batch_id: str
    external_id: str
    email: str | None

    # Timestamps
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Enrichment details
    enrichment_type: EnrichmentType = EnrichmentType.TIERED
    status: EnrichmentStatus = EnrichmentStatus.SUCCESS

    # ATL Detection (for accuracy tracking)
    is_atl: bool = False
    atl_persona: str | None = None
    atl_confidence: float = 0.0
    atl_reason: str | None = None
    title_checked: str | None = None  # Original title for validation
    seniority_checked: str | None = None

    # Credit tracking
    credits_used: int = 0
    phase1_credits: int = 0  # Basic enrichment (1 credit)
    phase2_credits: int = 0  # Phone reveal (8 credits)

    # Phone results (PHONES ARE GOLD!)
    phone_revealed: bool = False
    direct_phone_found: bool = False
    mobile_phone_found: bool = False
    work_phone_found: bool = False
    any_phone_found: bool = False

    # Rate limit tracking
    rate_limit_hit: bool = False
    retry_count: int = 0

    # Error tracking
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database persistence or JSON logging."""
        return {
            "batch_id": self.batch_id,
            "external_id": self.external_id,
            "email": self.email,
            "timestamp": self.timestamp.isoformat(),
            "enrichment_type": self.enrichment_type.value,
            "status": self.status.value,
            "is_atl": self.is_atl,
            "atl_persona": self.atl_persona,
            "atl_confidence": self.atl_confidence,
            "atl_reason": self.atl_reason,
            "title_checked": self.title_checked,
            "seniority_checked": self.seniority_checked,
            "credits_used": self.credits_used,
            "phase1_credits": self.phase1_credits,
            "phase2_credits": self.phase2_credits,
            "phone_revealed": self.phone_revealed,
            "direct_phone_found": self.direct_phone_found,
            "mobile_phone_found": self.mobile_phone_found,
            "work_phone_found": self.work_phone_found,
            "any_phone_found": self.any_phone_found,
            "rate_limit_hit": self.rate_limit_hit,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
        }

    def to_hubspot_properties(self) -> dict[str, Any]:
        """Convert to HubSpot custom property format for CRM sync.

        These properties enable Tim's BDR workflow:
        - Filter by ATL status in HubSpot views
        - See persona match for script selection
        - Track enrichment quality
        """
        return {
            "epiphan_atl_status": "atl" if self.is_atl else "non_atl",
            "epiphan_atl_persona": self.atl_persona,
            "epiphan_atl_confidence": round(self.atl_confidence, 2),
            "epiphan_enrichment_status": self.status.value,
            "epiphan_phone_available": self.any_phone_found,
            "epiphan_direct_dial_available": self.direct_phone_found,
            "epiphan_enrichment_date": self.timestamp.isoformat(),
        }


@dataclass
class BatchAuditSummary:
    """Summary statistics for a batch of enrichment operations.

    Enables ROI analysis and optimization:
    - Credit savings vs legacy approach
    - ATL detection rate
    - Phone discovery success
    - Rate limit impact
    """

    batch_id: str
    started_at: datetime
    completed_at: datetime | None = None

    # Volume
    total_leads: int = 0
    processed: int = 0
    failed: int = 0

    # ATL metrics
    atl_leads: int = 0
    non_atl_leads: int = 0
    atl_rate: float = 0.0

    # Credit metrics
    total_credits_used: int = 0
    phase1_credits: int = 0
    phase2_credits: int = 0
    legacy_equivalent_credits: int = 0  # What it would have cost without tiered
    credits_saved: int = 0
    savings_percent: float = 0.0

    # Phone metrics (PHONES ARE GOLD!)
    phones_revealed: int = 0
    direct_phones_found: int = 0
    mobile_phones_found: int = 0
    any_phones_found: int = 0
    phone_discovery_rate: float = 0.0

    # Rate limit metrics
    rate_limit_hits: int = 0
    total_retries: int = 0

    # Error metrics
    api_errors: int = 0
    not_found: int = 0

    def update_from_entry(self, entry: EnrichmentAuditEntry) -> None:
        """Update summary with a single entry."""
        self.processed += 1

        if entry.status == EnrichmentStatus.SUCCESS:
            if entry.is_atl:
                self.atl_leads += 1
            else:
                self.non_atl_leads += 1
        elif entry.status == EnrichmentStatus.NOT_FOUND:
            self.not_found += 1
        elif entry.status == EnrichmentStatus.RATE_LIMITED:
            self.rate_limit_hits += 1
        elif entry.status == EnrichmentStatus.API_ERROR:
            self.api_errors += 1
            self.failed += 1

        # Credits
        self.total_credits_used += entry.credits_used
        self.phase1_credits += entry.phase1_credits
        self.phase2_credits += entry.phase2_credits

        # Phones
        if entry.phone_revealed:
            self.phones_revealed += 1
        if entry.direct_phone_found:
            self.direct_phones_found += 1
        if entry.mobile_phone_found:
            self.mobile_phones_found += 1
        if entry.any_phone_found:
            self.any_phones_found += 1

        # Rate limits
        if entry.rate_limit_hit:
            self.rate_limit_hits += 1
        self.total_retries += entry.retry_count

    def finalize(self) -> None:
        """Calculate derived metrics after batch completion."""
        self.completed_at = datetime.now(timezone.utc)

        # ATL rate
        if self.processed > 0:
            self.atl_rate = self.atl_leads / self.processed

        # Legacy equivalent (8 credits per lead)
        self.legacy_equivalent_credits = self.total_leads * 8
        self.credits_saved = self.legacy_equivalent_credits - self.total_credits_used
        if self.legacy_equivalent_credits > 0:
            self.savings_percent = self.credits_saved / self.legacy_equivalent_credits

        # Phone discovery rate (among ATL leads where we attempted)
        if self.phones_revealed > 0:
            self.phone_discovery_rate = self.any_phones_found / self.phones_revealed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging and persistence."""
        return {
            "batch_id": self.batch_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_leads": self.total_leads,
            "processed": self.processed,
            "failed": self.failed,
            "atl_leads": self.atl_leads,
            "non_atl_leads": self.non_atl_leads,
            "atl_rate": round(self.atl_rate, 3),
            "total_credits_used": self.total_credits_used,
            "phase1_credits": self.phase1_credits,
            "phase2_credits": self.phase2_credits,
            "legacy_equivalent_credits": self.legacy_equivalent_credits,
            "credits_saved": self.credits_saved,
            "savings_percent": round(self.savings_percent, 3),
            "phones_revealed": self.phones_revealed,
            "direct_phones_found": self.direct_phones_found,
            "mobile_phones_found": self.mobile_phones_found,
            "any_phones_found": self.any_phones_found,
            "phone_discovery_rate": round(self.phone_discovery_rate, 3),
            "rate_limit_hits": self.rate_limit_hits,
            "total_retries": self.total_retries,
            "api_errors": self.api_errors,
            "not_found": self.not_found,
        }


class EnrichmentAuditLogger:
    """
    Audit logger for enrichment operations.

    Provides structured logging and optional persistence for:
    - Credit usage tracking
    - Rate limit monitoring
    - ATL detection analytics
    - HubSpot field preparation

    Usage:
        audit = EnrichmentAuditLogger(batch_id="batch_123")
        audit.log_enrichment(entry)
        summary = audit.get_summary()
    """

    def __init__(self, batch_id: str, persist: bool = False):
        """
        Initialize audit logger.

        Args:
            batch_id: Unique identifier for this batch
            persist: If True, persist entries to database (TODO)
        """
        self.batch_id = batch_id
        self.persist = persist
        self.entries: list[EnrichmentAuditEntry] = []
        self.summary = BatchAuditSummary(
            batch_id=batch_id,
            started_at=datetime.now(timezone.utc),
        )

    def log_enrichment(self, entry: EnrichmentAuditEntry) -> None:
        """
        Log a single enrichment operation.

        Args:
            entry: Enrichment audit entry to log
        """
        self.entries.append(entry)
        self.summary.update_from_entry(entry)

        # Structured logging for observability
        logger.info(
            "Enrichment completed",
            extra={
                "audit": entry.to_dict(),
            },
        )

        # TODO: Persist to database if self.persist is True
        # await self._persist_entry(entry)

    def log_tiered_enrichment(
        self,
        external_id: str,
        email: str | None,
        is_atl: bool,
        atl_persona: str | None,
        atl_confidence: float,
        atl_reason: str | None,
        credits_used: int,
        phone_revealed: bool,
        direct_phone: str | None = None,
        mobile_phone: str | None = None,
        work_phone: str | None = None,
        title: str | None = None,
        seniority: str | None = None,
        rate_limit_hit: bool = False,
        error: str | None = None,
    ) -> EnrichmentAuditEntry:
        """
        Convenience method to log tiered enrichment with common parameters.

        Returns the created entry for further processing.
        """
        status = EnrichmentStatus.SUCCESS
        if error:
            if "rate limit" in error.lower():
                status = EnrichmentStatus.RATE_LIMITED
            elif "not found" in error.lower():
                status = EnrichmentStatus.NOT_FOUND
            else:
                status = EnrichmentStatus.API_ERROR

        entry = EnrichmentAuditEntry(
            batch_id=self.batch_id,
            external_id=external_id,
            email=email,
            enrichment_type=EnrichmentType.TIERED,
            status=status,
            is_atl=is_atl,
            atl_persona=atl_persona,
            atl_confidence=atl_confidence,
            atl_reason=atl_reason,
            title_checked=title,
            seniority_checked=seniority,
            credits_used=credits_used,
            phase1_credits=1 if credits_used > 0 else 0,
            phase2_credits=8 if phone_revealed else 0,
            phone_revealed=phone_revealed,
            direct_phone_found=bool(direct_phone),
            mobile_phone_found=bool(mobile_phone),
            work_phone_found=bool(work_phone),
            any_phone_found=bool(direct_phone or mobile_phone or work_phone),
            rate_limit_hit=rate_limit_hit,
            error_message=error,
        )

        self.log_enrichment(entry)
        return entry

    def log_clay_enrichment(
        self,
        external_id: str,
        email: str | None,
        action: str,
        phones_found: int = 0,
        emails_found: int = 0,
        success: bool = True,
        error: str | None = None,
    ) -> EnrichmentAuditEntry:
        """
        Log a Clay enrichment event (push or webhook receive).

        Args:
            external_id: Lead external identifier
            email: Lead email
            action: "push" (sent to Clay) or "webhook_received" (got results back)
            phones_found: Number of phones Clay found
            emails_found: Number of emails Clay found
            success: Whether the operation succeeded
            error: Error message if failed
        """
        status = EnrichmentStatus.SUCCESS if success else EnrichmentStatus.API_ERROR

        entry = EnrichmentAuditEntry(
            batch_id=self.batch_id,
            external_id=external_id,
            email=email,
            enrichment_type=EnrichmentType.CLAY,
            status=status,
            credits_used=0,  # Clay credits are managed on Clay's side
            any_phone_found=phones_found > 0,
            error_message=error,
        )

        logger.info(
            "Clay %s: lead=%s phones=%d emails=%d",
            action, external_id, phones_found, emails_found,
        )

        self.log_enrichment(entry)
        return entry

    def set_total_leads(self, count: int) -> None:
        """Set total lead count for the batch."""
        self.summary.total_leads = count

    def get_summary(self) -> BatchAuditSummary:
        """Get finalized batch summary."""
        self.summary.finalize()
        return self.summary

    def log_summary(self) -> None:
        """Log batch summary for observability."""
        summary = self.get_summary()
        logger.info(
            "Enrichment batch completed",
            extra={
                "batch_summary": summary.to_dict(),
            },
        )


# Apollo rate limit tracking
@dataclass
class RateLimitStatus:
    """Tracks Apollo rate limit status for the current session.

    Apollo limits:
    - 50 requests/minute for basic plans
    - Higher limits for enterprise plans
    - Phone reveals may have separate limits
    """

    requests_this_minute: int = 0
    minute_started: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rate_limit_hits_today: int = 0
    last_rate_limit: datetime | None = None
    consecutive_rate_limits: int = 0

    def record_request(self) -> None:
        """Record a request, resetting counter if new minute."""
        now = datetime.now(timezone.utc)
        if (now - self.minute_started).seconds >= 60:
            self.requests_this_minute = 0
            self.minute_started = now
        self.requests_this_minute += 1

    def record_rate_limit(self) -> None:
        """Record a rate limit hit."""
        self.rate_limit_hits_today += 1
        self.last_rate_limit = datetime.now(timezone.utc)
        self.consecutive_rate_limits += 1

    def record_success(self) -> None:
        """Record a successful request (resets consecutive rate limits)."""
        self.consecutive_rate_limits = 0

    def get_backoff_seconds(self) -> float:
        """Calculate exponential backoff based on consecutive rate limits."""
        if self.consecutive_rate_limits == 0:
            return 0.0
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 32s
        return float(min(32, 2 ** (self.consecutive_rate_limits - 1)))

    def should_pause(self, safety_margin: int = 5) -> bool:
        """Check if we should pause to avoid rate limits.

        Args:
            safety_margin: Stop this many requests before estimated limit
        """
        # Assume 50 req/min limit, be conservative
        return self.requests_this_minute >= (50 - safety_margin)
