"""JWT authentication middleware for API protection.

Provides:
- create_access_token: Issue JWTs for authenticated users
- get_current_user: Decode and validate JWT tokens
- require_auth: FastAPI dependency for protected routes (extracts Bearer token)
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

# Bearer token scheme — auto-extracts from Authorization header
_bearer_scheme = HTTPBearer(auto_error=True)


def create_access_token(
    subject: str,
    role: str = "bdr",
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        subject: User identifier (stored as 'sub' claim).
        role: User role (default: 'bdr').
        expires_delta: Custom token lifetime. Defaults to settings value.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token, returning user claims.

    Args:
        token: Raw JWT string.

    Returns:
        Dict with 'sub', 'role', and other claims.

    Raises:
        HTTPException: 401 if token is invalid, expired, or missing required claims.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError:
        raise credentials_exception from None

    if "sub" not in payload or not payload["sub"]:
        raise credentials_exception

    return payload


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),  # noqa: B008
) -> dict[str, Any]:
    """FastAPI dependency that extracts and validates Bearer token.

    Usage:
        @app.get("/protected")
        async def protected(user: dict = Depends(require_auth)):
            return {"user": user["sub"]}
    """
    return await get_current_user(token=credentials.credentials)
