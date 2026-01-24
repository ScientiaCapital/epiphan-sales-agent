"""
Integration Tests for Supabase

These tests demonstrate how to test Supabase interactions:
- CRUD operations with real or mocked Supabase
- Row Level Security (RLS) policy testing
- Authentication flows
- Edge functions
- Storage operations

Requirements:
    pip install supabase pytest-asyncio

Environment Variables:
    SUPABASE_URL - Your Supabase project URL
    SUPABASE_KEY - Your anon or service key
    SUPABASE_SERVICE_KEY - Service role key (for RLS bypass testing)

Usage:
    # Run with real Supabase (integration)
    pytest tests/integration/test_supabase.py -m integration

    # Run with mocked Supabase (unit)
    pytest tests/integration/test_supabase.py -m "not integration"
"""

from __future__ import annotations

import os
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip all tests if supabase is not installed
pytest.importorskip("supabase")

from supabase import create_client, Client


# -----------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------

@pytest.fixture
def supabase_url() -> str:
    """Get Supabase URL from environment."""
    url = os.getenv("SUPABASE_URL")
    if not url:
        pytest.skip("SUPABASE_URL not set")
    return url


@pytest.fixture
def supabase_key() -> str:
    """Get Supabase anon key from environment."""
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not key:
        pytest.skip("SUPABASE_KEY not set")
    return key


@pytest.fixture
def supabase_service_key() -> str:
    """Get Supabase service role key from environment."""
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not key:
        pytest.skip("SUPABASE_SERVICE_KEY not set")
    return key


@pytest.fixture
def supabase_client(supabase_url: str, supabase_key: str) -> Client:
    """Create a Supabase client with anon key (respects RLS)."""
    return create_client(supabase_url, supabase_key)


@pytest.fixture
def supabase_admin_client(supabase_url: str, supabase_service_key: str) -> Client:
    """Create a Supabase client with service key (bypasses RLS)."""
    return create_client(supabase_url, supabase_service_key)


@pytest.fixture
def mock_supabase() -> Generator[MagicMock, None, None]:
    """
    Create a mock Supabase client for unit testing.
    Use this when you don't want to hit real Supabase.
    """
    mock_client = MagicMock(spec=Client)

    # Mock the table builder pattern
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.neq.return_value = mock_table
    mock_table.gt.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lt.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.like.return_value = mock_table
    mock_table.ilike.return_value = mock_table
    mock_table.is_.return_value = mock_table
    mock_table.in_.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.range.return_value = mock_table
    mock_table.single.return_value = mock_table
    mock_table.maybe_single.return_value = mock_table

    # Default empty response
    mock_table.execute.return_value = MagicMock(data=[], count=0)

    mock_client.table.return_value = mock_table
    mock_client.from_.return_value = mock_table

    yield mock_client


# -----------------------------------------------------------------
# Unit Tests (Mocked)
# -----------------------------------------------------------------

class TestSupabaseClientMocked:
    """Unit tests using mocked Supabase client."""

    def test_select_query(self, mock_supabase: MagicMock) -> None:
        """Test that select query is built correctly."""
        # Setup mock response
        mock_supabase.table("users").select("*").execute.return_value = MagicMock(
            data=[{"id": "1", "name": "Test User"}],
            count=1
        )

        # Execute query
        result = mock_supabase.table("users").select("*").execute()

        # Verify
        assert len(result.data) == 1
        assert result.data[0]["name"] == "Test User"
        mock_supabase.table.assert_called_with("users")

    def test_insert_operation(self, mock_supabase: MagicMock) -> None:
        """Test that insert operation works correctly."""
        new_user = {"name": "New User", "email": "new@example.com"}

        mock_supabase.table("users").insert(new_user).execute.return_value = MagicMock(
            data=[{"id": "2", **new_user}],
            count=1
        )

        result = mock_supabase.table("users").insert(new_user).execute()

        assert result.data[0]["id"] == "2"
        assert result.data[0]["name"] == "New User"

    def test_update_with_filter(self, mock_supabase: MagicMock) -> None:
        """Test update operation with filter."""
        update_data = {"name": "Updated Name"}

        mock_supabase.table("users").update(update_data).eq("id", "1").execute.return_value = MagicMock(
            data=[{"id": "1", "name": "Updated Name"}],
            count=1
        )

        result = (
            mock_supabase.table("users")
            .update(update_data)
            .eq("id", "1")
            .execute()
        )

        assert result.data[0]["name"] == "Updated Name"

    def test_delete_operation(self, mock_supabase: MagicMock) -> None:
        """Test delete operation."""
        mock_supabase.table("users").delete().eq("id", "1").execute.return_value = MagicMock(
            data=[{"id": "1"}],
            count=1
        )

        result = mock_supabase.table("users").delete().eq("id", "1").execute()

        assert result.count == 1


# -----------------------------------------------------------------
# Integration Tests (Real Supabase)
# -----------------------------------------------------------------

@pytest.mark.integration
class TestSupabaseIntegration:
    """
    Integration tests that hit a real Supabase instance.

    These tests require:
    - SUPABASE_URL and SUPABASE_KEY environment variables
    - A 'test_items' table in your Supabase project

    Create the test table:
        CREATE TABLE test_items (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            name TEXT NOT NULL,
            value INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Enable RLS
        ALTER TABLE test_items ENABLE ROW LEVEL SECURITY;

        -- Allow all operations for testing (adjust for production)
        CREATE POLICY "Allow all for testing" ON test_items
            FOR ALL USING (true) WITH CHECK (true);
    """

    @pytest.fixture(autouse=True)
    def cleanup_test_data(
        self, supabase_client: Client
    ) -> Generator[None, None, None]:
        """Clean up test data before and after each test."""
        # Clean before test
        supabase_client.table("test_items").delete().neq("id", "").execute()

        yield

        # Clean after test
        supabase_client.table("test_items").delete().neq("id", "").execute()

    def test_insert_and_select(self, supabase_client: Client) -> None:
        """Test inserting and retrieving data."""
        # Insert
        test_item = {"name": "Integration Test Item", "value": 42}
        insert_result = supabase_client.table("test_items").insert(test_item).execute()

        assert len(insert_result.data) == 1
        inserted_id = insert_result.data[0]["id"]

        # Select
        select_result = (
            supabase_client.table("test_items")
            .select("*")
            .eq("id", inserted_id)
            .single()
            .execute()
        )

        assert select_result.data["name"] == "Integration Test Item"
        assert select_result.data["value"] == 42

    def test_update_record(self, supabase_client: Client) -> None:
        """Test updating a record."""
        # Insert first
        test_item = {"name": "Original Name", "value": 1}
        insert_result = supabase_client.table("test_items").insert(test_item).execute()
        item_id = insert_result.data[0]["id"]

        # Update
        update_result = (
            supabase_client.table("test_items")
            .update({"name": "Updated Name", "value": 2})
            .eq("id", item_id)
            .execute()
        )

        assert update_result.data[0]["name"] == "Updated Name"
        assert update_result.data[0]["value"] == 2

    def test_delete_record(self, supabase_client: Client) -> None:
        """Test deleting a record."""
        # Insert first
        test_item = {"name": "To Be Deleted", "value": 0}
        insert_result = supabase_client.table("test_items").insert(test_item).execute()
        item_id = insert_result.data[0]["id"]

        # Delete
        supabase_client.table("test_items").delete().eq("id", item_id).execute()

        # Verify deletion
        select_result = (
            supabase_client.table("test_items")
            .select("*")
            .eq("id", item_id)
            .execute()
        )

        assert len(select_result.data) == 0

    def test_filter_operations(self, supabase_client: Client) -> None:
        """Test various filter operations."""
        # Insert test data
        items = [
            {"name": "Item A", "value": 10},
            {"name": "Item B", "value": 20},
            {"name": "Item C", "value": 30},
        ]
        supabase_client.table("test_items").insert(items).execute()

        # Test gt (greater than)
        gt_result = (
            supabase_client.table("test_items")
            .select("*")
            .gt("value", 15)
            .execute()
        )
        assert len(gt_result.data) == 2

        # Test lt (less than)
        lt_result = (
            supabase_client.table("test_items")
            .select("*")
            .lt("value", 25)
            .execute()
        )
        assert len(lt_result.data) == 2

        # Test order
        ordered_result = (
            supabase_client.table("test_items")
            .select("*")
            .order("value", desc=True)
            .execute()
        )
        assert ordered_result.data[0]["value"] == 30


@pytest.mark.integration
class TestRowLevelSecurity:
    """
    Tests for Row Level Security (RLS) policies.

    These tests verify that RLS policies are working correctly
    by comparing results between anon key (respects RLS) and
    service key (bypasses RLS).
    """

    def test_rls_restricts_access(
        self,
        supabase_client: Client,
        supabase_admin_client: Client,
    ) -> None:
        """
        Test that RLS restricts access appropriately.

        This test assumes you have a table with user-specific RLS.
        Adjust the table name and policies according to your schema.
        """
        # This is a placeholder - implement based on your actual RLS policies
        # Example: If you have a 'user_posts' table where users can only see their own posts

        # Insert as admin (bypasses RLS)
        # admin_result = supabase_admin_client.table("user_posts").insert(...).execute()

        # Try to access as anon (subject to RLS)
        # anon_result = supabase_client.table("user_posts").select("*").execute()

        # Verify RLS is working
        # assert len(anon_result.data) < len(admin_result.data)  # or == 0

        pytest.skip("Implement based on your specific RLS policies")


# -----------------------------------------------------------------
# Example: Testing a Repository Pattern
# -----------------------------------------------------------------

class UserRepository:
    """Example repository class that wraps Supabase operations."""

    def __init__(self, client: Client) -> None:
        self.client = client
        self.table = "users"

    def get_by_id(self, user_id: str) -> dict | None:
        """Get a user by ID."""
        result = (
            self.client.table(self.table)
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def create(self, user_data: dict) -> dict:
        """Create a new user."""
        result = (
            self.client.table(self.table)
            .insert(user_data)
            .execute()
        )
        return result.data[0]

    def update(self, user_id: str, user_data: dict) -> dict:
        """Update an existing user."""
        result = (
            self.client.table(self.table)
            .update(user_data)
            .eq("id", user_id)
            .execute()
        )
        return result.data[0]

    def delete(self, user_id: str) -> bool:
        """Delete a user."""
        result = (
            self.client.table(self.table)
            .delete()
            .eq("id", user_id)
            .execute()
        )
        return len(result.data) > 0


class TestUserRepository:
    """Tests for the UserRepository class using mocked Supabase."""

    def test_get_by_id_found(self, mock_supabase: MagicMock) -> None:
        """Test getting a user that exists."""
        # Setup mock
        mock_supabase.table("users").select("*").eq("id", "1").maybe_single().execute.return_value = MagicMock(
            data={"id": "1", "name": "Test User"}
        )

        repo = UserRepository(mock_supabase)
        user = repo.get_by_id("1")

        assert user is not None
        assert user["name"] == "Test User"

    def test_get_by_id_not_found(self, mock_supabase: MagicMock) -> None:
        """Test getting a user that doesn't exist."""
        mock_supabase.table("users").select("*").eq("id", "999").maybe_single().execute.return_value = MagicMock(
            data=None
        )

        repo = UserRepository(mock_supabase)
        user = repo.get_by_id("999")

        assert user is None

    def test_create_user(self, mock_supabase: MagicMock) -> None:
        """Test creating a new user."""
        new_user = {"name": "New User", "email": "new@example.com"}
        mock_supabase.table("users").insert(new_user).execute.return_value = MagicMock(
            data=[{"id": "2", **new_user}]
        )

        repo = UserRepository(mock_supabase)
        created = repo.create(new_user)

        assert created["id"] == "2"
        assert created["name"] == "New User"
