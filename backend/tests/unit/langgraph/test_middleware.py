"""Tests for LangGraph middleware layer.

Tests cover:
- PIIDetectionMiddleware: PII detection and scrubbing
- DynamicModelMiddleware: Model selection based on complexity
- RateLimitMiddleware: Rate limiting with token buckets
- MiddlewarePipeline: Executing multiple middleware
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.langgraph.middleware import (
    DynamicModelMiddleware,
    MiddlewarePipeline,
    PIIDetectionMiddleware,
    RateLimitBucket,
    RateLimitConfig,
    RateLimitMiddleware,
    create_default_pipeline,
)


class TestPIIDetectionMiddleware:
    """Tests for PII detection middleware."""

    @pytest.fixture
    def middleware(self) -> PIIDetectionMiddleware:
        """Create middleware instance."""
        return PIIDetectionMiddleware()

    def test_detects_email(self, middleware: PIIDetectionMiddleware) -> None:
        """Test email detection."""
        text = "Contact me at john.doe@example.com for more info."
        matches = middleware.detect_pii(text)

        assert len(matches) == 1
        assert matches[0].pii_type == "email"
        assert matches[0].original == "john.doe@example.com"

    def test_detects_phone(self, middleware: PIIDetectionMiddleware) -> None:
        """Test phone number detection."""
        text = "Call me at 555-123-4567 for more info."
        matches = middleware.detect_pii(text)

        phone_matches = [m for m in matches if m.pii_type == "phone"]
        assert len(phone_matches) == 1
        assert phone_matches[0].original == "555-123-4567"

    def test_detects_ssn(self, middleware: PIIDetectionMiddleware) -> None:
        """Test SSN detection."""
        text = "My SSN is 123-45-6789."
        matches = middleware.detect_pii(text)

        assert len(matches) == 1
        assert matches[0].pii_type == "ssn"

    def test_detects_credit_card(self, middleware: PIIDetectionMiddleware) -> None:
        """Test credit card detection."""
        text = "Card number: 4111-1111-1111-1111"
        matches = middleware.detect_pii(text)

        assert len(matches) == 1
        assert matches[0].pii_type == "credit_card"

    def test_detects_ip_address(self, middleware: PIIDetectionMiddleware) -> None:
        """Test IP address detection."""
        text = "Server IP: 192.168.1.100"
        matches = middleware.detect_pii(text)

        assert len(matches) == 1
        assert matches[0].pii_type == "ip_address"

    def test_scrubs_all_pii(self, middleware: PIIDetectionMiddleware) -> None:
        """Test scrubbing all PII types."""
        text = "Email: test@example.com, Phone: 555-123-4567"
        scrubbed = middleware.scrub_text(text)

        assert "[EMAIL_REDACTED]" in scrubbed
        assert "[PHONE_REDACTED]" in scrubbed
        assert "test@example.com" not in scrubbed
        assert "555-123-4567" not in scrubbed

    def test_respects_allowed_domains(self) -> None:
        """Test that allowed email domains are not scrubbed."""
        middleware = PIIDetectionMiddleware(
            allowed_domains={"company.com", "partner.org"}
        )
        text = "Contact: user@company.com or user@external.com"
        scrubbed = middleware.scrub_text(text)

        assert "user@company.com" in scrubbed  # Allowed
        assert "[EMAIL_REDACTED]" in scrubbed  # External scrubbed

    @pytest.mark.asyncio
    async def test_before_agent_logs_pii_warnings(
        self, middleware: PIIDetectionMiddleware
    ) -> None:
        """Test that before_agent scans state for PII."""
        state = {
            "email": "user@example.com",
            "context": "Call 555-123-4567 for details",
        }

        result = await middleware.before_agent(state)

        # State should be unchanged (only logs warnings)
        assert result == state
        # Detection stats should be updated
        stats = middleware.get_detection_stats()
        assert stats["email"] > 0
        assert stats["phone"] > 0

    @pytest.mark.asyncio
    async def test_after_agent_scrubs_outputs_when_enabled(self) -> None:
        """Test that outputs are scrubbed when enabled."""
        middleware = PIIDetectionMiddleware(scrub_outputs=True)
        state: dict[str, str] = {}
        result = {
            "response": "Contact john@example.com for help",
            "metadata": {"phone": "555-123-4567"},
        }

        scrubbed = await middleware.after_agent(state, result)

        assert "[EMAIL_REDACTED]" in scrubbed["response"]
        assert "[PHONE_REDACTED]" in scrubbed["metadata"]["phone"]

    def test_get_detection_stats(self, middleware: PIIDetectionMiddleware) -> None:
        """Test getting detection statistics."""
        middleware.detect_pii("test@example.com 555-123-4567")
        stats = middleware.get_detection_stats()

        assert stats["email"] == 1
        assert stats["phone"] == 1
        assert stats["ssn"] == 0

    def test_reset_stats(self, middleware: PIIDetectionMiddleware) -> None:
        """Test resetting detection statistics."""
        middleware.detect_pii("test@example.com")
        middleware.reset_stats()
        stats = middleware.get_detection_stats()

        assert stats["email"] == 0


class TestDynamicModelMiddleware:
    """Tests for dynamic model selection middleware."""

    @pytest.fixture
    def middleware(self) -> DynamicModelMiddleware:
        """Create middleware instance."""
        return DynamicModelMiddleware(
            default_model="sonnet",
            fast_model="haiku",
            powerful_model="opus",
        )

    @pytest.mark.asyncio
    async def test_selects_fast_model_for_simple_task(
        self, middleware: DynamicModelMiddleware
    ) -> None:
        """Test that simple tasks get fast model."""
        state = {"context": "lookup the user", "query": "find email"}

        result = await middleware.before_agent(state)

        assert result["_selected_model"] == "haiku"
        assert result["_model_selection_reason"] == "simple_task"

    @pytest.mark.asyncio
    async def test_selects_powerful_model_for_complex_task(
        self, middleware: DynamicModelMiddleware
    ) -> None:
        """Test that complex tasks get powerful model."""
        state = {
            "context": "analyze and synthesize the competitive landscape, "
            "evaluate multiple strategies, and recommend an approach",
            "query": "design a comprehensive architecture",
        }

        result = await middleware.before_agent(state)

        assert result["_selected_model"] == "opus"
        assert result["_model_selection_reason"] == "complex_task"

    @pytest.mark.asyncio
    async def test_selects_default_model_for_standard_task(
        self, middleware: DynamicModelMiddleware
    ) -> None:
        """Test that standard tasks get default model."""
        state = {
            "context": "Generate a sales email for the prospect",
            "query": "Create personalized outreach",
        }

        result = await middleware.before_agent(state)

        assert result["_selected_model"] == "sonnet"
        assert result["_model_selection_reason"] == "standard_task"

    def test_complexity_calculation(
        self, middleware: DynamicModelMiddleware
    ) -> None:
        """Test complexity score calculation."""
        simple_text = "get the user list"
        complex_text = "analyze synthesize evaluate design recommend strategy"

        simple_score = middleware._calculate_complexity(simple_text)
        complex_score = middleware._calculate_complexity(complex_text)

        assert simple_score < 0.4
        assert complex_score > 0.6

    def test_token_estimation(self, middleware: DynamicModelMiddleware) -> None:
        """Test token count estimation."""
        text = "This is a test with ten words total here now"  # 10 words
        tokens = middleware._estimate_tokens(text)

        # Should be roughly word_count * 1.3
        assert tokens == 13

    def test_get_selection_history(
        self, middleware: DynamicModelMiddleware
    ) -> None:
        """Test that selection history is recorded."""
        import asyncio

        asyncio.get_event_loop().run_until_complete(
            middleware.before_agent({"context": "simple lookup"})
        )
        asyncio.get_event_loop().run_until_complete(
            middleware.before_agent({"context": "complex analysis"})
        )

        history = middleware.get_selection_history()
        assert len(history) == 2

    def test_clear_history(self, middleware: DynamicModelMiddleware) -> None:
        """Test clearing selection history."""
        import asyncio

        asyncio.get_event_loop().run_until_complete(
            middleware.before_agent({"context": "test"})
        )
        middleware.clear_history()

        assert len(middleware.get_selection_history()) == 0


class TestRateLimitBucket:
    """Tests for rate limit token bucket."""

    def test_consume_succeeds_with_tokens(self) -> None:
        """Test consuming tokens when available."""
        bucket = RateLimitBucket(
            tokens=10.0,
            last_update=datetime.now(timezone.utc),
            max_tokens=10.0,
            refill_rate=1.0,
        )

        assert bucket.consume(1.0) is True
        assert bucket.tokens == 9.0

    def test_consume_fails_without_tokens(self) -> None:
        """Test consuming tokens when empty."""
        bucket = RateLimitBucket(
            tokens=0.0,
            last_update=datetime.now(timezone.utc),
            max_tokens=10.0,
            refill_rate=0.0,  # Zero refill rate to prevent any refill
        )

        assert bucket.consume(1.0) is False
        assert bucket.tokens == 0.0

    def test_refill_over_time(self) -> None:
        """Test token refill over time."""
        bucket = RateLimitBucket(
            tokens=0.0,
            last_update=datetime.now(timezone.utc) - timedelta(seconds=5),
            max_tokens=10.0,
            refill_rate=1.0,  # 1 token per second
        )

        # Should refill 5 tokens over 5 seconds
        assert bucket.consume(1.0) is True
        assert bucket.tokens >= 4.0  # At least 4 remaining

    def test_refill_caps_at_max(self) -> None:
        """Test that refill doesn't exceed max tokens."""
        bucket = RateLimitBucket(
            tokens=0.0,
            last_update=datetime.now(timezone.utc) - timedelta(hours=1),
            max_tokens=10.0,
            refill_rate=1.0,
        )

        bucket._refill()
        assert bucket.tokens == 10.0  # Capped at max


class TestRateLimitMiddleware:
    """Tests for rate limit middleware."""

    @pytest.fixture
    def middleware(self) -> RateLimitMiddleware:
        """Create middleware with low limits for testing."""
        return RateLimitMiddleware(
            config=RateLimitConfig(
                requests_per_minute=5,
                requests_per_hour=100,
                burst_size=3,
            )
        )

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Test that requests within limit are allowed."""
        state: dict[str, str] = {}

        result = await middleware.before_agent(state)

        assert result["_rate_limited"] is False

    @pytest.mark.asyncio
    async def test_rate_limits_burst(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Test that burst exceeding limit is rate limited."""
        state: dict[str, str] = {}

        # Exhaust burst limit
        for _ in range(3):
            await middleware.before_agent(state)

        # Next request should be rate limited
        result = await middleware.before_agent(state)
        assert result["_rate_limited"] is True
        assert result["_rate_limit_reason"] == "minute_limit_exceeded"

    def test_get_remaining_tokens(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Test getting remaining rate limit tokens."""
        tokens = middleware.get_remaining_tokens()

        assert "minute" in tokens
        assert "hour" in tokens
        assert tokens["minute"] == 3.0  # burst_size

    def test_get_stats(self, middleware: RateLimitMiddleware) -> None:
        """Test getting rate limit statistics."""
        stats = middleware.get_stats()

        assert stats["total_requests"] == 0
        assert stats["rate_limited_count"] == 0
        assert stats["rate_limited_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_stats_update_on_requests(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Test that stats update with requests."""
        # Make several requests
        for _ in range(5):
            await middleware.before_agent({})

        stats = middleware.get_stats()
        assert stats["total_requests"] == 5
        # Some should be rate limited (only burst_size=3 allowed)
        assert stats["rate_limited_count"] >= 2

    def test_reset(self, middleware: RateLimitMiddleware) -> None:
        """Test resetting rate limits."""
        import asyncio

        # Exhaust limits
        for _ in range(5):
            asyncio.get_event_loop().run_until_complete(
                middleware.before_agent({})
            )

        middleware.reset()

        stats = middleware.get_stats()
        assert stats["total_requests"] == 0
        assert stats["rate_limited_count"] == 0


class TestMiddlewarePipeline:
    """Tests for middleware pipeline."""

    @pytest.fixture
    def pipeline(self) -> MiddlewarePipeline:
        """Create pipeline with test middleware."""
        return MiddlewarePipeline([
            PIIDetectionMiddleware(),
            DynamicModelMiddleware(),
        ])

    @pytest.mark.asyncio
    async def test_run_before_executes_all_middleware(
        self, pipeline: MiddlewarePipeline
    ) -> None:
        """Test that before hooks run in order."""
        state = {"context": "simple lookup task"}

        result = await pipeline.run_before(state)

        # Model should be selected
        assert "_selected_model" in result

    @pytest.mark.asyncio
    async def test_run_after_executes_in_reverse(
        self, pipeline: MiddlewarePipeline
    ) -> None:
        """Test that after hooks run in reverse order."""
        state: dict[str, str] = {}
        result = {"response": "test"}

        final_result = await pipeline.run_after(state, result)

        # Result should pass through unchanged (no scrubbing enabled)
        assert final_result == result

    def test_add_middleware_chaining(self) -> None:
        """Test that add() supports method chaining."""
        pipeline = (
            MiddlewarePipeline()
            .add(PIIDetectionMiddleware())
            .add(DynamicModelMiddleware())
        )

        assert len(pipeline.middlewares) == 2


class TestCreateDefaultPipeline:
    """Tests for default pipeline factory."""

    def test_creates_pipeline_with_defaults(self) -> None:
        """Test creating pipeline with default settings."""
        pipeline = create_default_pipeline()

        assert len(pipeline.middlewares) == 3
        assert isinstance(pipeline.middlewares[0], PIIDetectionMiddleware)
        assert isinstance(pipeline.middlewares[1], DynamicModelMiddleware)
        assert isinstance(pipeline.middlewares[2], RateLimitMiddleware)

    def test_creates_pipeline_with_custom_settings(self) -> None:
        """Test creating pipeline with custom settings."""
        pipeline = create_default_pipeline(
            scrub_pii_outputs=True,
            allowed_email_domains={"company.com"},
            rate_limit_config=RateLimitConfig(requests_per_minute=100),
        )

        pii_middleware = pipeline.middlewares[0]
        assert isinstance(pii_middleware, PIIDetectionMiddleware)
        assert pii_middleware.scrub_outputs is True
        assert "company.com" in pii_middleware.allowed_domains
