"""Tests for Clay enrichment audit logging.

Verifies Clay events are tracked in the same audit system as Apollo.
"""

from app.services.enrichment.audit import (
    EnrichmentAuditLogger,
    EnrichmentStatus,
    EnrichmentType,
)


class TestClayAuditLogging:
    """Tests for Clay audit log entries and summaries."""

    def test_clay_enrichment_type_exists(self) -> None:
        """CLAY is a valid EnrichmentType."""
        assert EnrichmentType.CLAY.value == "clay"

    def test_audit_clay_push(self) -> None:
        """Logs Clay push event with correct enrichment type."""
        logger = EnrichmentAuditLogger(batch_id="test_batch")
        entry = logger.log_clay_enrichment(
            external_id="ext_001",
            email="john@acme.com",
            action="push",
            success=True,
        )
        assert entry.enrichment_type == EnrichmentType.CLAY
        assert entry.status == EnrichmentStatus.SUCCESS
        assert entry.credits_used == 0
        assert entry.batch_id == "test_batch"

    def test_audit_clay_webhook(self) -> None:
        """Logs Clay webhook receive event with phone counts."""
        logger = EnrichmentAuditLogger(batch_id="test_batch")
        entry = logger.log_clay_enrichment(
            external_id="ext_002",
            email="jane@acme.com",
            action="webhook_received",
            phones_found=2,
            emails_found=1,
            success=True,
        )
        assert entry.any_phone_found is True
        assert entry.enrichment_type == EnrichmentType.CLAY

    def test_audit_clay_failure(self) -> None:
        """Logs Clay failure event."""
        logger = EnrichmentAuditLogger(batch_id="test_batch")
        entry = logger.log_clay_enrichment(
            external_id="ext_003",
            email="fail@acme.com",
            action="push",
            success=False,
            error="Clay webhook timeout",
        )
        assert entry.status == EnrichmentStatus.API_ERROR
        assert entry.error_message == "Clay webhook timeout"

    def test_audit_summary_includes_clay(self) -> None:
        """Batch summary correctly counts Clay events."""
        logger = EnrichmentAuditLogger(batch_id="test_batch")
        logger.set_total_leads(3)

        # Log 2 Clay enrichments and 1 failure
        logger.log_clay_enrichment(
            external_id="ext_001", email="a@a.com", action="push", phones_found=1
        )
        logger.log_clay_enrichment(
            external_id="ext_002", email="b@b.com", action="push", phones_found=0
        )
        logger.log_clay_enrichment(
            external_id="ext_003", email="c@c.com", action="push",
            success=False, error="Timeout",
        )

        summary = logger.get_summary()
        assert summary.processed == 3
        assert summary.any_phones_found == 1
        assert summary.api_errors == 1
