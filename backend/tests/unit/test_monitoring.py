"""Tests for monitoring endpoints.

Track Apollo credit usage, rate limits, and batch status.
PHONES ARE GOLD - but we need to track how much gold we're spending!
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_monitoring_state():
    """Reset monitoring state before each test."""
    from app.api.routes.monitoring import (
        _active_batches,
        _completed_batches,
        _rate_limit_status,
    )

    _active_batches.clear()
    _completed_batches.clear()
    _rate_limit_status.requests_this_minute = 0
    _rate_limit_status.consecutive_rate_limits = 0
    _rate_limit_status.rate_limit_hits_today = 0

    yield

    # Clean up after test
    _active_batches.clear()
    _completed_batches.clear()


class TestCreditUsageEndpoint:
    """Tests for GET /api/monitoring/credits endpoint."""

    def test_credits_returns_zero_when_no_batches(self, client: TestClient):
        """Test credit usage returns zeros when no batches tracked."""
        response = client.get("/api/monitoring/credits")

        assert response.status_code == 200
        data = response.json()
        assert data["total_credits_used"] == 0
        assert data["phase1_credits"] == 0
        assert data["phase2_credits"] == 0
        assert data["atl_leads"] == 0
        assert data["non_atl_leads"] == 0
        assert data["credits_saved"] == 0

    def test_credits_aggregates_batch_data(self, client: TestClient):
        """Test credit usage aggregates across batches."""
        from app.api.routes.monitoring import (
            _completed_batches,
        )
        from app.services.enrichment.audit import BatchAuditSummary

        # Add some completed batch data
        summary1 = BatchAuditSummary(
            batch_id="batch_1",
            started_at=datetime.now(timezone.utc),
            total_leads=10,
        )
        summary1.total_credits_used = 50
        summary1.phase1_credits = 10
        summary1.phase2_credits = 40
        summary1.atl_leads = 5
        summary1.non_atl_leads = 5
        summary1.phones_revealed = 5
        summary1.direct_phones_found = 3
        summary1.any_phones_found = 4
        _completed_batches["batch_1"] = summary1

        response = client.get("/api/monitoring/credits")

        assert response.status_code == 200
        data = response.json()
        assert data["total_credits_used"] == 50
        assert data["phase1_credits"] == 10
        assert data["phase2_credits"] == 40
        assert data["atl_leads"] == 5
        assert data["non_atl_leads"] == 5
        assert data["phones_revealed"] == 5
        assert data["direct_phones_found"] == 3

    def test_credits_calculates_savings(self, client: TestClient):
        """Test credit savings calculation. Tiered enrichment saves credits!"""
        from app.api.routes.monitoring import _completed_batches
        from app.services.enrichment.audit import BatchAuditSummary

        # Simulate batch where tiered enrichment saved credits
        # Legacy: 10 leads * 8 credits = 80 credits
        # Tiered: 10 * 1 + 3 * 8 = 34 credits (only 3 ATL)
        summary = BatchAuditSummary(
            batch_id="batch_savings",
            started_at=datetime.now(timezone.utc),
            total_leads=10,
        )
        summary.total_credits_used = 34
        summary.atl_leads = 3
        summary.non_atl_leads = 7
        _completed_batches["batch_savings"] = summary

        response = client.get("/api/monitoring/credits")

        assert response.status_code == 200
        data = response.json()
        # Legacy would be 10 * 8 = 80, actual is 34, savings = 46
        assert data["credits_saved"] == 46
        assert data["savings_percent"] > 0.5  # More than 50% saved

    def test_credits_period_parameter(self, client: TestClient):
        """Test period parameter is echoed back."""
        response = client.get("/api/monitoring/credits?period=today")

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "today"


class TestRateLimitEndpoint:
    """Tests for GET /api/monitoring/rate-limits endpoint."""

    def test_rate_limits_returns_healthy_when_no_activity(self, client: TestClient):
        """Test rate limits show healthy when no recent activity."""
        response = client.get("/api/monitoring/rate-limits")

        assert response.status_code == 200
        data = response.json()
        assert data["requests_this_minute"] == 0
        assert data["health"] == "healthy"
        assert data["approaching_limit"] is False
        assert data["current_backoff_seconds"] == 0

    def test_rate_limits_shows_warning_when_approaching(self, client: TestClient):
        """Test rate limits show warning when approaching limit."""
        from app.api.routes.monitoring import get_rate_limit_tracker

        tracker = get_rate_limit_tracker()
        tracker.requests_this_minute = 42  # Above 80% of 50

        response = client.get("/api/monitoring/rate-limits")

        assert response.status_code == 200
        data = response.json()
        assert data["requests_this_minute"] == 42
        assert data["health"] == "warning"
        assert data["approaching_limit"] is True

    def test_rate_limits_shows_critical_on_consecutive_limits(self, client: TestClient):
        """Test rate limits show critical when rate limited."""
        from app.api.routes.monitoring import get_rate_limit_tracker

        tracker = get_rate_limit_tracker()
        tracker.consecutive_rate_limits = 2

        response = client.get("/api/monitoring/rate-limits")

        assert response.status_code == 200
        data = response.json()
        assert data["health"] == "critical"
        assert data["consecutive_rate_limits"] == 2
        assert data["current_backoff_seconds"] > 0

    def test_rate_limits_backoff_calculation(self, client: TestClient):
        """Test exponential backoff calculation."""
        from app.api.routes.monitoring import get_rate_limit_tracker

        tracker = get_rate_limit_tracker()

        # 1 consecutive = 1s backoff
        tracker.consecutive_rate_limits = 1
        response = client.get("/api/monitoring/rate-limits")
        assert response.json()["current_backoff_seconds"] == 1

        # 3 consecutive = 4s backoff
        tracker.consecutive_rate_limits = 3
        response = client.get("/api/monitoring/rate-limits")
        assert response.json()["current_backoff_seconds"] == 4


class TestBatchStatusEndpoint:
    """Tests for GET /api/monitoring/batches/{batch_id} endpoint."""

    def test_batch_status_returns_404_for_unknown(self, client: TestClient):
        """Test batch status returns 404 for unknown batch."""
        response = client.get("/api/monitoring/batches/unknown_batch_123")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_batch_status_returns_active_batch(self, client: TestClient):
        """Test batch status for active batch."""
        from app.api.routes.monitoring import register_batch

        register_batch("test_batch_001", total_leads=100)

        response = client.get("/api/monitoring/batches/test_batch_001")

        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == "test_batch_001"
        assert data["status"] == "processing"
        assert data["total_leads"] == 100
        assert data["processed"] == 0
        assert data["progress_percent"] == 0.0

    def test_batch_status_returns_completed_batch(self, client: TestClient):
        """Test batch status for completed batch."""
        from app.api.routes.monitoring import complete_batch, get_batch, register_batch

        register_batch("completed_batch", total_leads=50)
        batch = get_batch("completed_batch")
        batch.processed = 50
        batch.atl_leads = 10
        batch.non_atl_leads = 40
        batch.total_credits_used = 130

        complete_batch("completed_batch")

        response = client.get("/api/monitoring/batches/completed_batch")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["processed"] == 50
        assert data["progress_percent"] == 100.0
        assert data["atl_leads"] == 10
        assert data["non_atl_leads"] == 40
        assert data["credits_used"] == 130

    def test_batch_status_shows_progress(self, client: TestClient):
        """Test batch status shows progress percentage."""
        from app.api.routes.monitoring import get_batch, register_batch

        register_batch("progress_batch", total_leads=100)
        batch = get_batch("progress_batch")
        batch.processed = 30

        response = client.get("/api/monitoring/batches/progress_batch")

        assert response.status_code == 200
        data = response.json()
        assert data["progress_percent"] == 30.0


class TestListBatchesEndpoint:
    """Tests for GET /api/monitoring/batches endpoint."""

    def test_list_batches_empty(self, client: TestClient):
        """Test list batches returns empty when no batches."""
        response = client.get("/api/monitoring/batches")

        assert response.status_code == 200
        data = response.json()
        assert data["active_count"] == 0
        assert data["completed_count"] == 0
        assert data["active_batches"] == []
        assert data["recent_completed"] == []

    def test_list_batches_shows_active(self, client: TestClient):
        """Test list batches shows active batches."""
        from app.api.routes.monitoring import register_batch

        register_batch("active_1", 50)
        register_batch("active_2", 100)

        response = client.get("/api/monitoring/batches")

        assert response.status_code == 200
        data = response.json()
        assert data["active_count"] == 2
        batch_ids = [b["batch_id"] for b in data["active_batches"]]
        assert "active_1" in batch_ids
        assert "active_2" in batch_ids

    def test_list_batches_shows_completed(self, client: TestClient):
        """Test list batches shows completed batches."""
        from app.api.routes.monitoring import complete_batch, register_batch

        register_batch("done_1", 10)
        complete_batch("done_1")

        response = client.get("/api/monitoring/batches")

        assert response.status_code == 200
        data = response.json()
        assert data["completed_count"] == 1
        assert data["recent_completed"][0]["batch_id"] == "done_1"


class TestBatchTracking:
    """Tests for batch tracking utility functions."""

    def test_register_batch_creates_summary(self):
        """Test register_batch creates BatchAuditSummary."""
        from app.api.routes.monitoring import get_batch, register_batch

        summary = register_batch("new_batch", 25)

        assert summary.batch_id == "new_batch"
        assert summary.total_leads == 25
        assert summary.processed == 0

        # Should be retrievable
        retrieved = get_batch("new_batch")
        assert retrieved is summary

    def test_complete_batch_moves_to_completed(self):
        """Test complete_batch moves batch from active to completed."""
        from app.api.routes.monitoring import (
            _active_batches,
            _completed_batches,
            complete_batch,
            register_batch,
        )

        register_batch("to_complete", 10)
        assert "to_complete" in _active_batches
        assert "to_complete" not in _completed_batches

        complete_batch("to_complete")

        assert "to_complete" not in _active_batches
        assert "to_complete" in _completed_batches

    def test_complete_batch_finalizes_summary(self):
        """Test complete_batch calls finalize on summary."""
        from app.api.routes.monitoring import complete_batch, get_batch, register_batch

        register_batch("finalize_test", 20)
        batch = get_batch("finalize_test")
        batch.processed = 20
        batch.atl_leads = 4
        batch.non_atl_leads = 16

        complete_batch("finalize_test")

        completed = get_batch("finalize_test")
        assert completed.completed_at is not None
        assert completed.atl_rate > 0  # Should be calculated


class TestRateLimitTracking:
    """Tests for rate limit tracker."""

    def test_rate_limit_tracker_records_requests(self):
        """Test rate limit tracker counts requests."""
        from app.api.routes.monitoring import get_rate_limit_tracker

        tracker = get_rate_limit_tracker()
        initial = tracker.requests_this_minute

        tracker.record_request()
        assert tracker.requests_this_minute == initial + 1

    def test_rate_limit_tracker_records_limits(self):
        """Test rate limit tracker counts rate limits."""
        from app.api.routes.monitoring import get_rate_limit_tracker

        tracker = get_rate_limit_tracker()

        tracker.record_rate_limit()
        assert tracker.consecutive_rate_limits == 1
        assert tracker.rate_limit_hits_today == 1

        tracker.record_rate_limit()
        assert tracker.consecutive_rate_limits == 2
        assert tracker.rate_limit_hits_today == 2

    def test_rate_limit_tracker_success_resets_consecutive(self):
        """Test successful request resets consecutive rate limits."""
        from app.api.routes.monitoring import get_rate_limit_tracker

        tracker = get_rate_limit_tracker()
        tracker.consecutive_rate_limits = 5

        tracker.record_success()
        assert tracker.consecutive_rate_limits == 0
