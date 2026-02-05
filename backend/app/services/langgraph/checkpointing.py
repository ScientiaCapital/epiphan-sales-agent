"""PostgresSaver checkpointing for LangGraph agents.

Provides persistent state checkpointing for agent workflows,
enabling human-in-the-loop workflows, state recovery, and
time travel debugging.

Encryption:
    Set LANGGRAPH_AES_KEY environment variable to enable AES encryption
    of checkpoint data at rest. Generate a secure key with:
        openssl rand -base64 32

Usage:
    from app.services.langgraph.checkpointing import get_checkpointer

    # In agent
    compiled = graph.compile(checkpointer=get_checkpointer())
    result = await compiled.ainvoke(state, {"configurable": {"thread_id": "my-thread"}})
"""

import logging
import os
from functools import lru_cache
from typing import Any

from app.core.config import settings
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


class AESCipher:
    """AES cipher implementation for checkpoint encryption.

    Uses AES-256-GCM for authenticated encryption.
    Requires cryptography package.

    Implements LangGraph's CipherProtocol:
    - encrypt(plaintext) -> (cipher_name, ciphertext)
    - decrypt(cipher_name, ciphertext) -> plaintext
    """

    CIPHER_NAME = "aes-256-gcm"

    def __init__(self, key: bytes) -> None:
        """
        Initialize AES cipher.

        Args:
            key: 32-byte AES key (base64 decoded from LANGGRAPH_AES_KEY)
        """
        self._key = key

    def encrypt(self, plaintext: bytes) -> tuple[str, bytes]:
        """
        Encrypt plaintext using AES-256-GCM.

        Returns:
            Tuple of (cipher_name, ciphertext with prepended nonce)
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as err:
            raise ImportError(
                "cryptography package required for checkpoint encryption. "
                "Install with: pip install cryptography"
            ) from err

        import secrets

        # Generate random 12-byte nonce
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        # Prepend nonce to ciphertext
        return (self.CIPHER_NAME, nonce + ciphertext)

    def decrypt(self, ciphername: str, ciphertext: bytes) -> bytes:
        """
        Decrypt ciphertext using AES-256-GCM.

        Args:
            ciphername: Name of cipher (must match CIPHER_NAME)
            ciphertext: Ciphertext with prepended nonce

        Returns:
            Decrypted plaintext
        """
        if ciphername != self.CIPHER_NAME:
            raise ValueError(f"Unknown cipher: {ciphername}, expected {self.CIPHER_NAME}")

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as err:
            raise ImportError(
                "cryptography package required for checkpoint encryption. "
                "Install with: pip install cryptography"
            ) from err

        # Extract nonce (first 12 bytes) and actual ciphertext
        nonce = ciphertext[:12]
        actual_ciphertext = ciphertext[12:]
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(nonce, actual_ciphertext, None)


def get_serializer() -> Any:
    """
    Get serializer with optional AES encryption.

    If LANGGRAPH_AES_KEY environment variable is set, returns an
    EncryptedSerializer that encrypts checkpoint data at rest.
    Otherwise returns None to use the default JsonPlusSerializer.

    The key should be a base64-encoded 32-byte key. Generate with:
        openssl rand -base64 32

    Returns:
        EncryptedSerializer if key is set, None otherwise
    """
    import base64

    aes_key = os.getenv("LANGGRAPH_AES_KEY")
    if aes_key:
        try:
            from langgraph.checkpoint.serde.encrypted import EncryptedSerializer

            # Decode base64 key
            key_bytes = base64.b64decode(aes_key)
            if len(key_bytes) != 32:
                logger.warning(
                    f"LANGGRAPH_AES_KEY must be 32 bytes (got {len(key_bytes)}). "
                    "Falling back to unencrypted."
                )
                return None

            cipher = AESCipher(key_bytes)
            logger.info("Checkpoint encryption enabled with LANGGRAPH_AES_KEY")
            return EncryptedSerializer(cipher=cipher)
        except ImportError as e:
            logger.warning(
                f"Encryption dependencies not available: {e}. "
                "Falling back to unencrypted."
            )
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize EncryptedSerializer: {e}")
            return None
    return None


class CheckpointManager:
    """
    Manager for LangGraph checkpointing.

    Provides a PostgresSaver for production use with fallback
    to MemorySaver for testing/development.
    """

    def __init__(self) -> None:
        """Initialize checkpoint manager."""
        self._checkpointer: Any = None
        self._initialized = False

    def _init_postgres_checkpointer(self) -> Any:
        """
        Initialize PostgresSaver checkpointer.

        Requires langgraph-checkpoint-postgres package.
        Falls back to MemorySaver if unavailable.

        If LANGGRAPH_AES_KEY is set, enables encrypted serialization.
        """
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            # Extract sync URL for psycopg connection
            # LangGraph checkpoint expects format: postgresql://user:pass@host:port/db
            db_url = settings.database_url

            # Convert psycopg2 URL to standard postgres URL if needed
            if "+psycopg" in db_url:
                db_url = db_url.replace("postgresql+psycopg://", "postgresql://")

            # Get optional encrypted serializer
            serializer = get_serializer()

            if serializer:
                return AsyncPostgresSaver.from_conn_string(db_url, serde=serializer)
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
