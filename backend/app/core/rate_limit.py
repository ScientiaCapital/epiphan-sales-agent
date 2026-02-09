"""Rate limiting configuration using slowapi.

Provides user-based rate limiting for API endpoints. Extracts user identity
from JWT 'sub' claim when available, falls back to client IP for
unauthenticated endpoints (webhooks, health).

Tier limits:
- AGENT_RATE_LIMIT: 10/min — LLM-powered endpoints (expensive)
- WRITE_RATE_LIMIT: 20/min — Database write operations
- READ_RATE_LIMIT: 60/min — Read-only / monitoring endpoints
- DEFAULT_RATE_LIMIT: 100/min — Fallback for undecorated endpoints
"""

import contextlib
from typing import Any, cast

import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import Response

from app.core.config import settings

__all__ = [
    "AGENT_RATE_LIMIT",
    "DEFAULT_RATE_LIMIT",
    "READ_RATE_LIMIT",
    "WRITE_RATE_LIMIT",
    "limiter",
    "rate_limit_exceeded_handler",
    "setup_rate_limiting",
]


def _get_user_or_ip(request: Request) -> str:
    """Extract rate-limit key: JWT sub claim if present, else client IP.

    Parses the Authorization header directly (no dependency injection needed)
    so that rate limiting works as middleware before endpoint handlers run.
    Falls back to IP for unauthenticated requests (webhooks, health).
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        with contextlib.suppress(jwt.InvalidTokenError):
            payload: dict[str, Any] = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
    return get_remote_address(request)


# Global limiter instance keyed by user identity or IP
limiter = Limiter(key_func=_get_user_or_ip)

# Tiered rate limits
AGENT_RATE_LIMIT = "10/minute"   # LLM calls: expensive, slow
WRITE_RATE_LIMIT = "20/minute"   # DB writes: moderate cost
READ_RATE_LIMIT = "60/minute"    # Reads: lightweight
DEFAULT_RATE_LIMIT = "100/minute"  # Fallback


def rate_limit_exceeded_handler(
    request: Request,  # noqa: ARG001 - required by FastAPI exception handler signature
    exc: Exception,  # noqa: ARG001 - required by FastAPI exception handler signature
) -> Response:
    """Custom handler for rate limit exceeded errors.

    Returns a JSON response with 429 status code and descriptive message.
    """
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please retry after a short wait."},
    )


def setup_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting middleware and exception handler.

    Call this after FastAPI app creation to enable rate limiting:

        app = FastAPI(...)
        setup_rate_limiting(app)

    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        cast(Any, rate_limit_exceeded_handler),  # Type narrowing for slowapi handler
    )
    app.add_middleware(SlowAPIMiddleware)
