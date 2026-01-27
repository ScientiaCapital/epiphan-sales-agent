"""Tests for HubSpot Sync Service.

TDD tests for syncing HubSpot contacts to local Supabase.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.lead_schemas import LeadCreate, SyncResult
from app.services.hubspot.sync import HubSpotSyncService


@pytest.fixture
def mock_hubspot_client():
    """Mock HubSpot client."""
    with patch("app.services.hubspot.sync.hubspot_client") as mock:
        yield mock


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client."""
    with patch("app.services.hubspot.sync.supabase_client") as mock:
        yield mock


@pytest.fixture
def sample_hubspot_contacts():
    """Sample HubSpot contact data."""
    return [
        {
            "id": "12345",
            "email": "john.smith@university.edu",
            "first_name": "John",
            "last_name": "Smith",
            "company": "State University",
            "title": "AV Director",
            "phone": "+1-555-123-4567",
            "linkedin": "linkedin.com/in/johnsmith",
            "city": "Boston",
            "state": "MA",
            "country": "United States",
            "lifecycle_stage": "lead",
            "lead_status": "new",
            "owner_id": "owner123",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-20T14:30:00Z",
            "contact_count": 0,
            "last_contacted": None,
        },
        {
            "id": "12346",
            "email": "jane.doe@techcorp.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "TechCorp Inc",
            "title": "L&D Director",
            "phone": "+1-555-987-6543",
            "linkedin": None,
            "city": "San Francisco",
            "state": "CA",
            "country": "United States",
            "lifecycle_stage": "marketingqualifiedlead",
            "lead_status": "open",
            "owner_id": "owner456",
            "created_at": "2024-01-10T08:00:00Z",
            "updated_at": "2024-01-22T09:15:00Z",
            "contact_count": 2,
            "last_contacted": "2024-01-21T16:00:00Z",
        },
    ]


class TestHubSpotSyncService:
    """Tests for HubSpotSyncService."""

    def test_transform_contact_to_lead(self):
        """Test transforming HubSpot contact to Lead model."""
        service = HubSpotSyncService()

        hubspot_contact = {
            "id": "12345",
            "email": "john.smith@university.edu",
            "first_name": "John",
            "last_name": "Smith",
            "company": "State University",
            "title": "AV Director",
            "phone": "+1-555-123-4567",
            "linkedin": "linkedin.com/in/johnsmith",
            "city": "Boston",
            "state": "MA",
            "country": "United States",
            "lifecycle_stage": "lead",
            "lead_status": "new",
            "owner_id": "owner123",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-20T14:30:00Z",
            "contact_count": 0,
            "last_contacted": None,
        }

        lead = service._transform_contact_to_lead(hubspot_contact)

        assert isinstance(lead, LeadCreate)
        assert lead.hubspot_id == "12345"
        assert lead.email == "john.smith@university.edu"
        assert lead.first_name == "John"
        assert lead.last_name == "Smith"
        assert lead.company == "State University"
        assert lead.title == "AV Director"
        assert lead.lifecycle_stage == "lead"

    def test_transform_contact_skips_invalid_email(self):
        """Test that contacts without email are skipped."""
        service = HubSpotSyncService()

        hubspot_contact = {
            "id": "12345",
            "email": None,
            "first_name": "John",
            "last_name": "Smith",
        }

        lead = service._transform_contact_to_lead(hubspot_contact)
        assert lead is None

    def test_transform_contact_skips_empty_email(self):
        """Test that contacts with empty email are skipped."""
        service = HubSpotSyncService()

        hubspot_contact = {
            "id": "12345",
            "email": "",
            "first_name": "John",
            "last_name": "Smith",
        }

        lead = service._transform_contact_to_lead(hubspot_contact)
        assert lead is None


class TestFullSync:
    """Tests for full_sync operation."""

    @pytest.mark.asyncio
    async def test_full_sync_success(
        self, mock_hubspot_client, mock_supabase_client, sample_hubspot_contacts
    ):
        """Test successful full sync."""
        # Setup mocks
        mock_hubspot_client.get_all_contacts = AsyncMock(
            return_value={
                "results": sample_hubspot_contacts,
                "paging": None,  # No more pages
            }
        )
        mock_supabase_client.upsert_leads_batch = MagicMock(return_value=2)

        service = HubSpotSyncService()
        result = await service.full_sync()

        assert isinstance(result, SyncResult)
        assert result.success is True
        assert result.contacts_fetched == 2
        assert result.contacts_synced == 2
        assert result.contacts_skipped == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_full_sync_with_pagination(
        self, mock_hubspot_client, mock_supabase_client, sample_hubspot_contacts
    ):
        """Test full sync with multiple pages."""
        # First page returns data + paging cursor
        # Second page returns data + no paging
        mock_hubspot_client.get_all_contacts = AsyncMock(
            side_effect=[
                {
                    "results": sample_hubspot_contacts[:1],
                    "paging": {"next": {"after": "cursor123"}},
                },
                {
                    "results": sample_hubspot_contacts[1:],
                    "paging": None,
                },
            ]
        )
        mock_supabase_client.upsert_leads_batch = MagicMock(return_value=1)

        service = HubSpotSyncService()
        result = await service.full_sync()

        assert result.success is True
        assert result.contacts_fetched == 2
        assert mock_hubspot_client.get_all_contacts.call_count == 2

    @pytest.mark.asyncio
    async def test_full_sync_skips_invalid_contacts(
        self, mock_hubspot_client, mock_supabase_client
    ):
        """Test that invalid contacts are skipped but sync continues."""
        contacts_with_invalid = [
            {
                "id": "12345",
                "email": None,  # Invalid - no email
                "first_name": "Invalid",
            },
            {
                "id": "12346",
                "email": "valid@example.com",
                "first_name": "Valid",
            },
        ]

        mock_hubspot_client.get_all_contacts = AsyncMock(
            return_value={"results": contacts_with_invalid, "paging": None}
        )
        mock_supabase_client.upsert_leads_batch = MagicMock(return_value=1)

        service = HubSpotSyncService()
        result = await service.full_sync()

        assert result.success is True
        assert result.contacts_fetched == 2
        assert result.contacts_synced == 1
        assert result.contacts_skipped == 1

    @pytest.mark.asyncio
    async def test_full_sync_handles_hubspot_error(
        self, mock_hubspot_client, mock_supabase_client
    ):
        """Test handling of HubSpot API errors."""
        mock_hubspot_client.get_all_contacts = AsyncMock(
            side_effect=Exception("HubSpot API error")
        )

        service = HubSpotSyncService()
        result = await service.full_sync()

        assert result.success is False
        assert len(result.errors) > 0
        assert "HubSpot API error" in result.errors[0]


class TestIncrementalSync:
    """Tests for incremental_sync operation."""

    @pytest.mark.asyncio
    async def test_incremental_sync_uses_since_filter(
        self, mock_hubspot_client, mock_supabase_client, sample_hubspot_contacts
    ):
        """Test that incremental sync filters by lastmodifieddate."""
        mock_hubspot_client.get_contacts_modified_since = AsyncMock(
            return_value={"results": sample_hubspot_contacts, "paging": None}
        )
        mock_supabase_client.upsert_leads_batch = MagicMock(return_value=2)

        service = HubSpotSyncService()
        since = datetime(2024, 1, 20, 0, 0, 0, tzinfo=timezone.utc)
        result = await service.incremental_sync(since=since)

        assert result.success is True
        mock_hubspot_client.get_contacts_modified_since.assert_called_once()
        call_args = mock_hubspot_client.get_contacts_modified_since.call_args
        assert call_args[1]["since"] == since

    @pytest.mark.asyncio
    async def test_incremental_sync_with_no_changes(
        self, mock_hubspot_client, mock_supabase_client
    ):
        """Test incremental sync when no contacts modified."""
        mock_hubspot_client.get_contacts_modified_since = AsyncMock(
            return_value={"results": [], "paging": None}
        )

        service = HubSpotSyncService()
        since = datetime(2024, 1, 25, 0, 0, 0, tzinfo=timezone.utc)
        result = await service.incremental_sync(since=since)

        assert result.success is True
        assert result.contacts_fetched == 0
        assert result.contacts_synced == 0


class TestLeadTransformation:
    """Tests for lead data transformation."""

    def test_linkedin_url_normalization(self):
        """Test that LinkedIn URLs are normalized."""
        service = HubSpotSyncService()

        # Test various LinkedIn URL formats
        test_cases = [
            ("linkedin.com/in/johnsmith", "https://linkedin.com/in/johnsmith"),
            ("https://linkedin.com/in/johnsmith", "https://linkedin.com/in/johnsmith"),
            ("www.linkedin.com/in/johnsmith", "https://www.linkedin.com/in/johnsmith"),
            (None, None),
            ("", None),
        ]

        for input_url, expected in test_cases:
            result = service._normalize_linkedin_url(input_url)
            assert result == expected, f"Failed for input: {input_url}"

    def test_datetime_parsing(self):
        """Test datetime parsing from HubSpot format."""
        service = HubSpotSyncService()

        # HubSpot uses ISO 8601 format
        test_cases = [
            ("2024-01-15T10:00:00Z", datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)),
            ("2024-01-15T10:00:00.000Z", datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)),
            (None, None),
            ("", None),
        ]

        for input_str, expected in test_cases:
            result = service._parse_datetime(input_str)
            if expected is None:
                assert result is None
            else:
                assert result == expected
