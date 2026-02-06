"""Authentication endpoints for token issuance.

Provides a simple API key exchange for JWT tokens.
In production, this would be replaced by SSO/OAuth integration.
"""

import hmac

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.middleware.auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenRequest(BaseModel):
    """Request body for token issuance."""

    api_key: str
    user_id: str
    role: str = "bdr"


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/token", response_model=TokenResponse)
async def issue_token(request: TokenRequest) -> TokenResponse:
    """Issue a JWT access token in exchange for a valid API key.

    For development/testing. Production should use SSO/OAuth.
    """
    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(request.api_key, settings.jwt_secret_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    token = create_access_token(subject=request.user_id, role=request.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )
