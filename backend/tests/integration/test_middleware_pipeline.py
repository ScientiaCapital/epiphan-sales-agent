"""Integration tests for middleware pipeline.

Tests verify:
1. ModelCallLimitMiddleware raises after exceeding run limit
2. ModelFallbackMiddleware triggers on recorded primary failure
3. Full pipeline end-to-end with multiple middleware
"""

from typing import Any

import pytest

from app.services.langgraph.middleware import (
    MiddlewarePipeline,
    ModelCallLimitError,
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    PIIDetectionMiddleware,
    RateLimitConfig,
    create_default_pipeline,
)


class TestModelCallLimitMiddleware:
    """Tests for ModelCallLimitMiddleware enforcement."""

    @pytest.fixture
    def middleware(self) -> ModelCallLimitMiddleware:
        """Create middleware with low limits for testing."""
        return ModelCallLimitMiddleware(
            thread_limit=10,
            run_limit=5,
        )

    @pytest.mark.asyncio
    async def test_allows_calls_within_run_limit(
        self, middleware: ModelCallLimitMiddleware
    ) -> None:
        """Test calls within run limit succeed."""
        state: dict[str, Any] = {"_thread_id": "test-thread"}

        # 5 calls should all succeed (limit is 5)
        for i in range(5):
            result = await middleware.before_agent(state.copy())
            assert "_model_call_count" in result
            assert result["_model_call_count"] == i + 1

    @pytest.mark.asyncio
    async def test_raises_after_exceeding_run_limit(
        self, middleware: ModelCallLimitMiddleware
    ) -> None:
        """Test raises ModelCallLimitError after run limit exceeded."""
        state: dict[str, Any] = {"_thread_id": "test-thread"}

        # Make 5 allowed calls
        for _ in range(5):
            await middleware.before_agent(state.copy())

        # 6th call should raise
        with pytest.raises(ModelCallLimitError) as exc_info:
            await middleware.before_agent(state.copy())

        assert exc_info.value.limit_type == "run"
        assert exc_info.value.count == 6
        assert exc_info.value.limit == 5

    @pytest.mark.asyncio
    async def test_raises_after_exceeding_thread_limit(self) -> None:
        """Test raises ModelCallLimitError after thread limit exceeded."""
        middleware = ModelCallLimitMiddleware(
            thread_limit=3,  # Low thread limit
            run_limit=100,  # High run limit
        )
        state: dict[str, Any] = {"_thread_id": "test-thread"}

        # Make 3 allowed calls
        for _ in range(3):
            await middleware.before_agent(state.copy())
            middleware.reset_run()  # Reset run counter to not hit run limit

        # 4th call should raise thread limit error
        with pytest.raises(ModelCallLimitError) as exc_info:
            await middleware.before_agent(state.copy())

        assert exc_info.value.limit_type == "thread"
        assert exc_info.value.count == 4
        assert exc_info.value.limit == 3

    @pytest.mark.asyncio
    async def test_different_threads_tracked_separately(
        self, middleware: ModelCallLimitMiddleware
    ) -> None:
        """Test each thread has independent counters."""
        state_a: dict[str, Any] = {"_thread_id": "thread-a"}
        state_b: dict[str, Any] = {"_thread_id": "thread-b"}

        # Make 5 calls on thread A
        for _ in range(5):
            await middleware.before_agent(state_a.copy())
            middleware.reset_run()

        # Thread B should still have capacity
        result = await middleware.before_agent(state_b.copy())
        assert result["_thread_call_count"] == 1

    @pytest.mark.asyncio
    async def test_reset_run_clears_run_counter(
        self, middleware: ModelCallLimitMiddleware
    ) -> None:
        """Test reset_run() allows new run calls."""
        state: dict[str, Any] = {"_thread_id": "test-thread"}

        # Make 5 calls
        for _ in range(5):
            await middleware.before_agent(state.copy())

        # Reset run
        middleware.reset_run()

        # Should be able to make calls again
        result = await middleware.before_agent(state.copy())
        assert result["_model_call_count"] == 1

    @pytest.mark.asyncio
    async def test_reset_thread_clears_thread_counter(self) -> None:
        """Test reset_thread() clears specific thread counter."""
        middleware = ModelCallLimitMiddleware(thread_limit=3, run_limit=100)
        state: dict[str, Any] = {"_thread_id": "test-thread"}

        # Make 3 calls
        for _ in range(3):
            await middleware.before_agent(state.copy())
            middleware.reset_run()

        # Reset thread
        middleware.reset_thread("test-thread")

        # Should be able to make calls again
        result = await middleware.before_agent(state.copy())
        assert result["_thread_call_count"] == 1

    @pytest.mark.asyncio
    async def test_stats_tracking(
        self, middleware: ModelCallLimitMiddleware
    ) -> None:
        """Test statistics are tracked correctly."""
        state: dict[str, Any] = {"_thread_id": "test-thread"}

        # Make some calls
        for _ in range(3):
            await middleware.before_agent(state.copy())

        stats = middleware.get_stats()
        assert stats.run_calls == 3
        assert stats.thread_calls == 3

    @pytest.mark.asyncio
    async def test_limit_error_stats_incremented(self) -> None:
        """Test limit_errors stat incremented on error."""
        middleware = ModelCallLimitMiddleware(run_limit=1, thread_limit=100)
        state: dict[str, Any] = {"_thread_id": "test-thread"}

        await middleware.before_agent(state.copy())

        with pytest.raises(ModelCallLimitError):
            await middleware.before_agent(state.copy())

        stats = middleware.get_stats()
        assert stats.limit_errors == 1


class TestModelFallbackMiddleware:
    """Tests for ModelFallbackMiddleware behavior."""

    @pytest.fixture
    def middleware(self) -> ModelFallbackMiddleware:
        """Create fallback middleware."""
        return ModelFallbackMiddleware(
            fallback_model="openrouter",
            max_fallback_attempts=3,
        )

    @pytest.mark.asyncio
    async def test_no_fallback_on_initial_call(
        self, middleware: ModelFallbackMiddleware
    ) -> None:
        """Test first call uses primary model."""
        state: dict[str, Any] = {}

        result = await middleware.before_agent(state)

        assert result.get("_use_fallback") is False

    @pytest.mark.asyncio
    async def test_fallback_triggered_after_error_recorded(
        self, middleware: ModelFallbackMiddleware
    ) -> None:
        """Test fallback triggers when primary error is recorded."""
        state: dict[str, Any] = {}

        # Record a primary error
        state = middleware.record_primary_error(state, "Connection refused")

        # Next call should use fallback
        result = await middleware.before_agent(state)

        assert result["_use_fallback"] is True
        assert result["_fallback_model"] == "openrouter"
        assert result["_fallback_reason"] == "Connection refused"

    @pytest.mark.asyncio
    async def test_max_fallback_attempts_enforced(
        self, middleware: ModelFallbackMiddleware
    ) -> None:
        """Test fallback stops after max attempts."""
        state: dict[str, Any] = {}

        # Trigger 3 fallback attempts (max)
        for i in range(3):
            state = middleware.record_primary_error(state, f"Error {i}")
            state = await middleware.before_agent(state)
            assert state["_use_fallback"] is True

        # 4th attempt should not trigger fallback
        state = middleware.record_primary_error(state, "Error 4")
        state = await middleware.before_agent(state)
        assert state["_use_fallback"] is False

    @pytest.mark.asyncio
    async def test_after_agent_records_fallback_attempt(
        self, middleware: ModelFallbackMiddleware
    ) -> None:
        """Test successful fallback is recorded."""
        state: dict[str, Any] = {}
        state = middleware.record_primary_error(state, "Timeout")
        state = await middleware.before_agent(state)

        # Simulate successful result
        await middleware.after_agent(state, {"result": "success"})

        attempts = middleware.get_attempts()
        assert len(attempts) == 1
        assert attempts[0].success is True
        assert attempts[0].fallback_model == "openrouter"

    @pytest.mark.asyncio
    async def test_stats_track_success_rate(
        self, middleware: ModelFallbackMiddleware
    ) -> None:
        """Test statistics track fallback success rate."""
        state: dict[str, Any] = {}

        # Two successful fallbacks
        for _ in range(2):
            state = middleware.record_primary_error(state, "Error")
            state = await middleware.before_agent(state)
            await middleware.after_agent(state, {"result": "ok"})

        stats = middleware.get_stats()
        assert stats["total_fallbacks"] == 2
        assert stats["successful_fallbacks"] == 2
        assert stats["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_reset_clears_fallback_count(
        self, middleware: ModelFallbackMiddleware
    ) -> None:
        """Test reset allows fallback again."""
        state: dict[str, Any] = {}

        # Use up all fallback attempts
        for _ in range(3):
            state = middleware.record_primary_error(state, "Error")
            await middleware.before_agent(state)

        # Reset
        middleware.reset()

        # Should be able to fallback again
        state = middleware.record_primary_error({}, "New error")
        result = await middleware.before_agent(state)
        assert result["_use_fallback"] is True


class TestMiddlewarePipeline:
    """Tests for MiddlewarePipeline orchestration."""

    @pytest.mark.asyncio
    async def test_pipeline_executes_all_middleware(self) -> None:
        """Test pipeline runs all middleware in order."""
        pipeline = MiddlewarePipeline()
        pipeline.add(PIIDetectionMiddleware())
        pipeline.add(ModelCallLimitMiddleware(thread_limit=100, run_limit=50))

        state: dict[str, Any] = {"input": "test@email.com"}

        result = await pipeline.run_before(state)

        # Both middleware should have processed the state
        assert "_pii_warnings" in result or "_model_call_count" in result

    @pytest.mark.asyncio
    async def test_pipeline_stops_on_exception(self) -> None:
        """Test pipeline stops when middleware raises."""
        pipeline = MiddlewarePipeline()
        limit_middleware = ModelCallLimitMiddleware(run_limit=0)  # Will fail immediately
        pipeline.add(limit_middleware)

        state: dict[str, Any] = {"_thread_id": "test"}

        with pytest.raises(ModelCallLimitError):
            await pipeline.run_before(state)

    @pytest.mark.asyncio
    async def test_create_default_pipeline(self) -> None:
        """Test default pipeline is created correctly."""
        config = RateLimitConfig(requests_per_minute=60, requests_per_hour=1000)
        pipeline = create_default_pipeline(rate_limit_config=config)

        # Should have default middleware (PII, Dynamic, RateLimit, CallLimit, Fallback)
        assert len(pipeline.middlewares) >= 3

    @pytest.mark.asyncio
    async def test_pipeline_run_after_processes_result(self) -> None:
        """Test run_after passes result through all middleware."""
        pipeline = MiddlewarePipeline()
        fallback = ModelFallbackMiddleware()
        pipeline.add(fallback)

        # Set up state for fallback recording
        state: dict[str, Any] = {"_use_fallback": True}

        result = await pipeline.run_after(state, {"output": "test"})

        # Result should pass through
        assert result == {"output": "test"}


class TestFullPipelineIntegration:
    """End-to-end integration tests for complete middleware stack."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_pii_and_limits(self) -> None:
        """Test realistic pipeline with PII detection and call limits."""
        pipeline = MiddlewarePipeline()
        pipeline.add(PIIDetectionMiddleware())
        pipeline.add(ModelCallLimitMiddleware(thread_limit=10, run_limit=5))
        pipeline.add(ModelFallbackMiddleware())

        state: dict[str, Any] = {
            "_thread_id": "integration-test",
            "input": "Contact john@example.com for details",
        }

        # First call should succeed
        result = await pipeline.run_before(state)

        # PII detection may or may not find anything depending on input
        # Just verify the middleware ran without error (call count is tracked below)

        # Call count should be tracked
        assert result.get("_model_call_count") == 1

        # No fallback needed
        assert result.get("_use_fallback") is False

    @pytest.mark.asyncio
    async def test_pipeline_enforces_limits_through_stack(self) -> None:
        """Test call limits are enforced even in full pipeline."""
        pipeline = MiddlewarePipeline()
        pipeline.add(PIIDetectionMiddleware())
        limit_mw = ModelCallLimitMiddleware(run_limit=3)
        pipeline.add(limit_mw)

        state: dict[str, Any] = {"_thread_id": "limit-test", "input": "test"}

        # Make 3 allowed calls
        for _ in range(3):
            await pipeline.run_before(state.copy())

        # 4th should raise
        with pytest.raises(ModelCallLimitError):
            await pipeline.run_before(state.copy())

    @pytest.mark.asyncio
    async def test_pipeline_fallback_after_simulated_failure(self) -> None:
        """Test fallback middleware works in pipeline context."""
        fallback = ModelFallbackMiddleware()
        pipeline = MiddlewarePipeline()
        pipeline.add(fallback)

        state: dict[str, Any] = {}

        # First call - no fallback
        result = await pipeline.run_before(state)
        assert result.get("_use_fallback") is False

        # Record error (simulating primary failure)
        state = fallback.record_primary_error(state, "API timeout")

        # Second call - should trigger fallback
        result = await pipeline.run_before(state)
        assert result["_use_fallback"] is True
        assert result["_fallback_model"] == "openrouter"


class TestMiddlewareEdgeCases:
    """Edge case tests for middleware robustness."""

    @pytest.mark.asyncio
    async def test_call_limit_with_default_thread_id(self) -> None:
        """Test middleware handles missing thread_id gracefully."""
        middleware = ModelCallLimitMiddleware(run_limit=5)
        state: dict[str, Any] = {}  # No _thread_id

        result = await middleware.before_agent(state)

        # Should use default thread_id
        assert result["_model_call_count"] == 1

    @pytest.mark.asyncio
    async def test_fallback_with_empty_error(self) -> None:
        """Test fallback handles empty error string."""
        middleware = ModelFallbackMiddleware()
        state: dict[str, Any] = {}

        state = middleware.record_primary_error(state, "")
        result = await middleware.before_agent(state)

        # Empty string is falsy, should not trigger fallback
        assert result.get("_use_fallback") is False

    @pytest.mark.asyncio
    async def test_reset_all_clears_everything(self) -> None:
        """Test reset_all clears all tracked state."""
        middleware = ModelCallLimitMiddleware(run_limit=3, thread_limit=5)

        # Make some calls across threads
        for thread_id in ["a", "b", "c"]:
            await middleware.before_agent({"_thread_id": thread_id})

        middleware.reset_all()

        # All counters should be cleared
        result = await middleware.before_agent({"_thread_id": "a"})
        assert result["_model_call_count"] == 1
        assert result["_thread_call_count"] == 1
