"""PostgresSaver checkpointing for LangGraph agents.

Provides persistent state checkpointing for agent workflows,
enabling human-in-the-loop workflows, state recovery, and
time travel debugging.

Usage:
    from app.services.langgraph.checkpointing import get_checkpointer

    # In agent
    compiled = graph.compile(checkpointer=get_checkpointer())
    result = await compiled.ainvoke(state, {"configurable": {"thread_id": "my-thread"}})
"""

from functools import lru_cache
from typing import Any

from app.core.config import settings
from langgraph.checkpoint.memory import MemorySaver


class CheckpointManager:
    """
    Manager for LangGraph checkpointing.

    Provides a PostgresSaver for production use with fallback
    to MemorySaver for testing/development.
    """

    def __init__(self):
        """Initialize checkpoint manager."""
        self._checkpointer: Any = None
        self._initialized = False

    def _init_postgres_checkpointer(self) -> Any:
        """
        Initialize PostgresSaver checkpointer.

        Requires langgraph-checkpoint-postgres package.
        Falls back to MemorySaver if unavailable.
        """
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            # Extract sync URL for psycopg connection
            # LangGraph checkpoint expects format: postgresql://user:pass@host:port/db
            db_url = settings.database_url

            # Convert psycopg2 URL to standard postgres URL if needed
            if "+psycopg" in db_url:
                db_url = db_url.replace("postgresql+psycopg://", "postgresql://")

            return AsyncPostgresSaver.from_conn_string(db_url)

        except ImportError:
            # Fallback to memory saver if postgres checkpoint not available
            return MemorySaver()
        except Exception:
            # Fallback on any connection error
            return MemorySaver()

    def get_checkpointer(self) -> Any:
        """
        Get the checkpointer instance.

        Uses PostgresSaver in production, MemorySaver as fallback.
        """
        if not self._initialized:
            if settings.environment == "test":
                # Always use memory saver in tests
                self._checkpointer = MemorySaver()
            else:
                self._checkpointer = self._init_postgres_checkpointer()
            self._initialized = True

        return self._checkpointer

    def get_memory_checkpointer(self) -> MemorySaver:
        """
        Get an in-memory checkpointer.

        Useful for testing or ephemeral workflows.
        """
        return MemorySaver()


# Singleton manager
_checkpoint_manager = CheckpointManager()


@lru_cache
def get_checkpointer() -> Any:
    """
    Get the default checkpointer.

    Cached for reuse across agent instances.
    """
    return _checkpoint_manager.get_checkpointer()


def get_memory_checkpointer() -> MemorySaver:
    """Get an in-memory checkpointer for testing."""
    return _checkpoint_manager.get_memory_checkpointer()


async def setup_checkpoint_tables() -> bool:
    """
    Set up checkpoint tables in the database.

    This should be called during application startup or
    as part of a migration script.

    Returns:
        True if setup succeeded, False otherwise
    """
    try:
        checkpointer = get_checkpointer()

        # AsyncPostgresSaver has setup() method to create tables
        if hasattr(checkpointer, "setup"):
            await checkpointer.setup()
            return True

        return True  # MemorySaver doesn't need setup

    except Exception:
        return False
