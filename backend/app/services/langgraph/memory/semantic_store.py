"""Semantic Memory Store for LangGraph agents.

Provides long-term semantic memory for storing and retrieving
patterns, learnings, and successful strategies.

Features:
- Namespace-based organization (e.g., qualification/patterns)
- JSON value storage with optional vector embeddings
- Semantic search via vector similarity

Usage:
    from app.services.langgraph.memory import semantic_memory

    # Store a qualification pattern
    await semantic_memory.save_qualification_pattern(
        tier="TIER_1",
        persona="AV Director",
        score_breakdown={"company_size": 10, ...}
    )

    # Find similar patterns
    patterns = await semantic_memory.find_similar_patterns(
        query="Higher Education AV Director",
        limit=5
    )
"""

from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


class SemanticMemory:
    """
    Long-term semantic memory for agent patterns and learnings.

    Uses PostgreSQL with pgvector for semantic search capabilities.
    Falls back to in-memory store for testing.
    """

    def __init__(self) -> None:
        """Initialize semantic memory."""
        self._store: Any = None
        self._use_postgres = settings.environment != "test"
        self._memory_store: dict[tuple[str, ...], dict[str, Any]] = {}

    async def _get_postgres_store(self) -> Any:
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

    async def put(
        self,
        namespace: tuple[str, ...],
        key: str,
        value: dict[str, Any],
    ) -> None:
        """
        Store a value in semantic memory.

        Args:
            namespace: Hierarchical namespace (e.g., ("qualification", "patterns"))
            key: Unique key within namespace
            value: Data to store (JSON-serializable dict)
        """
        if self._use_postgres:
            try:
                store = await self._get_postgres_store()
                if store:
                    await store.aput(namespace=namespace, key=key, value=value)
                    return
            except Exception:
                pass  # Fall through to memory store

        # In-memory fallback
        self._memory_store[namespace] = self._memory_store.get(namespace, {})
        self._memory_store[namespace][key] = {
            "value": value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve a value from semantic memory.

        Args:
            namespace: Hierarchical namespace
            key: Key to retrieve

        Returns:
            Stored value or None if not found
        """
        if self._use_postgres:
            try:
                store = await self._get_postgres_store()
                if store:
                    result = await store.aget(namespace=namespace, key=key)
                    return result.value if result else None
            except Exception:
                pass  # Fall through to memory store

        # In-memory fallback
        ns_data = self._memory_store.get(namespace, {})
        entry = ns_data.get(key)
        return entry["value"] if entry else None

    async def search(
        self,
        namespace: tuple[str, ...],
        query: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search semantic memory.

        Args:
            namespace: Namespace to search within
            query: Optional search query (for semantic search)
            limit: Maximum results to return

        Returns:
            List of matching entries
        """
        if self._use_postgres and query:
            try:
                store = await self._get_postgres_store()
                if store and hasattr(store, "asearch"):
                    results = await store.asearch(
                        namespace=namespace,
                        query=query,
                        limit=limit,
                    )
                    return [r.value for r in results]
            except Exception:
                pass  # Fall through to memory store

        # In-memory fallback (simple key matching, no semantic search)
        ns_data = self._memory_store.get(namespace, {})
        results = []
        for key, entry in list(ns_data.items())[:limit]:
            results.append({
                "key": key,
                **entry["value"],
            })
        return results

    async def delete(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> bool:
        """
        Delete a value from semantic memory.

        Args:
            namespace: Hierarchical namespace
            key: Key to delete

        Returns:
            True if deleted, False if not found
        """
        if self._use_postgres:
            try:
                store = await self._get_postgres_store()
                if store:
                    await store.adelete(namespace=namespace, key=key)
                    return True
            except Exception:
                pass  # Fall through to memory store

        # In-memory fallback
        ns_data = self._memory_store.get(namespace, {})
        if key in ns_data:
            del ns_data[key]
            return True
        return False

    # ==========================================================================
    # Convenience methods for specific use cases
    # ==========================================================================

    async def save_qualification_pattern(
        self,
        tier: str,
        persona: str,
        score_breakdown: dict[str, Any],
        success_indicators: list[str] | None = None,
    ) -> None:
        """
        Store a successful qualification pattern.

        Args:
            tier: Qualification tier (TIER_1, TIER_2, etc.)
            persona: Matched persona (AV Director, L&D Director, etc.)
            score_breakdown: Full ICP score breakdown
            success_indicators: What made this a successful qualification
        """
        await self.put(
            namespace=("qualification", "patterns"),
            key=f"{tier}_{persona}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            value={
                "tier": tier,
                "persona": persona,
                "score_breakdown": score_breakdown,
                "success_indicators": success_indicators or [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def find_similar_patterns(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find similar qualification patterns.

        Args:
            query: Search query describing the pattern
            limit: Maximum patterns to return

        Returns:
            List of similar qualification patterns
        """
        return await self.search(
            namespace=("qualification", "patterns"),
            query=query,
            limit=limit,
        )

    async def save_email_success(
        self,
        persona: str,
        email_type: str,
        subject_line: str,
        opening_hook: str,
        response_rate: float | None = None,
    ) -> None:
        """
        Store a successful email pattern.

        Args:
            persona: Target persona
            email_type: Email type (pattern_interrupt, pain_point, etc.)
            subject_line: Subject line that worked
            opening_hook: Opening line that worked
            response_rate: Optional measured response rate
        """
        await self.put(
            namespace=("email", "successes"),
            key=f"{persona}_{email_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            value={
                "persona": persona,
                "email_type": email_type,
                "subject_line": subject_line,
                "opening_hook": opening_hook,
                "response_rate": response_rate,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def find_successful_emails(
        self,
        persona: str,
        email_type: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find successful email patterns.

        Args:
            persona: Target persona
            email_type: Optional email type filter
            limit: Maximum patterns to return

        Returns:
            List of successful email patterns
        """
        query = f"{persona} {email_type or ''} successful email".strip()
        return await self.search(
            namespace=("email", "successes"),
            query=query,
            limit=limit,
        )


# Singleton instance
semantic_memory = SemanticMemory()
