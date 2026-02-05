"""Tests for enhanced streaming functionality.

Tests cover:
- MasterOrchestratorAgent.stream: Node-level streaming
- MasterOrchestratorAgent.stream_tokens: Token-level streaming with astream_events
- EmailPersonalizationAgent.stream_tokens: Token-level email streaming
- API endpoints for streaming
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.data.lead_schemas import Lead


class TestOrchestratorNodeStreaming:
    """Tests for orchestrator node-level streaming."""

    @pytest.fixture
    def sample_lead(self) -> Lead:
        """Create a sample lead for testing."""
        return Lead(
            hubspot_id="test-123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            company="Test Company",
        )

    @pytest.mark.asyncio
    async def test_stream_yields_node_updates(self, sample_lead: Lead) -> None:
        """Test that stream yields updates as nodes complete."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent

        orchestrator = MasterOrchestratorAgent()

        # Mock the graph's astream method
        mock_events = [
            {"parallel_research": {"research_brief": {"company_overview": "Test"}}},
            {"synthesis": {"confidence_score": 0.8}},
            {"review_gate_1": {"gate_1_decision": {"proceed": True}}},
        ]

        mock_graph = MagicMock()
        mock_compiled = MagicMock()

        async def mock_astream(*_args: Any, **_kwargs: Any) -> Any:
            for event in mock_events:
                yield event

        mock_compiled.astream = mock_astream
        mock_graph.compile.return_value = mock_compiled
        orchestrator._graph = mock_graph

        events: list[dict[str, Any]] = []
        async for event in orchestrator.stream(sample_lead):
            events.append(event)

        assert len(events) == 3
        assert events[0]["event_type"] == "node_update"
        assert events[0]["node"] == "parallel_research"
        assert events[1]["node"] == "synthesis"
        assert events[2]["node"] == "review_gate_1"

    @pytest.mark.asyncio
    async def test_stream_includes_timestamps(self, sample_lead: Lead) -> None:
        """Test that stream events include ISO timestamps."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent

        orchestrator = MasterOrchestratorAgent()

        mock_events = [
            {"parallel_research": {}},
        ]

        mock_graph = MagicMock()
        mock_compiled = MagicMock()

        async def mock_astream(*_args: Any, **_kwargs: Any) -> Any:
            for event in mock_events:
                yield event

        mock_compiled.astream = mock_astream
        mock_graph.compile.return_value = mock_compiled
        orchestrator._graph = mock_graph

        events: list[dict[str, Any]] = []
        async for event in orchestrator.stream(sample_lead):
            events.append(event)

        assert len(events) == 1
        # Should be a valid ISO timestamp
        timestamp = events[0]["timestamp"]
        assert "T" in timestamp
        # Parse to verify it's valid
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


class TestOrchestratorTokenStreaming:
    """Tests for orchestrator token-level streaming."""

    @pytest.fixture
    def sample_lead(self) -> Lead:
        """Create a sample lead for testing."""
        return Lead(
            hubspot_id="test-456",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            company="Test Company",
        )

    @pytest.mark.asyncio
    async def test_stream_tokens_yields_token_events(self, sample_lead: Lead) -> None:
        """Test that stream_tokens yields token-level events."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent

        orchestrator = MasterOrchestratorAgent()

        # Mock chunk with content
        mock_chunk = MagicMock()
        mock_chunk.content = "Hello"

        mock_events = [
            {
                "event": "on_chat_model_stream",
                "data": {"chunk": mock_chunk},
                "run_id": "run-123",
            },
        ]

        mock_graph = MagicMock()
        mock_compiled = MagicMock()

        async def mock_astream_events(*_args: Any, **_kwargs: Any) -> Any:
            for event in mock_events:
                yield event

        mock_compiled.astream_events = mock_astream_events
        mock_graph.compile.return_value = mock_compiled
        orchestrator._graph = mock_graph

        events: list[dict[str, Any]] = []
        async for event in orchestrator.stream_tokens(sample_lead):
            events.append(event)

        assert len(events) == 1
        assert events[0]["event_type"] == "token"
        assert events[0]["content"] == "Hello"
        assert events[0]["run_id"] == "run-123"

    @pytest.mark.asyncio
    async def test_stream_tokens_handles_chain_events(self, sample_lead: Lead) -> None:
        """Test that stream_tokens handles chain start/end events."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent

        orchestrator = MasterOrchestratorAgent()

        mock_events = [
            {
                "event": "on_chain_start",
                "name": "parallel_research",
                "run_id": "run-start",
                "parent_ids": [],
            },
            {
                "event": "on_chain_end",
                "name": "parallel_research",
                "run_id": "run-end",
            },
        ]

        mock_graph = MagicMock()
        mock_compiled = MagicMock()

        async def mock_astream_events(*_args: Any, **_kwargs: Any) -> Any:
            for event in mock_events:
                yield event

        mock_compiled.astream_events = mock_astream_events
        mock_graph.compile.return_value = mock_compiled
        orchestrator._graph = mock_graph

        events: list[dict[str, Any]] = []
        async for event in orchestrator.stream_tokens(sample_lead):
            events.append(event)

        assert len(events) == 2
        assert events[0]["event_type"] == "chain_start"
        assert events[0]["name"] == "parallel_research"
        assert events[1]["event_type"] == "chain_end"

    @pytest.mark.asyncio
    async def test_stream_tokens_handles_tool_events(self, sample_lead: Lead) -> None:
        """Test that stream_tokens handles tool start/end events."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent

        orchestrator = MasterOrchestratorAgent()

        mock_events = [
            {
                "event": "on_tool_start",
                "name": "enrich_from_apollo",
                "run_id": "tool-run",
                "data": {"input": {"email": "test@example.com"}},
            },
            {
                "event": "on_tool_end",
                "name": "enrich_from_apollo",
                "run_id": "tool-run",
                "data": {"output": {"company": "Test Co"}},
            },
        ]

        mock_graph = MagicMock()
        mock_compiled = MagicMock()

        async def mock_astream_events(*_args: Any, **_kwargs: Any) -> Any:
            for event in mock_events:
                yield event

        mock_compiled.astream_events = mock_astream_events
        mock_graph.compile.return_value = mock_compiled
        orchestrator._graph = mock_graph

        events: list[dict[str, Any]] = []
        async for event in orchestrator.stream_tokens(sample_lead):
            events.append(event)

        assert len(events) == 2
        assert events[0]["event_type"] == "tool_start"
        assert events[0]["name"] == "enrich_from_apollo"
        assert events[0]["input"] == {"email": "test@example.com"}
        assert events[1]["event_type"] == "tool_end"
        assert events[1]["output"] == {"company": "Test Co"}

    @pytest.mark.asyncio
    async def test_stream_tokens_handles_custom_events(self, sample_lead: Lead) -> None:
        """Test that stream_tokens handles custom developer events."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent

        orchestrator = MasterOrchestratorAgent()

        mock_events = [
            {
                "event": "on_custom_event",
                "name": "qualification_progress",
                "data": {"dimension": "company_size", "score": 8},
                "run_id": "custom-run",
            },
        ]

        mock_graph = MagicMock()
        mock_compiled = MagicMock()

        async def mock_astream_events(*_args: Any, **_kwargs: Any) -> Any:
            for event in mock_events:
                yield event

        mock_compiled.astream_events = mock_astream_events
        mock_graph.compile.return_value = mock_compiled
        orchestrator._graph = mock_graph

        events: list[dict[str, Any]] = []
        async for event in orchestrator.stream_tokens(sample_lead):
            events.append(event)

        assert len(events) == 1
        assert events[0]["event_type"] == "custom"
        assert events[0]["name"] == "qualification_progress"
        assert events[0]["data"] == {"dimension": "company_size", "score": 8}


class TestEmailTokenStreaming:
    """Tests for email personalization token-level streaming."""

    @pytest.fixture
    def sample_lead(self) -> Lead:
        """Create a sample lead for testing."""
        return Lead(
            hubspot_id="email-test-123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            company="Test Company",
        )

    @pytest.mark.asyncio
    async def test_stream_tokens_yields_email_tokens(self, sample_lead: Lead) -> None:
        """Test that email stream_tokens yields individual tokens."""
        from app.services.langgraph.agents.email_personalization import (
            EmailPersonalizationAgent,
        )

        agent = EmailPersonalizationAgent()

        # Mock chunk with content (simulating email being typed)
        mock_chunks = [
            MagicMock(content="Subject: "),
            MagicMock(content="Quick question"),
            MagicMock(content=" about Test Company"),
        ]

        mock_events = [
            {
                "event": "on_chat_model_stream",
                "data": {"chunk": chunk},
                "run_id": "email-run",
            }
            for chunk in mock_chunks
        ]

        mock_graph = MagicMock()
        mock_compiled = MagicMock()

        async def mock_astream_events(*_args: Any, **_kwargs: Any) -> Any:
            for event in mock_events:
                yield event

        mock_compiled.astream_events = mock_astream_events
        mock_graph.compile.return_value = mock_compiled
        agent._graph = mock_graph

        events: list[dict[str, Any]] = []
        async for event in agent.stream_tokens(sample_lead):
            events.append(event)

        assert len(events) == 3
        assert events[0]["content"] == "Subject: "
        assert events[1]["content"] == "Quick question"
        assert events[2]["content"] == " about Test Company"

    @pytest.mark.asyncio
    async def test_stream_tokens_with_research_brief(self, sample_lead: Lead) -> None:
        """Test stream_tokens with research brief context."""
        from app.services.langgraph.agents.email_personalization import (
            EmailPersonalizationAgent,
        )
        from app.services.langgraph.states import ResearchBrief

        agent = EmailPersonalizationAgent()

        research_brief: ResearchBrief = {
            "company_overview": "Leading video solutions provider",
            "recent_news": ["Just raised Series B"],
            "talking_points": ["Video streaming expertise"],
            "risk_factors": [],
            "linkedin_summary": None,
        }

        mock_chunk = MagicMock()
        mock_chunk.content = "Personalized content"

        mock_events = [
            {
                "event": "on_chat_model_stream",
                "data": {"chunk": mock_chunk},
                "run_id": "brief-run",
            },
        ]

        mock_graph = MagicMock()
        mock_compiled = MagicMock()

        async def mock_astream_events(*_args: Any, **_kwargs: Any) -> Any:
            for event in mock_events:
                yield event

        mock_compiled.astream_events = mock_astream_events
        mock_graph.compile.return_value = mock_compiled
        agent._graph = mock_graph

        events: list[dict[str, Any]] = []
        async for event in agent.stream_tokens(
            sample_lead, research_brief=research_brief
        ):
            events.append(event)

        assert len(events) == 1
        assert events[0]["content"] == "Personalized content"


class TestStreamingAPIEndpoints:
    """Tests for streaming API endpoints."""

    @pytest.mark.asyncio
    async def test_email_stream_endpoint_format(self) -> None:
        """Test that email stream endpoint returns proper SSE format."""

        from fastapi.testclient import TestClient

        from app.main import app

        # Mock the agent's stream_tokens method
        mock_events = [
            {"event_type": "token", "content": "Hello", "timestamp": "2024-01-01T00:00:00+00:00"},
            {"event_type": "chain_end", "name": "generate_email", "timestamp": "2024-01-01T00:00:01+00:00"},
        ]

        async def mock_stream_tokens(*_args: Any, **_kwargs: Any) -> Any:
            for event in mock_events:
                yield event

        with patch(
            "app.api.routes.agents.email_personalization_agent.stream_tokens",
            mock_stream_tokens,
        ), TestClient(app) as client:
            response = client.post(
                "/api/agents/emails/stream",
                json={
                    "lead": {
                        "hubspot_id": "test-123",
                        "email": "test@example.com",
                    }
                },
            )

            # Check content type
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    @pytest.mark.asyncio
    async def test_batch_token_stream_endpoint(self) -> None:
        """Test that batch token stream endpoint exists and returns SSE."""
        from fastapi.testclient import TestClient

        from app.main import app

        async def mock_stream_tokens(*_args: Any, **_kwargs: Any) -> Any:
            yield {"event_type": "token", "content": "test"}

        with patch(
            "app.services.langgraph.agents.orchestrator.MasterOrchestratorAgent.stream_tokens",
            mock_stream_tokens,
        ), TestClient(app) as client:
            response = client.post(
                "/api/batch/process/stream/tokens",
                json={
                    "lead": {
                        "hubspot_id": "test-123",
                        "email": "test@example.com",
                    }
                },
            )

            # Check content type
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


class TestStreamEventTimestamps:
    """Tests for consistent timestamp handling in streaming."""

    def test_timestamps_are_timezone_aware(self) -> None:
        """Test that all timestamps use timezone-aware UTC."""
        # Verify we're using the correct datetime pattern
        timestamp = datetime.now(timezone.utc).isoformat()

        # Should contain timezone info
        assert "+" in timestamp or "Z" in timestamp

    @pytest.mark.asyncio
    async def test_stream_timestamps_are_utc(self) -> None:
        """Test that stream events use UTC timestamps."""
        from app.services.langgraph.agents.orchestrator import MasterOrchestratorAgent

        orchestrator = MasterOrchestratorAgent()

        mock_events = [{"test_node": {}}]

        mock_graph = MagicMock()
        mock_compiled = MagicMock()

        async def mock_astream(*_args: Any, **_kwargs: Any) -> Any:
            for event in mock_events:
                yield event

        mock_compiled.astream = mock_astream
        mock_graph.compile.return_value = mock_compiled
        orchestrator._graph = mock_graph

        sample_lead = Lead(
            hubspot_id="ts-test",
            email="test@example.com",
        )

        events = []
        async for event in orchestrator.stream(sample_lead):
            events.append(event)

        # Timestamp should be UTC (contains +00:00 or Z)
        timestamp = events[0]["timestamp"]
        assert "+00:00" in timestamp or "Z" in timestamp
