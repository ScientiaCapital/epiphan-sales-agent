"""
Shared pytest fixtures and configuration.

This file is automatically loaded by pytest. Fixtures defined here
are available to all tests without explicit imports.

Key concepts:
- Fixtures provide test dependencies (db connections, test data, mocks)
- Scope controls how often fixtures are created (function/class/module/session)
- yield fixtures allow cleanup after tests complete
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

# =============================================================================
# Database Fixtures (example for Supabase/PostgreSQL)
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the test session.
    
    scope="session" means ONE loop for ALL tests - faster but be careful
    about test isolation. Use scope="function" if tests need isolation.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_db() -> AsyncGenerator[MagicMock, None]:
    """
    Mock database connection for unit tests.
    
    Use this when you want to test logic WITHOUT hitting a real database.
    For integration tests, use a real test database instead.
    """
    db = MagicMock()
    db.execute = AsyncMock(return_value=[])
    db.fetch_one = AsyncMock(return_value=None)
    db.fetch_all = AsyncMock(return_value=[])

    yield db


@pytest.fixture
async def test_db_connection() -> AsyncGenerator[Any, None]:
    """
    Real database connection for integration tests.
    
    Uses a separate test database that gets cleaned up after each test.
    Configure via TEST_DATABASE_URL environment variable.
    
    Example:
        async def test_create_lead(test_db_connection):
            result = await create_lead(test_db_connection, lead_data)
            assert result.id is not None
    """
    # In real implementation, you'd connect to your test database here
    # Example with asyncpg:
    #
    # import asyncpg
    # conn = await asyncpg.connect(os.getenv("TEST_DATABASE_URL"))
    # yield conn
    # await conn.close()

    # For now, yield a mock - replace with real connection
    yield MagicMock()


# =============================================================================
# HTTP Client Fixtures (for API testing)
# =============================================================================

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for testing FastAPI endpoints.
    
    Example usage with FastAPI:
        from your_app.main import app
        
        @pytest.fixture
        async def client() -> AsyncGenerator[AsyncClient, None]:
            async with AsyncClient(app=app, base_url="http://test") as client:
                yield client
        
        async def test_health_check(client):
            response = await client.get("/health")
            assert response.status_code == 200
    """
    async with AsyncClient(base_url="http://test") as client:
        yield client


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_lead() -> dict[str, Any]:
    """
    Sample lead data for testing.
    
    Use fixtures for test data instead of hardcoding in tests.
    This makes tests more readable and data easier to maintain.
    """
    return {
        "company_name": "Acme HVAC Services",
        "contact_name": "John Smith",
        "email": "john@acmehvac.com",
        "phone": "555-123-4567",
        "trade": "hvac",
        "employee_count": 25,
        "annual_revenue": 2_500_000,
        "source": "dealer_scraper",
    }


@pytest.fixture
def sample_leads(sample_lead: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Multiple sample leads for batch testing.
    
    Notice how this fixture DEPENDS on sample_lead fixture.
    Pytest handles the dependency injection automatically.
    """
    trades = ["hvac", "electrical", "plumbing", "solar"]
    return [
        {**sample_lead, "company_name": f"Test Company {i}", "trade": trades[i % 4]}
        for i in range(10)
    ]


# =============================================================================
# Mock External Services
# =============================================================================

@pytest.fixture
def mock_llm_client() -> MagicMock:
    """
    Mock LLM client to avoid API calls during testing.
    
    Real LLM calls are:
    - Slow (adds seconds to every test)
    - Expensive (costs money per call)
    - Non-deterministic (responses vary)
    
    Always mock LLM calls in unit tests.
    """
    client = MagicMock()
    client.chat = AsyncMock(
        return_value={
            "content": "This is a mock LLM response for testing.",
            "model": "mock-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
    )
    return client


@pytest.fixture
def mock_enrichment_api() -> MagicMock:
    """
    Mock external enrichment API (e.g., Clearbit, Apollo).
    
    External APIs should ALWAYS be mocked in tests because:
    - They might be down
    - They have rate limits
    - They cost money
    - They're slow
    """
    api = MagicMock()
    api.enrich_company = AsyncMock(
        return_value={
            "name": "Acme HVAC Services",
            "industry": "Construction",
            "employee_count": 25,
            "linkedin_url": "https://linkedin.com/company/acme-hvac",
            "technologies": ["QuickBooks", "ServiceTitan"],
        }
    )
    return api


# =============================================================================
# Environment & Configuration
# =============================================================================

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Set up test environment variables.
    
    autouse=True means this runs for EVERY test automatically.
    Use monkeypatch to set env vars - they reset after each test.
    """
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test_db")


# =============================================================================
# Cleanup Utilities
# =============================================================================

@pytest.fixture
def temp_file(tmp_path) -> Generator[Any, None, None]:
    """
    Create a temporary file that's automatically cleaned up.
    
    tmp_path is a built-in pytest fixture that provides a temp directory
    unique to each test invocation.
    """
    file_path = tmp_path / "test_file.json"
    file_path.write_text('{"test": "data"}')
    yield file_path
    # Cleanup happens automatically when tmp_path goes out of scope
