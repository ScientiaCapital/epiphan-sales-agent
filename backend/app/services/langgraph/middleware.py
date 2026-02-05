"""Middleware Layer for LangGraph Agents.

Provides middleware hooks that run before and after agent execution:
- PIIDetectionMiddleware: Detect and scrub PII from logs and outputs
- DynamicModelMiddleware: Select model based on task complexity
- RateLimitMiddleware: Enforce rate limits across agent executions

Based on LangChain best practices for guardrails and middleware patterns.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Base Middleware
# =============================================================================


class AgentMiddleware(ABC):
    """Abstract base class for agent middleware."""

    @abstractmethod
    async def before_agent(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Hook that runs before agent execution.

        Args:
            state: Current agent state

        Returns:
            Modified state (or original if no changes)
        """
        pass

    @abstractmethod
    async def after_agent(self, state: dict[str, Any], result: Any) -> Any:
        """
        Hook that runs after agent execution.

        Args:
            state: Agent state
            result: Agent execution result

        Returns:
            Modified result (or original if no changes)
        """
        pass


# =============================================================================
# PII Detection Middleware
# =============================================================================


@dataclass
class PIIMatch:
    """Detected PII match information."""

    pii_type: str
    original: str
    redacted: str
    start: int
    end: int


class PIIDetectionMiddleware(AgentMiddleware):
    """
    Detect and scrub PII from logs and outputs.

    Detects common PII patterns:
    - Email addresses
    - Phone numbers (US format)
    - Social Security Numbers
    - Credit card numbers
    - IP addresses

    Usage:
        middleware = PIIDetectionMiddleware()
        state = await middleware.before_agent(state)
        result = await middleware.after_agent(state, result)
    """

    # PII patterns with named groups
    PII_PATTERNS: dict[str, re.Pattern[str]] = {
        "email": re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        ),
        "phone": re.compile(
            r"\b(?:\+1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b"
        ),
        "ssn": re.compile(
            r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b"
        ),
        "credit_card": re.compile(
            r"\b(?:\d{4}[-. ]?){3}\d{4}\b"
        ),
        "ip_address": re.compile(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
        ),
    }

    # Redaction masks by type
    REDACTION_MASKS: dict[str, str] = {
        "email": "[EMAIL_REDACTED]",
        "phone": "[PHONE_REDACTED]",
        "ssn": "[SSN_REDACTED]",
        "credit_card": "[CC_REDACTED]",
        "ip_address": "[IP_REDACTED]",
    }

    def __init__(
        self,
        scrub_logs: bool = True,
        scrub_outputs: bool = False,
        allowed_domains: set[str] | None = None,
    ) -> None:
        """
        Initialize PII detection middleware.

        Args:
            scrub_logs: Whether to scrub PII from log messages
            scrub_outputs: Whether to scrub PII from agent outputs
            allowed_domains: Email domains to allow (e.g., company domains)
        """
        self.scrub_logs = scrub_logs
        self.scrub_outputs = scrub_outputs
        self.allowed_domains = allowed_domains or set()
        self._detection_count: dict[str, int] = dict.fromkeys(self.PII_PATTERNS, 0)

    async def before_agent(self, state: dict[str, Any]) -> dict[str, Any]:
        """Scan state for PII and log warnings."""
        if self.scrub_logs:
            self._scan_for_pii(state, context="state_before")
        return state

    async def after_agent(self, _state: dict[str, Any], result: Any) -> Any:
        """Optionally scrub PII from results."""
        if self.scrub_outputs and isinstance(result, dict):
            return self._scrub_dict(result)
        return result

    def detect_pii(self, text: str) -> list[PIIMatch]:
        """
        Detect all PII in text.

        Args:
            text: Text to scan

        Returns:
            List of PII matches found
        """
        matches: list[PIIMatch] = []

        for pii_type, pattern in self.PII_PATTERNS.items():
            for match in pattern.finditer(text):
                original = match.group()

                # Skip allowed email domains
                if pii_type == "email" and self.allowed_domains:
                    domain = original.split("@")[-1].lower()
                    if domain in self.allowed_domains:
                        continue

                matches.append(
                    PIIMatch(
                        pii_type=pii_type,
                        original=original,
                        redacted=self.REDACTION_MASKS[pii_type],
                        start=match.start(),
                        end=match.end(),
                    )
                )
                self._detection_count[pii_type] += 1

        return matches

    def scrub_text(self, text: str) -> str:
        """
        Scrub all PII from text.

        Args:
            text: Text to scrub

        Returns:
            Text with PII replaced by redaction masks
        """
        result = text
        for pii_type, pattern in self.PII_PATTERNS.items():
            # Skip allowed email domains
            if pii_type == "email" and self.allowed_domains:
                # More complex replacement that checks domain
                def replace_email(m: re.Match[str]) -> str:
                    email = m.group()
                    domain = email.split("@")[-1].lower()
                    if domain in self.allowed_domains:
                        return email
                    return self.REDACTION_MASKS["email"]

                result = pattern.sub(replace_email, result)
            else:
                result = pattern.sub(self.REDACTION_MASKS[pii_type], result)
        return result

    def _scan_for_pii(self, data: Any, context: str = "") -> None:
        """Scan data structure for PII and log warnings."""
        if isinstance(data, str):
            matches = self.detect_pii(data)
            if matches:
                pii_types = {m.pii_type for m in matches}
                logger.warning(
                    f"PII detected in {context}: types={pii_types}, count={len(matches)}"
                )
        elif isinstance(data, dict):
            for key, value in data.items():
                self._scan_for_pii(value, context=f"{context}.{key}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._scan_for_pii(item, context=f"{context}[{i}]")

    def _scrub_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively scrub PII from a dictionary."""
        result: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.scrub_text(value)
            elif isinstance(value, dict):
                result[key] = self._scrub_dict(value)
            elif isinstance(value, list):
                scrubbed_list: list[Any] = []
                for item in value:
                    if isinstance(item, str):
                        scrubbed_list.append(self.scrub_text(item))
                    elif isinstance(item, dict):
                        scrubbed_list.append(self._scrub_dict(item))
                    else:
                        scrubbed_list.append(item)
                result[key] = scrubbed_list
            else:
                result[key] = value
        return result

    def get_detection_stats(self) -> dict[str, int]:
        """Get PII detection statistics."""
        return dict(self._detection_count)

    def reset_stats(self) -> None:
        """Reset detection statistics."""
        self._detection_count = dict.fromkeys(self.PII_PATTERNS, 0)


# =============================================================================
# Dynamic Model Selection Middleware
# =============================================================================


@dataclass
class ModelSelectionResult:
    """Result of model selection decision."""

    model_name: str
    reason: str
    complexity_score: float
    tokens_estimate: int


class DynamicModelMiddleware(AgentMiddleware):
    """
    Select model based on task complexity.

    Routes tasks to appropriate models:
    - Simple lookups → Haiku/Cerebras (fast, cheap)
    - Standard tasks → Sonnet (balanced)
    - Complex reasoning → Opus (most capable)

    Usage:
        middleware = DynamicModelMiddleware()
        state = await middleware.before_agent(state)
        # state["_selected_model"] contains the recommended model
    """

    # Complexity indicators
    COMPLEX_INDICATORS = [
        "analyze",
        "synthesize",
        "compare",
        "evaluate",
        "design",
        "architect",
        "strategy",
        "recommend",
        "complex",
        "multiple",
    ]

    SIMPLE_INDICATORS = [
        "lookup",
        "find",
        "get",
        "fetch",
        "retrieve",
        "list",
        "search",
        "check",
    ]

    # Token thresholds
    TOKEN_THRESHOLD_COMPLEX = 2000
    TOKEN_THRESHOLD_SIMPLE = 500

    def __init__(
        self,
        default_model: str = "sonnet",
        fast_model: str = "haiku",
        powerful_model: str = "opus",
    ) -> None:
        """
        Initialize model selection middleware.

        Args:
            default_model: Default model for standard tasks
            fast_model: Fast model for simple lookups
            powerful_model: Powerful model for complex reasoning
        """
        self.default_model = default_model
        self.fast_model = fast_model
        self.powerful_model = powerful_model
        self._selection_history: list[ModelSelectionResult] = []

    async def before_agent(self, state: dict[str, Any]) -> dict[str, Any]:
        """Analyze state and select appropriate model."""
        selection = self._select_model(state)
        self._selection_history.append(selection)

        # Add model selection to state
        state["_selected_model"] = selection.model_name
        state["_model_selection_reason"] = selection.reason

        logger.debug(
            f"Model selected: {selection.model_name} "
            f"(complexity={selection.complexity_score:.2f}, reason={selection.reason})"
        )

        return state

    async def after_agent(self, _state: dict[str, Any], result: Any) -> Any:
        """No modification on output."""
        return result

    def _select_model(self, state: dict[str, Any]) -> ModelSelectionResult:
        """Analyze state and select appropriate model."""
        # Extract text content for analysis
        text_content = self._extract_text_content(state)
        tokens_estimate = self._estimate_tokens(text_content)
        complexity_score = self._calculate_complexity(text_content)

        # Decision logic
        if complexity_score < 0.3 and tokens_estimate < self.TOKEN_THRESHOLD_SIMPLE:
            return ModelSelectionResult(
                model_name=self.fast_model,
                reason="simple_task",
                complexity_score=complexity_score,
                tokens_estimate=tokens_estimate,
            )
        elif complexity_score > 0.7 or tokens_estimate > self.TOKEN_THRESHOLD_COMPLEX:
            return ModelSelectionResult(
                model_name=self.powerful_model,
                reason="complex_task",
                complexity_score=complexity_score,
                tokens_estimate=tokens_estimate,
            )
        else:
            return ModelSelectionResult(
                model_name=self.default_model,
                reason="standard_task",
                complexity_score=complexity_score,
                tokens_estimate=tokens_estimate,
            )

    def _extract_text_content(self, state: dict[str, Any]) -> str:
        """Extract text content from state for analysis."""
        text_parts = []

        # Common state fields that contain text
        text_fields = ["context", "query", "prompt", "input", "message", "content"]

        for key, value in state.items():
            if key in text_fields and isinstance(value, str):
                text_parts.append(value)

        return " ".join(text_parts)

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of token count (words * 1.3)."""
        word_count = len(text.split())
        return int(word_count * 1.3)

    def _calculate_complexity(self, text: str) -> float:
        """
        Calculate complexity score (0.0-1.0).

        Based on:
        - Presence of complexity indicators
        - Text length
        - Question complexity
        """
        text_lower = text.lower()

        # Count complexity indicators
        complex_count = sum(
            1 for indicator in self.COMPLEX_INDICATORS
            if indicator in text_lower
        )
        simple_count = sum(
            1 for indicator in self.SIMPLE_INDICATORS
            if indicator in text_lower
        )

        # Base score from indicators
        indicator_score = (complex_count - simple_count) / max(
            1, complex_count + simple_count
        )
        # Normalize to 0-1
        indicator_score = (indicator_score + 1) / 2

        # Length factor (longer = more complex)
        length_factor = min(1.0, len(text) / 2000)

        # Combine factors
        complexity = (indicator_score * 0.7) + (length_factor * 0.3)

        return min(1.0, max(0.0, complexity))

    def get_selection_history(self) -> list[ModelSelectionResult]:
        """Get model selection history."""
        return list(self._selection_history)

    def clear_history(self) -> None:
        """Clear selection history."""
        self._selection_history = []


# =============================================================================
# Rate Limit Middleware
# =============================================================================


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""

    tokens: float
    last_update: datetime
    max_tokens: float
    refill_rate: float  # tokens per second

    def consume(self, amount: float = 1.0) -> bool:
        """
        Attempt to consume tokens.

        Args:
            amount: Number of tokens to consume

        Returns:
            True if tokens consumed, False if rate limited
        """
        self._refill()
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on time elapsed."""
        now = datetime.now(timezone.utc)
        elapsed = (now - self.last_update).total_seconds()
        self.tokens = min(
            self.max_tokens,
            self.tokens + (elapsed * self.refill_rate)
        )
        self.last_update = now


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10


class RateLimitMiddleware(AgentMiddleware):
    """
    Enforce rate limits across agent executions.

    Uses token bucket algorithm for smooth rate limiting.

    Usage:
        middleware = RateLimitMiddleware(config=RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000,
        ))
        state = await middleware.before_agent(state)  # May raise RateLimitError
    """

    def __init__(
        self,
        config: RateLimitConfig | None = None,
    ) -> None:
        """
        Initialize rate limit middleware.

        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()

        # Initialize buckets
        self._minute_bucket = RateLimitBucket(
            tokens=float(self.config.burst_size),
            last_update=datetime.now(timezone.utc),
            max_tokens=float(self.config.burst_size),
            refill_rate=self.config.requests_per_minute / 60.0,
        )
        self._hour_bucket = RateLimitBucket(
            tokens=float(self.config.requests_per_hour),
            last_update=datetime.now(timezone.utc),
            max_tokens=float(self.config.requests_per_hour),
            refill_rate=self.config.requests_per_hour / 3600.0,
        )

        self._rate_limited_count = 0
        self._total_requests = 0

    async def before_agent(self, state: dict[str, Any]) -> dict[str, Any]:
        """Check rate limits before execution."""
        self._total_requests += 1

        # Check minute bucket
        if not self._minute_bucket.consume():
            self._rate_limited_count += 1
            state["_rate_limited"] = True
            state["_rate_limit_reason"] = "minute_limit_exceeded"
            logger.warning(
                f"Rate limit exceeded (minute): "
                f"{self._rate_limited_count}/{self._total_requests} requests limited"
            )
            return state

        # Check hour bucket
        if not self._hour_bucket.consume():
            self._rate_limited_count += 1
            state["_rate_limited"] = True
            state["_rate_limit_reason"] = "hour_limit_exceeded"
            logger.warning(
                f"Rate limit exceeded (hour): "
                f"{self._rate_limited_count}/{self._total_requests} requests limited"
            )
            return state

        state["_rate_limited"] = False
        return state

    async def after_agent(self, _state: dict[str, Any], result: Any) -> Any:
        """No modification on output."""
        return result

    def get_remaining_tokens(self) -> dict[str, float]:
        """Get remaining rate limit tokens."""
        return {
            "minute": self._minute_bucket.tokens,
            "hour": self._hour_bucket.tokens,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiting statistics."""
        return {
            "total_requests": self._total_requests,
            "rate_limited_count": self._rate_limited_count,
            "rate_limited_percentage": (
                self._rate_limited_count / max(1, self._total_requests) * 100
            ),
            "remaining_minute": self._minute_bucket.tokens,
            "remaining_hour": self._hour_bucket.tokens,
        }

    def reset(self) -> None:
        """Reset rate limit buckets and stats."""
        now = datetime.now(timezone.utc)
        self._minute_bucket.tokens = float(self.config.burst_size)
        self._minute_bucket.last_update = now
        self._hour_bucket.tokens = float(self.config.requests_per_hour)
        self._hour_bucket.last_update = now
        self._rate_limited_count = 0
        self._total_requests = 0


# =============================================================================
# Model Call Limit Middleware
# =============================================================================


class ModelCallLimitError(Exception):
    """Raised when model call limit is exceeded."""

    def __init__(self, limit_type: str, count: int, limit: int) -> None:
        self.limit_type = limit_type
        self.count = count
        self.limit = limit
        super().__init__(
            f"Model call limit exceeded: {limit_type} "
            f"({count}/{limit} calls)"
        )


@dataclass
class CallLimitStats:
    """Statistics for model call limiting."""

    thread_calls: int = 0
    run_calls: int = 0
    limit_errors: int = 0


class ModelCallLimitMiddleware(AgentMiddleware):
    """
    Prevent runaway costs by limiting model calls.

    Enforces limits at two levels:
    - Per-thread: Limits total calls across an entire conversation
    - Per-run: Limits calls within a single agent invocation

    This is a defensive measure against infinite loops and
    misconfigured agent graphs.

    Usage:
        middleware = ModelCallLimitMiddleware(
            thread_limit=50,  # Max calls per conversation
            run_limit=20,     # Max calls per single run
        )
        state = await middleware.before_agent(state)  # May raise ModelCallLimitError
    """

    def __init__(
        self,
        thread_limit: int = 50,
        run_limit: int = 20,
    ) -> None:
        """
        Initialize model call limit middleware.

        Args:
            thread_limit: Maximum model calls per thread/conversation
            run_limit: Maximum model calls per single agent run
        """
        self.thread_limit = thread_limit
        self.run_limit = run_limit

        # Track calls by thread_id
        self._thread_counts: dict[str, int] = {}
        self._current_run_count = 0
        self._stats = CallLimitStats()

    async def before_agent(self, state: dict[str, Any]) -> dict[str, Any]:
        """Check and increment call counts before execution."""
        thread_id = state.get("_thread_id", "default")

        # Increment counts
        self._current_run_count += 1
        self._thread_counts[thread_id] = self._thread_counts.get(thread_id, 0) + 1

        # Update stats
        self._stats.thread_calls = self._thread_counts[thread_id]
        self._stats.run_calls = self._current_run_count

        # Check run limit
        if self._current_run_count > self.run_limit:
            self._stats.limit_errors += 1
            logger.error(
                f"Run call limit exceeded: {self._current_run_count}/{self.run_limit}"
            )
            raise ModelCallLimitError(
                "run", self._current_run_count, self.run_limit
            )

        # Check thread limit
        if self._thread_counts[thread_id] > self.thread_limit:
            self._stats.limit_errors += 1
            logger.error(
                f"Thread call limit exceeded: "
                f"{self._thread_counts[thread_id]}/{self.thread_limit}"
            )
            raise ModelCallLimitError(
                "thread", self._thread_counts[thread_id], self.thread_limit
            )

        # Add current counts to state for observability
        state["_model_call_count"] = self._current_run_count
        state["_thread_call_count"] = self._thread_counts[thread_id]

        return state

    async def after_agent(self, _state: dict[str, Any], result: Any) -> Any:
        """No modification on output."""
        return result

    def reset_run(self) -> None:
        """Reset run counter (call between agent invocations)."""
        self._current_run_count = 0

    def reset_thread(self, thread_id: str) -> None:
        """Reset counter for a specific thread."""
        if thread_id in self._thread_counts:
            del self._thread_counts[thread_id]

    def reset_all(self) -> None:
        """Reset all counters."""
        self._thread_counts.clear()
        self._current_run_count = 0

    def get_stats(self) -> CallLimitStats:
        """Get call limit statistics."""
        return self._stats


# =============================================================================
# Model Fallback Middleware
# =============================================================================


@dataclass
class FallbackAttempt:
    """Record of a fallback attempt."""

    timestamp: datetime
    primary_error: str
    fallback_model: str
    success: bool


class ModelFallbackMiddleware(AgentMiddleware):
    """
    Fallback to secondary model on primary model failure.

    Provides multi-provider redundancy by catching primary model
    errors and attempting the request with a fallback model.

    Usage:
        middleware = ModelFallbackMiddleware(
            fallback_model="openrouter",
            max_fallback_attempts=3,
        )
        state = await middleware.before_agent(state)
        # If primary fails, state["_use_fallback"] will be True
    """

    def __init__(
        self,
        fallback_model: str = "openrouter",
        max_fallback_attempts: int = 3,
        retry_on_errors: tuple[type[Exception], ...] | None = None,
    ) -> None:
        """
        Initialize model fallback middleware.

        Args:
            fallback_model: Name of fallback model to use
            max_fallback_attempts: Maximum fallback attempts per run
            retry_on_errors: Exception types that trigger fallback
        """
        self.fallback_model = fallback_model
        self.max_fallback_attempts = max_fallback_attempts
        self.retry_on_errors = retry_on_errors or (
            TimeoutError,
            ConnectionError,
        )

        self._fallback_count = 0
        self._attempts: list[FallbackAttempt] = []

    async def before_agent(self, state: dict[str, Any]) -> dict[str, Any]:
        """Check if fallback is needed based on previous errors."""
        # Check if we should use fallback from previous failure
        last_error = state.get("_last_model_error")
        if last_error and self._fallback_count < self.max_fallback_attempts:
            state["_use_fallback"] = True
            state["_fallback_model"] = self.fallback_model
            state["_fallback_reason"] = last_error
            self._fallback_count += 1
            logger.info(
                f"Using fallback model {self.fallback_model} due to: {last_error}"
            )
        else:
            state["_use_fallback"] = False

        return state

    async def after_agent(self, state: dict[str, Any], result: Any) -> Any:
        """Record fallback result."""
        if state.get("_use_fallback"):
            # Check if result indicates success
            success = not isinstance(result, Exception)
            self._attempts.append(
                FallbackAttempt(
                    timestamp=datetime.now(timezone.utc),
                    primary_error=state.get("_fallback_reason", "unknown"),
                    fallback_model=self.fallback_model,
                    success=success,
                )
            )
        return result

    def record_primary_error(self, state: dict[str, Any], error: str) -> dict[str, Any]:
        """
        Record a primary model error to trigger fallback on next call.

        Call this when catching a model error:
            state = middleware.record_primary_error(state, str(error))

        Args:
            state: Current agent state
            error: Error message from primary model

        Returns:
            Updated state with error recorded
        """
        state["_last_model_error"] = error
        return state

    def reset(self) -> None:
        """Reset fallback counter."""
        self._fallback_count = 0

    def get_attempts(self) -> list[FallbackAttempt]:
        """Get fallback attempt history."""
        return list(self._attempts)

    def get_stats(self) -> dict[str, Any]:
        """Get fallback statistics."""
        total = len(self._attempts)
        successful = sum(1 for a in self._attempts if a.success)
        return {
            "total_fallbacks": total,
            "successful_fallbacks": successful,
            "success_rate": successful / max(1, total),
            "current_fallback_count": self._fallback_count,
        }


# =============================================================================
# Middleware Pipeline
# =============================================================================


class MiddlewarePipeline:
    """
    Pipeline for executing multiple middleware in order.

    Usage:
        pipeline = MiddlewarePipeline([
            PIIDetectionMiddleware(),
            DynamicModelMiddleware(),
            RateLimitMiddleware(),
        ])
        state = await pipeline.run_before(state)
        # ... execute agent ...
        result = await pipeline.run_after(state, result)
    """

    def __init__(self, middlewares: list[AgentMiddleware] | None = None) -> None:
        """
        Initialize middleware pipeline.

        Args:
            middlewares: List of middleware to execute in order
        """
        self.middlewares = middlewares or []

    def add(self, middleware: AgentMiddleware) -> "MiddlewarePipeline":
        """Add middleware to pipeline (returns self for chaining)."""
        self.middlewares.append(middleware)
        return self

    async def run_before(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run all before_agent hooks in order."""
        current_state = state
        for middleware in self.middlewares:
            current_state = await middleware.before_agent(current_state)
        return current_state

    async def run_after(self, state: dict[str, Any], result: Any) -> Any:
        """Run all after_agent hooks in reverse order."""
        current_result = result
        for middleware in reversed(self.middlewares):
            current_result = await middleware.after_agent(state, current_result)
        return current_result


# =============================================================================
# Default Pipeline Factory
# =============================================================================


def create_default_pipeline(
    scrub_pii_outputs: bool = False,
    allowed_email_domains: set[str] | None = None,
    rate_limit_config: RateLimitConfig | None = None,
    enable_call_limits: bool = True,
    thread_call_limit: int = 50,
    run_call_limit: int = 20,
    enable_fallback: bool = True,
    fallback_model: str = "openrouter",
) -> MiddlewarePipeline:
    """
    Create default middleware pipeline.

    Args:
        scrub_pii_outputs: Whether to scrub PII from outputs
        allowed_email_domains: Email domains to allow in PII detection
        rate_limit_config: Rate limit configuration
        enable_call_limits: Whether to enable model call limiting
        thread_call_limit: Max model calls per thread
        run_call_limit: Max model calls per run
        enable_fallback: Whether to enable model fallback
        fallback_model: Fallback model name

    Returns:
        Configured middleware pipeline
    """
    middlewares: list[AgentMiddleware] = [
        PIIDetectionMiddleware(
            scrub_outputs=scrub_pii_outputs,
            allowed_domains=allowed_email_domains,
        ),
        DynamicModelMiddleware(),
        RateLimitMiddleware(config=rate_limit_config),
    ]

    if enable_call_limits:
        middlewares.append(
            ModelCallLimitMiddleware(
                thread_limit=thread_call_limit,
                run_limit=run_call_limit,
            )
        )

    if enable_fallback:
        middlewares.append(
            ModelFallbackMiddleware(fallback_model=fallback_model)
        )

    return MiddlewarePipeline(middlewares)
