"""Tests for call brief API endpoint.

Tests POST /api/agents/call-brief endpoint behavior.
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.langgraph.agents.call_brief import (
    BriefQuality,
    CallBriefResponse,
    CallScript,
    CompanySnapshot,
    CompetitorPrep,
    ContactInfo,
    DiscoveryPrep,
    ObjectionPrep,
    PhoneInfo,
    QualificationSummary,
    ReferenceStoryBrief,
)


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_request_body() -> dict[str, Any]:
    """Sample API request body."""
    return {
        "lead": {
            "hubspot_id": "test_123",
            "email": "john@university.edu",
            "first_name": "John",
            "last_name": "Doe",
            "company": "State University",
            "title": "AV Director",
            "phone": "555-0100",
            "industry": "higher_ed",
            "persona_match": "av_director",
        },
        "trigger": "content_download",
        "call_type": "warm",
        "research_depth": "quick",
    }


@pytest.fixture
def mock_brief() -> CallBriefResponse:
    """Create a mock brief response."""
    return CallBriefResponse(
        contact=ContactInfo(
            name="John Doe",
            first_name="John",
            last_name="Doe",
            title="AV Director",
            email="john@university.edu",
            persona="av_director",
            persona_title="AV Director",
            is_atl=True,
            phones=PhoneInfo(
                direct_phone="555-0199",
                best_phone="555-0199",
                has_phone=True,
                phone_source="apollo",
            ),
        ),
        company=CompanySnapshot(
            name="State University",
            industry="higher_ed",
            employees=5000,
            overview="A large public university.",
        ),
        qualification=QualificationSummary(
            tier="tier_1",
            tier_label="Tier 1 - Priority Sequence",
            score=78.5,
            confidence=0.85,
        ),
        script=CallScript(
            personalized_script="Hi John, I noticed your interest...",
            talking_points=["NC State case study"],
            call_type="warm",
        ),
        objection_prep=ObjectionPrep(objections=[], source="persona_profile"),
        discovery_prep=DiscoveryPrep(questions=[]),
        competitor_prep=CompetitorPrep(competitors=[]),
        reference_story=ReferenceStoryBrief(customer="NC State"),
        brief_quality=BriefQuality.HIGH,
        intelligence_gaps=[],
        processing_time_ms=1500.0,
        call_type="warm",
        trigger="content_download",
    )


def test_call_brief_endpoint_returns_200(
    client: TestClient,
    sample_request_body: dict[str, Any],
    mock_brief: CallBriefResponse,
) -> None:
    """Test that endpoint returns 200 with valid lead."""
    with patch(
        "app.api.routes.call_brief._assembler.assemble",
        new_callable=AsyncMock,
        return_value=mock_brief,
    ):
        response = client.post("/api/agents/call-brief", json=sample_request_body)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "brief" in data
    assert data["processing_time_ms"] >= 0


def test_call_brief_response_has_all_sections(
    client: TestClient,
    sample_request_body: dict[str, Any],
    mock_brief: CallBriefResponse,
) -> None:
    """Test that response includes all brief sections."""
    with patch(
        "app.api.routes.call_brief._assembler.assemble",
        new_callable=AsyncMock,
        return_value=mock_brief,
    ):
        response = client.post("/api/agents/call-brief", json=sample_request_body)

    brief = response.json()["brief"]
    assert "contact" in brief
    assert "company" in brief
    assert "qualification" in brief
    assert "script" in brief
    assert "objection_prep" in brief
    assert "discovery_prep" in brief
    assert "competitor_prep" in brief
    assert "reference_story" in brief
    assert "brief_quality" in brief
    assert "intelligence_gaps" in brief


def test_call_brief_phone_info_surfaced(
    client: TestClient,
    sample_request_body: dict[str, Any],
    mock_brief: CallBriefResponse,
) -> None:
    """Test that phone info is properly surfaced in response."""
    with patch(
        "app.api.routes.call_brief._assembler.assemble",
        new_callable=AsyncMock,
        return_value=mock_brief,
    ):
        response = client.post("/api/agents/call-brief", json=sample_request_body)

    phones = response.json()["brief"]["contact"]["phones"]
    assert phones["has_phone"] is True
    assert phones["best_phone"] == "555-0199"
    assert phones["direct_phone"] == "555-0199"


def test_call_brief_warm_call(
    client: TestClient,
    sample_request_body: dict[str, Any],
    mock_brief: CallBriefResponse,
) -> None:
    """Test warm call brief."""
    with patch(
        "app.api.routes.call_brief._assembler.assemble",
        new_callable=AsyncMock,
        return_value=mock_brief,
    ):
        response = client.post("/api/agents/call-brief", json=sample_request_body)

    assert response.json()["brief"]["call_type"] == "warm"
    assert response.json()["brief"]["trigger"] == "content_download"


def test_call_brief_cold_call(
    client: TestClient,
    sample_request_body: dict[str, Any],
    mock_brief: CallBriefResponse,
) -> None:
    """Test cold call brief."""
    sample_request_body["call_type"] = "cold"
    sample_request_body["trigger"] = None
    mock_brief.call_type = "cold"
    mock_brief.trigger = None
    mock_brief.script.call_type = "cold"

    with patch(
        "app.api.routes.call_brief._assembler.assemble",
        new_callable=AsyncMock,
        return_value=mock_brief,
    ):
        response = client.post("/api/agents/call-brief", json=sample_request_body)

    assert response.json()["brief"]["call_type"] == "cold"


def test_call_brief_minimal_lead(
    client: TestClient,
    mock_brief: CallBriefResponse,
) -> None:
    """Test endpoint accepts minimal lead data."""
    minimal_body: dict[str, Any] = {
        "lead": {
            "hubspot_id": "min_123",
            "email": "unknown@placeholder.harvester.local",
        },
    }

    with patch(
        "app.api.routes.call_brief._assembler.assemble",
        new_callable=AsyncMock,
        return_value=mock_brief,
    ):
        response = client.post("/api/agents/call-brief", json=minimal_body)

    assert response.status_code == 200


def test_call_brief_missing_lead_returns_422(
    client: TestClient,
) -> None:
    """Test that missing lead field returns validation error."""
    response = client.post("/api/agents/call-brief", json={"trigger": "demo_request"})
    assert response.status_code == 422


def test_call_brief_invalid_lead_returns_422(
    client: TestClient,
) -> None:
    """Test that invalid lead structure returns validation error."""
    response = client.post(
        "/api/agents/call-brief",
        json={"lead": {"email": "missing_hubspot_id"}},
    )
    assert response.status_code == 422


def test_call_brief_processing_time_tracked(
    client: TestClient,
    sample_request_body: dict[str, Any],
    mock_brief: CallBriefResponse,
) -> None:
    """Test that processing time is in the top-level response."""
    with patch(
        "app.api.routes.call_brief._assembler.assemble",
        new_callable=AsyncMock,
        return_value=mock_brief,
    ):
        response = client.post("/api/agents/call-brief", json=sample_request_body)

    data = response.json()
    assert "processing_time_ms" in data
    assert data["processing_time_ms"] >= 0


def test_call_brief_default_values(
    client: TestClient,
    mock_brief: CallBriefResponse,
) -> None:
    """Test that default values are applied correctly."""
    body: dict[str, Any] = {
        "lead": {
            "hubspot_id": "test_defaults",
            "email": "test@example.com",
        },
    }

    with patch(
        "app.api.routes.call_brief._assembler.assemble",
        new_callable=AsyncMock,
        return_value=mock_brief,
    ):
        response = client.post("/api/agents/call-brief", json=body)

    assert response.status_code == 200


def test_call_brief_quality_in_response(
    client: TestClient,
    sample_request_body: dict[str, Any],
    mock_brief: CallBriefResponse,
) -> None:
    """Test that brief quality assessment is in response."""
    with patch(
        "app.api.routes.call_brief._assembler.assemble",
        new_callable=AsyncMock,
        return_value=mock_brief,
    ):
        response = client.post("/api/agents/call-brief", json=sample_request_body)

    brief = response.json()["brief"]
    assert brief["brief_quality"] in ["high", "medium", "low"]
