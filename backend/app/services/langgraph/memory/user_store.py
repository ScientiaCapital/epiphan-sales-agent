"""Cross-Thread User Memory Store for LangGraph agents.

Provides persistent user preferences and context that persists
across conversation threads.

Features:
- User preferences (contact times, communication style)
- Interaction history summary
- Objection patterns encountered
- Account context (company, stakeholders)

Usage:
    from app.services.langgraph.memory.user_store import user_memory

    # Store user preference
    await user_memory.set_preference(
        user_id="user@company.com",
        key="preferred_contact_time",
        value="mornings"
    )

    # Get all user context
    context = await user_memory.get_user_context(user_id="user@company.com")
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, cast

from app.core.config import settings


@dataclass
class UserContext:
    """Aggregated user context from memory."""

    user_id: str
    preferences: dict[str, Any]
    interaction_count: int
    last_interaction: datetime | None
    objections_seen: list[str]
    account_notes: str | None


class UserMemoryStore:
    """
    Store user preferences and context across threads.

    Enables agents to "remember" users between conversations,
    providing continuity and personalization.

    Uses PostgreSQL with namespace-based storage.
    Falls back to in-memory store for testing.
    """

    NAMESPACE_PREFIX = ("users",)

    def __init__(self) -> None:
        """Initialize user memory store."""
        self._store: Any = None
        self._use_postgres = settings.environment != "test"
        self._memory_store: dict[str, dict[str, Any]] = {}

    async def _get_store(self) -> Any:
        """Get PostgresStore instance."""
        if self._store is None:
            try:
                from langgraph.store.postgres import AsyncPostgresStore

                db_url = settings.database_url
                if "+psycopg" in db_url:
                    db_url = db_url.replace("postgresql+psycopg://", "postgresql://")

                self._store = AsyncPostgresStore.from_conn_string(db_url)

            except ImportError:
                self._use_postgres = False
            except Exception:
                self._use_postgres = False

        return self._store

    def _get_namespace(self, user_id: str) -> tuple[str, ...]:
        """Get namespace for a user."""
        return (*self.NAMESPACE_PREFIX, user_id)

    async def set_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
    ) -> None:
        """
        Set a user preference.

        Args:
            user_id: User identifier (typically email)
            key: Preference key (e.g., "preferred_contact_time")
            value: Preference value
        """
        namespace = self._get_namespace(user_id)

        if self._use_postgres:
            try:
                store = await self._get_store()
                if store:
                    # Get existing preferences
                    result = await store.aget(namespace=namespace, key="preferences")
                    prefs = result.value if result else {}
                    prefs[key] = value
                    prefs["_updated_at"] = datetime.now(timezone.utc).isoformat()
                    await store.aput(namespace=namespace, key="preferences", value=prefs)
                    return
            except Exception:
                pass  # Fall through to memory store

        # In-memory fallback
        if user_id not in self._memory_store:
            self._memory_store[user_id] = {"preferences": {}}
        self._memory_store[user_id]["preferences"][key] = value
        self._memory_store[user_id]["preferences"]["_updated_at"] = (
            datetime.now(timezone.utc).isoformat()
        )

    async def get_preference(
        self,
        user_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Get a user preference.

        Args:
            user_id: User identifier
            key: Preference key
            default: Default value if not found

        Returns:
            Preference value or default
        """
        namespace = self._get_namespace(user_id)

        if self._use_postgres:
            try:
                store = await self._get_store()
                if store:
                    result = await store.aget(namespace=namespace, key="preferences")
                    if result and key in result.value:
                        return result.value[key]
                    return default
            except Exception:
                pass  # Fall through to memory store

        # In-memory fallback
        user_data = self._memory_store.get(user_id, {})
        prefs = user_data.get("preferences", {})
        return prefs.get(key, default)

    async def get_all_preferences(self, user_id: str) -> dict[str, Any]:
        """
        Get all preferences for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary of all preferences
        """
        namespace = self._get_namespace(user_id)

        if self._use_postgres:
            try:
                store = await self._get_store()
                if store:
                    result = await store.aget(namespace=namespace, key="preferences")
                    return result.value if result else {}
            except Exception:
                pass  # Fall through to memory store

        # In-memory fallback
        user_data = self._memory_store.get(user_id, {})
        prefs = user_data.get("preferences", {})
        return cast(dict[str, Any], prefs)

    async def record_interaction(
        self,
        user_id: str,
        interaction_type: str,
        summary: str,
        outcome: str | None = None,
    ) -> None:
        """
        Record a user interaction.

        Args:
            user_id: User identifier
            interaction_type: Type of interaction (call, email, meeting)
            summary: Brief summary of interaction
            outcome: Optional outcome (positive, negative, neutral)
        """
        namespace = self._get_namespace(user_id)
        interaction = {
            "type": interaction_type,
            "summary": summary,
            "outcome": outcome,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self._use_postgres:
            try:
                store = await self._get_store()
                if store:
                    # Get existing interactions
                    result = await store.aget(namespace=namespace, key="interactions")
                    interactions = result.value if result else []
                    interactions.append(interaction)
                    # Keep only last 50 interactions
                    interactions = interactions[-50:]
                    await store.aput(
                        namespace=namespace, key="interactions", value=interactions
                    )
                    return
            except Exception:
                pass  # Fall through to memory store

        # In-memory fallback
        if user_id not in self._memory_store:
            self._memory_store[user_id] = {}
        if "interactions" not in self._memory_store[user_id]:
            self._memory_store[user_id]["interactions"] = []
        self._memory_store[user_id]["interactions"].append(interaction)
        # Keep only last 50
        self._memory_store[user_id]["interactions"] = self._memory_store[user_id][
            "interactions"
        ][-50:]

    async def add_objection(
        self,
        user_id: str,
        objection: str,
        response_used: str | None = None,
        was_effective: bool | None = None,
    ) -> None:
        """
        Record an objection encountered with this user.

        Args:
            user_id: User identifier
            objection: The objection raised
            response_used: Optional response that was used
            was_effective: Whether the response was effective
        """
        namespace = self._get_namespace(user_id)
        objection_record = {
            "objection": objection,
            "response_used": response_used,
            "was_effective": was_effective,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self._use_postgres:
            try:
                store = await self._get_store()
                if store:
                    result = await store.aget(namespace=namespace, key="objections")
                    objections = result.value if result else []
                    objections.append(objection_record)
                    await store.aput(
                        namespace=namespace, key="objections", value=objections
                    )
                    return
            except Exception:
                pass  # Fall through to memory store

        # In-memory fallback
        if user_id not in self._memory_store:
            self._memory_store[user_id] = {}
        if "objections" not in self._memory_store[user_id]:
            self._memory_store[user_id]["objections"] = []
        self._memory_store[user_id]["objections"].append(objection_record)

    async def set_account_notes(self, user_id: str, notes: str) -> None:
        """
        Set account-level notes for a user.

        Args:
            user_id: User identifier
            notes: Free-form account notes
        """
        namespace = self._get_namespace(user_id)

        if self._use_postgres:
            try:
                store = await self._get_store()
                if store:
                    await store.aput(
                        namespace=namespace,
                        key="account_notes",
                        value={
                            "notes": notes,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    return
            except Exception:
                pass  # Fall through to memory store

        # In-memory fallback
        if user_id not in self._memory_store:
            self._memory_store[user_id] = {}
        self._memory_store[user_id]["account_notes"] = {
            "notes": notes,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_user_context(self, user_id: str) -> UserContext:
        """
        Get aggregated user context.

        Args:
            user_id: User identifier

        Returns:
            UserContext with all available information
        """
        namespace = self._get_namespace(user_id)

        preferences: dict[str, Any] = {}
        interactions: list[dict[str, Any]] = []
        objections: list[dict[str, Any]] = []
        account_notes: str | None = None

        if self._use_postgres:
            try:
                store = await self._get_store()
                if store:
                    # Fetch all user data
                    pref_result = await store.aget(namespace=namespace, key="preferences")
                    preferences = pref_result.value if pref_result else {}

                    int_result = await store.aget(namespace=namespace, key="interactions")
                    interactions = int_result.value if int_result else []

                    obj_result = await store.aget(namespace=namespace, key="objections")
                    objections = obj_result.value if obj_result else []

                    notes_result = await store.aget(
                        namespace=namespace, key="account_notes"
                    )
                    if notes_result:
                        account_notes = notes_result.value.get("notes")
            except Exception:
                pass  # Use empty defaults

        else:
            # In-memory fallback
            user_data = self._memory_store.get(user_id, {})
            preferences = user_data.get("preferences", {})
            interactions = user_data.get("interactions", [])
            objections = user_data.get("objections", [])
            notes_data = user_data.get("account_notes", {})
            account_notes = notes_data.get("notes") if notes_data else None

        # Calculate derived fields
        last_interaction = None
        if interactions:
            last_ts = interactions[-1].get("timestamp")
            if last_ts:
                last_interaction = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))

        objection_texts = [obj.get("objection", "") for obj in objections]

        return UserContext(
            user_id=user_id,
            preferences=preferences,
            interaction_count=len(interactions),
            last_interaction=last_interaction,
            objections_seen=objection_texts,
            account_notes=account_notes,
        )

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete all data for a user.

        Args:
            user_id: User identifier

        Returns:
            True if deleted, False if not found
        """
        namespace = self._get_namespace(user_id)

        if self._use_postgres:
            try:
                store = await self._get_store()
                if store:
                    for key in ["preferences", "interactions", "objections", "account_notes"]:
                        await store.adelete(namespace=namespace, key=key)
                    return True
            except Exception:
                pass  # Fall through to memory store

        # In-memory fallback
        if user_id in self._memory_store:
            del self._memory_store[user_id]
            return True
        return False


# Singleton instance
user_memory = UserMemoryStore()
