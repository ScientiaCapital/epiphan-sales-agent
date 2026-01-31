"""Cache utilities for API responses.

Provides helpers for adding Cache-Control headers to API responses.
Uses in-memory caching via functools.lru_cache where needed.
"""

from collections.abc import Sequence
from typing import Any, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel

__all__ = [
    "DEFAULT_MAX_AGE",
    "with_cache_headers",
]

# 24 hours default cache duration (static reference data)
DEFAULT_MAX_AGE = 86400

T = TypeVar("T", bound=BaseModel)


def with_cache_headers(
    data: BaseModel | Sequence[BaseModel],
    max_age: int = DEFAULT_MAX_AGE,
) -> JSONResponse:
    """Wrap response data with Cache-Control headers.

    Args:
        data: Pydantic model or list of models to serialize
        max_age: Cache duration in seconds (default 24 hours)

    Returns:
        JSONResponse with Cache-Control header set

    Example:
        @router.get("/personas")
        async def list_personas() -> JSONResponse:
            return with_cache_headers(PERSONAS)
    """
    content: list[dict[str, Any]] | dict[str, Any]
    if isinstance(data, BaseModel):
        content = data.model_dump(mode="json")
    else:
        # Sequence of models
        content = [item.model_dump(mode="json") for item in data]

    return JSONResponse(
        content=content,
        headers={"Cache-Control": f"public, max-age={max_age}"},
    )
