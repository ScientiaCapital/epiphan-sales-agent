"""Tests for Clay CRUD methods in Supabase client.

Mirrors the Apollo phone webhook CRUD test patterns.
"""

from unittest.mock import MagicMock

import pytest

from app.services.database.supabase_client import SupabaseClient


@pytest.fixture()
def mock_supabase() -> MagicMock:
    """Create a mock Supabase client for testing."""
    mock = MagicMock()
    return mock


@pytest.fixture()
def db_client(mock_supabase: MagicMock) -> SupabaseClient:
    """Create a SupabaseClient with mocked connection."""
    client = SupabaseClient.__new__(SupabaseClient)
    client._client = mock_supabase
    return client


# =============================================================================
# store_clay_enrichment
# =============================================================================


class TestStoreClayEnrichment:
    """Tests for storing Clay enrichment results."""

    def test_store_clay_enrichment(self, db_client: SupabaseClient, mock_supabase: MagicMock) -> None:
        """Inserts enrichment record with correct data."""
        mock_chain = MagicMock()
        mock_supabase.table.return_value = mock_chain
        mock_chain.upsert.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(
            data=[{"id": "uuid-1", "lead_id": "lead_123"}]
        )

        result = db_client.store_clay_enrichment(
            lead_id="lead_123",
            data={
                "phones": [{"number": "+1234", "type": "mobile"}],
                "emails": [],
                "company_name": "Acme Corp",
                "raw_payload": {"original": True},
            },
        )

        assert result["id"] == "uuid-1"
        mock_supabase.table.assert_called_with("clay_enrichment_results")
        upsert_call = mock_chain.upsert.call_args
        record = upsert_call.args[0]
        assert record["lead_id"] == "lead_123"
        assert record["company_name"] == "Acme Corp"
        assert record["synced_to_hubspot"] is False

    def test_store_clay_enrichment_upsert(self, db_client: SupabaseClient, mock_supabase: MagicMock) -> None:
        """Uses upsert with lead_id conflict resolution."""
        mock_chain = MagicMock()
        mock_supabase.table.return_value = mock_chain
        mock_chain.upsert.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{"id": "uuid-2"}])

        db_client.store_clay_enrichment(lead_id="lead_456", data={"raw_payload": {}})

        upsert_call = mock_chain.upsert.call_args
        assert upsert_call.kwargs.get("on_conflict") == "lead_id"


# =============================================================================
# get_clay_enrichment
# =============================================================================


class TestGetClayEnrichment:
    """Tests for fetching Clay enrichment by lead_id."""

    def test_get_clay_enrichment_found(self, db_client: SupabaseClient, mock_supabase: MagicMock) -> None:
        """Returns enrichment data when found."""
        mock_chain = MagicMock()
        mock_supabase.table.return_value = mock_chain
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(
            data=[{"id": "uuid-1", "lead_id": "lead_123", "phones": "[]"}]
        )

        result = db_client.get_clay_enrichment("lead_123")
        assert result is not None
        assert result["lead_id"] == "lead_123"

    def test_get_clay_enrichment_not_found(self, db_client: SupabaseClient, mock_supabase: MagicMock) -> None:
        """Returns None when no enrichment exists."""
        mock_chain = MagicMock()
        mock_supabase.table.return_value = mock_chain
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[])

        result = db_client.get_clay_enrichment("nonexistent")
        assert result is None


# =============================================================================
# get_unsynced_clay_enrichments
# =============================================================================


class TestGetUnsyncedClayEnrichments:
    """Tests for fetching unsynced Clay records."""

    def test_get_unsynced(self, db_client: SupabaseClient, mock_supabase: MagicMock) -> None:
        """Returns unsynced records in correct order."""
        mock_chain = MagicMock()
        mock_supabase.table.return_value = mock_chain
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(
            data=[
                {"id": "uuid-1", "synced_to_hubspot": False},
                {"id": "uuid-2", "synced_to_hubspot": False},
            ]
        )

        results = db_client.get_unsynced_clay_enrichments(limit=50)
        assert len(results) == 2
        mock_chain.eq.assert_called_with("synced_to_hubspot", False)


# =============================================================================
# mark_clay_synced
# =============================================================================


class TestMarkClaySynced:
    """Tests for marking Clay records as synced."""

    def test_mark_synced(self, db_client: SupabaseClient, mock_supabase: MagicMock) -> None:
        """Updates synced flag and timestamp."""
        mock_chain = MagicMock()
        mock_supabase.table.return_value = mock_chain
        mock_chain.update.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[])

        db_client.mark_clay_synced("uuid-1")

        mock_supabase.table.assert_called_with("clay_enrichment_results")
        update_call = mock_chain.update.call_args
        update_data = update_call.args[0]
        assert update_data["synced_to_hubspot"] is True
        assert "synced_at" in update_data
