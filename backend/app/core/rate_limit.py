"""Rate limiting configuration using slowapi.

Provides IP-based rate limiting for API endpoints.
Default: 100 requests per minute per IP address.
"""

from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import Response

__all__ = [
    "limiter",
    "DEFAULT_RATE_LIMIT",
    "rate_limit_exceeded_handler",
    "setup_rate_limiting",
]

# Global limiter instance keyed by client IP
limiter = Limiter(key_func=get_remote_address)

# Default rate limit: 100 requests per minute
DEFAULT_RATE_LIMIT = "100/minute"


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
