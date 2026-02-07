"""Tests for UserMemoryStore in-memory fallback mode.

Tests run with environment="test" so all operations use the in-memory store.
Covers preferences, interactions, objections, account notes, user context
aggregation, and user deletion.
"""

import pytest

from app.services.langgraph.memory.user_store import UserMemoryStore

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def store() -> UserMemoryStore:
    """Fresh UserMemoryStore for each test (in-memory mode)."""
    s = UserMemoryStore()
    s._use_postgres = False
    return s


# =============================================================================
# Preferences
# =============================================================================


class TestPreferences:
    """Test preference set/get operations."""

    @pytest.mark.asyncio
    async def test_set_and_get_preference(self, store: UserMemoryStore) -> None:
        """Basic set/get roundtrip."""
        await store.set_preference("user1", "preferred_contact_time", "mornings")
        result = await store.get_preference("user1", "preferred_contact_time")
        assert result == "mornings"

    @pytest.mark.asyncio
    async def test_get_preference_default(self, store: UserMemoryStore) -> None:
        """Get returns default when key not found."""
        result = await store.get_preference("user1", "missing_key", default="fallback")
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_get_preference_no_default(self, store: UserMemoryStore) -> None:
        """Get returns None when no default specified."""
        result = await store.get_preference("user1", "missing_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_preferences(self, store: UserMemoryStore) -> None:
        """Get all preferences returns full dict."""
        await store.set_preference("user1", "key1", "val1")
        await store.set_preference("user1", "key2", "val2")
        prefs = await store.get_all_preferences("user1")
        assert prefs["key1"] == "val1"
        assert prefs["key2"] == "val2"
        assert "_updated_at" in prefs

    @pytest.mark.asyncio
    async def test_get_all_preferences_empty_user(self, store: UserMemoryStore) -> None:
        """Get all preferences for unknown user returns empty dict."""
        prefs = await store.get_all_preferences("unknown")
        assert prefs == {}

    @pytest.mark.asyncio
    async def test_overwrite_preference(self, store: UserMemoryStore) -> None:
        """Setting same key overwrites previous value."""
        await store.set_preference("user1", "key", "old")
        await store.set_preference("user1", "key", "new")
        result = await store.get_preference("user1", "key")
        assert result == "new"


# =============================================================================
# Interactions
# =============================================================================


class TestInteractions:
    """Test interaction recording."""

    @pytest.mark.asyncio
    async def test_record_interaction_basic(self, store: UserMemoryStore) -> None:
        """Record a single interaction."""
        await store.record_interaction("user1", "call", "Discussed pricing", "positive")
        ctx = await store.get_user_context("user1")
        assert ctx.interaction_count == 1

    @pytest.mark.asyncio
    async def test_record_interaction_truncates_at_50(self, store: UserMemoryStore) -> None:
        """Interactions truncate to last 50 entries."""
        for i in range(55):
            await store.record_interaction("user1", "call", f"Call #{i}", "neutral")
        ctx = await store.get_user_context("user1")
        assert ctx.interaction_count == 50

    @pytest.mark.asyncio
    async def test_interaction_preserves_latest(self, store: UserMemoryStore) -> None:
        """After truncation, oldest entries are dropped."""
        for i in range(55):
            await store.record_interaction("user1", "call", f"Call #{i}", "neutral")
        # The first 5 (0-4) should be gone, 5-54 remain
        interactions = store._memory_store["user1"]["interactions"]
        assert interactions[0]["summary"] == "Call #5"
        assert interactions[-1]["summary"] == "Call #54"


# =============================================================================
# Objections
# =============================================================================


class TestObjections:
    """Test objection recording."""

    @pytest.mark.asyncio
    async def test_add_objection_basic(self, store: UserMemoryStore) -> None:
        """Record a basic objection."""
        await store.add_objection("user1", "Too expensive")
        ctx = await store.get_user_context("user1")
        assert "Too expensive" in ctx.objections_seen

    @pytest.mark.asyncio
    async def test_add_objection_with_response_and_effectiveness(
        self, store: UserMemoryStore
    ) -> None:
        """Record objection with response metadata."""
        await store.add_objection(
            "user1",
            "We already have a solution",
            response_used="What gaps have you noticed?",
            was_effective=True,
        )
        raw = store._memory_store["user1"]["objections"][0]
        assert raw["objection"] == "We already have a solution"
        assert raw["response_used"] == "What gaps have you noticed?"
        assert raw["was_effective"] is True

    @pytest.mark.asyncio
    async def test_multiple_objections(self, store: UserMemoryStore) -> None:
        """Multiple objections are all recorded."""
        await store.add_objection("user1", "Too expensive")
        await store.add_objection("user1", "Not the right time")
        ctx = await store.get_user_context("user1")
        assert len(ctx.objections_seen) == 2


# =============================================================================
# User Context Aggregation
# =============================================================================


class TestUserContext:
    """Test get_user_context aggregation."""

    @pytest.mark.asyncio
    async def test_empty_user_context(self, store: UserMemoryStore) -> None:
        """Empty user returns zeroed context."""
        ctx = await store.get_user_context("nobody")
        assert ctx.user_id == "nobody"
        assert ctx.interaction_count == 0
        assert ctx.last_interaction is None
        assert ctx.objections_seen == []
        assert ctx.account_notes is None
        assert ctx.preferences == {}

    @pytest.mark.asyncio
    async def test_context_interaction_count_and_last(self, store: UserMemoryStore) -> None:
        """Context correctly reports interaction count and last interaction."""
        await store.record_interaction("user1", "call", "First call", "positive")
        await store.record_interaction("user1", "email", "Follow up", "neutral")
        ctx = await store.get_user_context("user1")
        assert ctx.interaction_count == 2
        assert ctx.last_interaction is not None

    @pytest.mark.asyncio
    async def test_context_objections_list(self, store: UserMemoryStore) -> None:
        """Context collects objection texts."""
        await store.add_objection("user1", "Price concern")
        await store.add_objection("user1", "Timeline issue")
        ctx = await store.get_user_context("user1")
        assert ctx.objections_seen == ["Price concern", "Timeline issue"]

    @pytest.mark.asyncio
    async def test_context_with_account_notes(self, store: UserMemoryStore) -> None:
        """Context includes account notes."""
        await store.set_account_notes("user1", "Key stakeholder: VP Engineering")
        ctx = await store.get_user_context("user1")
        assert ctx.account_notes == "Key stakeholder: VP Engineering"

    @pytest.mark.asyncio
    async def test_context_combines_all_data(self, store: UserMemoryStore) -> None:
        """Context aggregates preferences, interactions, objections, and notes."""
        await store.set_preference("user1", "style", "formal")
        await store.record_interaction("user1", "call", "Intro call", "positive")
        await store.add_objection("user1", "Budget locked")
        await store.set_account_notes("user1", "Renewal in Q3")

        ctx = await store.get_user_context("user1")
        assert ctx.preferences["style"] == "formal"
        assert ctx.interaction_count == 1
        assert "Budget locked" in ctx.objections_seen
        assert ctx.account_notes == "Renewal in Q3"


# =============================================================================
# User Deletion
# =============================================================================


class TestDeleteUser:
    """Test user data deletion."""

    @pytest.mark.asyncio
    async def test_delete_user_removes_all_data(self, store: UserMemoryStore) -> None:
        """Deleting a user clears all their data."""
        await store.set_preference("user1", "key", "val")
        await store.record_interaction("user1", "call", "test", "ok")
        await store.add_objection("user1", "concern")
        await store.set_account_notes("user1", "notes")

        result = await store.delete_user("user1")
        assert result is True

        ctx = await store.get_user_context("user1")
        assert ctx.interaction_count == 0
        assert ctx.objections_seen == []
        assert ctx.account_notes is None

    @pytest.mark.asyncio
    async def test_delete_unknown_user_returns_false(self, store: UserMemoryStore) -> None:
        """Deleting a non-existent user returns False."""
        result = await store.delete_user("ghost")
        assert result is False


# =============================================================================
# Multi-User Isolation
# =============================================================================


class TestMultiUserIsolation:
    """Test that different users don't interfere with each other."""

    @pytest.mark.asyncio
    async def test_users_are_isolated(self, store: UserMemoryStore) -> None:
        """Data for user A doesn't appear in user B's context."""
        await store.set_preference("alice", "color", "blue")
        await store.record_interaction("alice", "call", "Alice call", "positive")
        await store.add_objection("alice", "Alice objection")

        await store.set_preference("bob", "color", "red")
        await store.record_interaction("bob", "email", "Bob email", "neutral")

        alice_ctx = await store.get_user_context("alice")
        bob_ctx = await store.get_user_context("bob")

        assert alice_ctx.preferences["color"] == "blue"
        assert bob_ctx.preferences["color"] == "red"
        assert alice_ctx.interaction_count == 1
        assert bob_ctx.interaction_count == 1
        assert "Alice objection" in alice_ctx.objections_seen
        assert bob_ctx.objections_seen == []
