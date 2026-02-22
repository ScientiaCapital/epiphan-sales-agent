"""Tests for JWT authentication middleware.

Tests cover:
- Token creation and validation
- Missing/invalid/expired token handling
- Public route bypass (health, docs)
- Protected route access with valid token
- get_current_user dependency
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

import jwt
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.middleware.auth import (
    create_access_token,
    get_current_user,
    require_auth,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_SECRET = "test-secret-key-for-jwt-testing-minimum-32-chars"
TEST_API_KEY = "test-api-key-separate-from-jwt-secret-value"
TEST_ALGORITHM = "HS256"


def _make_token(
    subject: str = "test-user",
    role: str = "bdr",
    expires_delta: timedelta | None = None,
    secret: str = TEST_SECRET,
) -> str:
    """Helper to create a JWT token for testing."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=15))
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, secret, algorithm=TEST_ALGORITHM)


@pytest.fixture
def _auth_settings():
    """Patch settings for auth testing."""
    with (
        patch("app.middleware.auth.settings") as mock_settings,
        patch("app.api.routes.auth.settings", mock_settings),
    ):
        mock_settings.jwt_secret_key = TEST_SECRET
        mock_settings.epiphan_api_key = TEST_API_KEY
        mock_settings.jwt_algorithm = TEST_ALGORITHM
        mock_settings.jwt_access_token_expire_minutes = 15
        yield mock_settings


# ---------------------------------------------------------------------------
# Token Creation Tests
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    """Tests for create_access_token function."""

    def test_creates_valid_jwt(self, _auth_settings: None) -> None:
        """Token should be decodable with the same secret."""
        token = create_access_token(subject="tim", role="bdr")
        decoded = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        assert decoded["sub"] == "tim"
        assert decoded["role"] == "bdr"

    def test_includes_expiry(self, _auth_settings: None) -> None:
        """Token should have an expiration claim."""
        token = create_access_token(subject="tim")
        decoded = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        assert "exp" in decoded

    def test_custom_expiry(self, _auth_settings: None) -> None:
        """Token should respect custom expiry duration."""
        token = create_access_token(
            subject="tim",
            expires_delta=timedelta(minutes=5),
        )
        decoded = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        # exp should be ~5 min from now, not 15
        exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = exp - now
        assert 4 * 60 <= delta.total_seconds() <= 5 * 60 + 5

    def test_default_role_is_bdr(self, _auth_settings: None) -> None:
        """Default role should be 'bdr' since that's our primary user."""
        token = create_access_token(subject="tim")
        decoded = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        assert decoded["role"] == "bdr"


# ---------------------------------------------------------------------------
# Token Validation Tests (get_current_user dependency)
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, _auth_settings: None) -> None:
        """Valid JWT should return user dict with sub and role."""
        token = _make_token()
        user = await get_current_user(token=token)
        assert user["sub"] == "test-user"
        assert user["role"] == "bdr"

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self, _auth_settings: None) -> None:
        """Expired JWT should raise HTTPException 401."""
        token = _make_token(expires_delta=timedelta(seconds=-1))
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token)
        assert exc_info.value.status_code == 401
        assert "expired" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, _auth_settings: None) -> None:
        """Malformed JWT should raise HTTPException 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="not-a-valid-jwt")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret_raises_401(self, _auth_settings: None) -> None:
        """JWT signed with wrong secret should raise HTTPException 401."""
        token = _make_token(secret="wrong-secret-key-that-doesnt-match!!")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_sub_claim_raises_401(self, _auth_settings: None) -> None:
        """JWT without 'sub' claim should raise HTTPException 401."""
        payload: dict[str, Any] = {
            "role": "bdr",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        }
        token = jwt.encode(payload, TEST_SECRET, algorithm=TEST_ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_token_raises_401(self, _auth_settings: None) -> None:
        """Empty string token should raise HTTPException 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="")
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# API Integration Tests (protected vs public routes)
# ---------------------------------------------------------------------------


class TestAuthIntegration:
    """Integration tests for auth with FastAPI endpoints."""

    @pytest.fixture
    def app_with_auth(self, _auth_settings: None) -> FastAPI:
        """Create a minimal FastAPI app with auth-protected routes."""
        app = FastAPI()

        @app.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "healthy"}

        @app.get("/protected")
        async def protected(
            user: dict[str, str] = Depends(require_auth),  # noqa: B008
        ) -> dict[str, str]:
            return {"user": user["sub"]}

        return app

    @pytest.fixture
    def client(self, app_with_auth: FastAPI) -> TestClient:
        return TestClient(app_with_auth)

    def test_health_no_auth_required(self, client: TestClient) -> None:
        """Health endpoint should work without any auth header."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_protected_without_token_returns_401(self, client: TestClient) -> None:
        """Protected route without Authorization header should return 401."""
        response = client.get("/protected")
        assert response.status_code == 401 or response.status_code == 403

    def test_protected_with_invalid_scheme_returns_401(self, client: TestClient) -> None:
        """Protected route with non-Bearer scheme should return 401."""
        response = client.get(
            "/protected",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert response.status_code == 401 or response.status_code == 403

    def test_protected_with_valid_token_returns_200(self, client: TestClient) -> None:
        """Protected route with valid Bearer token should return 200."""
        token = _make_token()
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["user"] == "test-user"

    def test_protected_with_expired_token_returns_401(self, client: TestClient) -> None:
        """Protected route with expired token should return 401."""
        token = _make_token(expires_delta=timedelta(seconds=-1))
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Auth Token Endpoint Tests
# ---------------------------------------------------------------------------


class TestAuthTokenEndpoint:
    """Tests for the POST /api/auth/token endpoint."""

    @pytest.fixture
    def auth_client(self, _auth_settings: None) -> TestClient:
        """Create a test client with the auth router."""
        from app.api.routes.auth import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_issue_token_with_valid_credentials(self, auth_client: TestClient) -> None:
        """Should return a JWT when given valid API key."""
        response = auth_client.post(
            "/api/auth/token",
            json={"api_key": TEST_API_KEY, "user_id": "tim"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_issue_token_without_api_key_returns_422(self, auth_client: TestClient) -> None:
        """Should reject requests without api_key."""
        response = auth_client.post(
            "/api/auth/token",
            json={"user_id": "tim"},
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_issue_token_with_wrong_api_key_returns_401(self, auth_client: TestClient) -> None:
        """Should reject requests with invalid api_key."""
        response = auth_client.post(
            "/api/auth/token",
            json={"api_key": "wrong-key", "user_id": "tim"},
        )
        assert response.status_code == 401

    def test_issued_token_is_valid(self, auth_client: TestClient) -> None:
        """Token returned by endpoint should be decodable."""
        response = auth_client.post(
            "/api/auth/token",
            json={"api_key": TEST_API_KEY, "user_id": "tim"},
        )
        token = response.json()["access_token"]
        decoded = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        assert decoded["sub"] == "tim"

    def test_jwt_secret_rejected_as_api_key(self, auth_client: TestClient) -> None:
        """JWT secret should NOT work as API key (they are separate now)."""
        response = auth_client.post(
            "/api/auth/token",
            json={"api_key": TEST_SECRET, "user_id": "tim"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Startup Secret Validation Tests
# ---------------------------------------------------------------------------


class TestStartupSecretValidation:
    """Tests for _validate_production_secrets() startup guard."""

    def test_production_default_jwt_secret_raises(self) -> None:
        """Production with default JWT secret should crash."""
        with patch("app.main.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.jwt_secret_key = "change-me-in-production"
            mock_settings.epiphan_api_key = "some-valid-api-key"

            from app.main import _validate_production_secrets

            with pytest.raises(SystemExit, match="JWT_SECRET_KEY is still the default"):
                _validate_production_secrets()

    def test_production_empty_api_key_raises(self) -> None:
        """Production with empty API key should crash."""
        with patch("app.main.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.jwt_secret_key = "a-real-production-secret-key"
            mock_settings.epiphan_api_key = ""

            from app.main import _validate_production_secrets

            with pytest.raises(SystemExit, match="EPIPHAN_API_KEY is not set"):
                _validate_production_secrets()

    def test_production_jwt_equals_api_key_raises(self) -> None:
        """Production with JWT == API key should crash (defeats the purpose)."""
        with patch("app.main.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.jwt_secret_key = "same-secret-for-both"
            mock_settings.epiphan_api_key = "same-secret-for-both"

            from app.main import _validate_production_secrets

            with pytest.raises(SystemExit, match="must be different"):
                _validate_production_secrets()

    def test_production_all_valid_passes(self) -> None:
        """Production with proper secrets should not raise."""
        with patch("app.main.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.jwt_secret_key = "a-real-jwt-secret-key-for-signing"
            mock_settings.epiphan_api_key = "a-separate-api-key-for-exchange"

            from app.main import _validate_production_secrets

            _validate_production_secrets()  # Should not raise

    def test_development_default_jwt_secret_allowed(self) -> None:
        """Development env should allow default JWT secret."""
        with patch("app.main.settings") as mock_settings:
            mock_settings.environment = "development"
            mock_settings.jwt_secret_key = "change-me-in-production"
            mock_settings.epiphan_api_key = ""

            from app.main import _validate_production_secrets

            _validate_production_secrets()  # Should not raise

    def test_staging_default_jwt_secret_allowed(self) -> None:
        """Staging env should allow default JWT secret (only production is strict)."""
        with patch("app.main.settings") as mock_settings:
            mock_settings.environment = "staging"
            mock_settings.jwt_secret_key = "change-me-in-production"
            mock_settings.epiphan_api_key = ""

            from app.main import _validate_production_secrets

            _validate_production_secrets()  # Should not raise

    def test_production_multiple_errors_all_listed(self) -> None:
        """All errors should be reported at once, not fail-fast."""
        with patch("app.main.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.jwt_secret_key = "change-me-in-production"
            mock_settings.epiphan_api_key = ""

            from app.main import _validate_production_secrets

            with pytest.raises(SystemExit) as exc_info:
                _validate_production_secrets()

            message = str(exc_info.value)
            assert "JWT_SECRET_KEY is still the default" in message
            assert "EPIPHAN_API_KEY is not set" in message

    def test_production_jwt_equals_api_key_not_triggered_when_api_key_empty(self) -> None:
        """Empty API key should NOT trigger the 'must be different' check."""
        with patch("app.main.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.jwt_secret_key = "a-real-secret"
            mock_settings.epiphan_api_key = ""

            from app.main import _validate_production_secrets

            with pytest.raises(SystemExit) as exc_info:
                _validate_production_secrets()

            message = str(exc_info.value)
            assert "EPIPHAN_API_KEY is not set" in message
            assert "must be different" not in message
