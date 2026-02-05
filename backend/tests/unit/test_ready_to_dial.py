"""Tests for ready-to-dial endpoint.

Tests GET /api/leads/ready-to-dial endpoint behavior.
"""

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_leads() -> list[dict[str, Any]]:
    """Sample leads data from Supabase."""
    return [
        {
            "id": "uuid-1",
            "hubspot_id": "hs_001",
            "first_name": "Alice",
            "last_name": "Smith",
            "company": "Big University",
            "title": "AV Director",
            "email": "alice@bigu.edu",
            "phone": "555-0001",
            "persona_match": "av_director",
            "tier": "hot",
            "total_score": 92,
            "last_contacted": None,
        },
        {
            "id": "uuid-2",
            "hubspot_id": "hs_002",
            "first_name": "Bob",
            "last_name": "Jones",
            "company": "Tech Corp",
            "title": "IT Director",
            "email": "bob@techcorp.com",
            "phone": "555-0002",
            "persona_match": "technical_director",
            "tier": "warm",
            "total_score": 78,
            "last_contacted": None,
        },
        {
            "id": "uuid-3",
            "hubspot_id": "hs_003",
            "first_name": "Charlie",
            "last_name": "Brown",
            "company": "Small LLC",
            "title": "Manager",
            "email": "charlie@small.com",
            "phone": None,  # No phone!
            "persona_match": None,
            "tier": "nurture",
            "total_score": 55,
            "last_contacted": None,
        },
        {
            "id": "uuid-4",
            "hubspot_id": "hs_004",
            "first_name": "Diana",
            "last_name": "Prince",
            "company": "Startup Inc",
            "title": "Intern",
            "email": "diana@startup.com",
            "phone": None,
            "persona_match": None,
            "tier": "cold",
            "total_score": 25,
            "last_contacted": None,
        },
    ]


def test_ready_to_dial_returns_leads(
    client: TestClient,
    mock_leads: list[dict[str, Any]],
) -> None:
    """Test that endpoint returns leads."""
    with patch(
        "app.api.routes.leads.supabase_client.get_prioritized_leads",
        return_value=mock_leads,
    ):
        response = client.get("/api/leads/ready-to-dial")

    assert response.status_code == 200
    data = response.json()
    assert "leads" in data
    assert "total_count" in data
    assert "filters_applied" in data


def test_ready_to_dial_default_warm_filter(
    client: TestClient,
    mock_leads: list[dict[str, Any]],
) -> None:
    """Test default min_tier=warm filters out nurture and cold."""
    with patch(
        "app.api.routes.leads.supabase_client.get_prioritized_leads",
        return_value=mock_leads,
    ):
        response = client.get("/api/leads/ready-to-dial")

    leads = response.json()["leads"]
    # Should only include hot (92) and warm (78) — both >= 70
    scores = [lead["total_score"] for lead in leads]
    assert all(s >= 70 for s in scores)


def test_ready_to_dial_require_phone(
    client: TestClient,
    mock_leads: list[dict[str, Any]],
) -> None:
    """Test require_phone filter excludes leads without phones."""
    with patch(
        "app.api.routes.leads.supabase_client.get_prioritized_leads",
        return_value=mock_leads,
    ):
        response = client.get("/api/leads/ready-to-dial?require_phone=true&min_tier=cold")

    leads = response.json()["leads"]
    for lead in leads:
        assert lead["has_phone"] is True
        assert lead["best_phone"] is not None


def test_ready_to_dial_hot_only(
    client: TestClient,
    mock_leads: list[dict[str, Any]],
) -> None:
    """Test min_tier=hot only returns 85+ leads."""
    with patch(
        "app.api.routes.leads.supabase_client.get_prioritized_leads",
        return_value=mock_leads,
    ):
        response = client.get("/api/leads/ready-to-dial?min_tier=hot")

    leads = response.json()["leads"]
    scores = [lead["total_score"] for lead in leads]
    assert all(s >= 85 for s in scores)
    assert len(leads) == 1  # Only Alice with score 92


def test_ready_to_dial_includes_call_brief_url(
    client: TestClient,
    mock_leads: list[dict[str, Any]],
) -> None:
    """Test each entry includes call_brief_url."""
    with patch(
        "app.api.routes.leads.supabase_client.get_prioritized_leads",
        return_value=mock_leads,
    ):
        response = client.get("/api/leads/ready-to-dial")

    leads = response.json()["leads"]
    for lead in leads:
        assert "call_brief_url" in lead
        assert lead["call_brief_url"] == "/api/agents/call-brief"


def test_ready_to_dial_respects_limit(
    client: TestClient,
    mock_leads: list[dict[str, Any]],
) -> None:
    """Test limit parameter caps results."""
    with patch(
        "app.api.routes.leads.supabase_client.get_prioritized_leads",
        return_value=mock_leads,
    ):
        response = client.get("/api/leads/ready-to-dial?limit=1&min_tier=cold")

    leads = response.json()["leads"]
    assert len(leads) <= 1


def test_ready_to_dial_ordered_by_score(
    client: TestClient,
    mock_leads: list[dict[str, Any]],
) -> None:
    """Test leads are ordered by score descending."""
    with patch(
        "app.api.routes.leads.supabase_client.get_prioritized_leads",
        return_value=mock_leads,
    ):
        response = client.get("/api/leads/ready-to-dial?min_tier=cold")

    leads = response.json()["leads"]
    scores = [lead["total_score"] for lead in leads]
    assert scores == sorted(scores, reverse=True)


def test_ready_to_dial_filters_in_response(
    client: TestClient,
    mock_leads: list[dict[str, Any]],
) -> None:
    """Test filters_applied is in response."""
    with patch(
        "app.api.routes.leads.supabase_client.get_prioritized_leads",
        return_value=mock_leads,
    ):
        response = client.get("/api/leads/ready-to-dial?min_tier=hot&require_phone=true")

    filters = response.json()["filters_applied"]
    assert filters["min_tier"] == "hot"
    assert filters["require_phone"] is True
