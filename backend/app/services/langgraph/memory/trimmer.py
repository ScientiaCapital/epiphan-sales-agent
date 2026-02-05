"""Message Trimmer for LangGraph agents.

Provides short-term memory management by trimming conversation history
to prevent context overflow while preserving important information.

Features:
- Message count limiting
- Token count limiting (estimated)
- System message preservation
- Recent message prioritization
- Optional summarization of trimmed content

Based on LangChain best practices for memory management:
- Keep system prompts
- Preserve recent context
- Summarize older messages when possible
"""

import logging
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

logger = logging.getLogger(__name__)


@dataclass
class TrimResult:
    """Result of message trimming operation."""

    messages: list[BaseMessage]
    trimmed_count: int
    original_count: int
    estimated_tokens_before: int
    estimated_tokens_after: int
    summary_added: bool

    @property
    def was_trimmed(self) -> bool:
        """Check if any messages were trimmed."""
        return self.trimmed_count > 0

    @property
    def reduction_percentage(self) -> float:
        """Calculate percentage of messages trimmed."""
        if self.original_count == 0:
            return 0.0
        return (self.trimmed_count / self.original_count) * 100


class MessageTrimmer:
    """
    Trim conversation messages to prevent context overflow.

    Strategies:
    1. Always keep system messages
    2. Keep the N most recent messages
    3. Optionally summarize trimmed content
    4. Respect token limits

    Usage:
        trimmer = MessageTrimmer(max_messages=20, max_tokens=8000)
        result = await trimmer.trim(messages)
        # result.messages contains trimmed list
    """

    # Approximate tokens per character (GPT-style tokenization)
    TOKENS_PER_CHAR = 0.25

    def __init__(
        self,
        max_messages: int = 20,
        max_tokens: int = 8000,
        keep_system: bool = True,
        summarize_trimmed: bool = False,
        summary_model: str | None = None,
    ) -> None:
        """
        Initialize message trimmer.

        Args:
            max_messages: Maximum number of messages to keep
            max_tokens: Maximum estimated token count
            keep_system: Whether to always keep system messages
            summarize_trimmed: Whether to summarize trimmed messages
            summary_model: Model to use for summarization (if enabled)
        """
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.keep_system = keep_system
        self.summarize_trimmed = summarize_trimmed
        self.summary_model = summary_model

        # Stats tracking
        self._total_trims = 0
        self._total_messages_trimmed = 0

    async def trim(
        self,
        messages: list[BaseMessage],
        llm: Any | None = None,
    ) -> TrimResult:
        """
        Trim messages to fit within limits.

        Args:
            messages: List of messages to trim
            llm: Optional LLM for summarization

        Returns:
            TrimResult with trimmed messages and stats
        """
        if not messages:
            return TrimResult(
                messages=[],
                trimmed_count=0,
                original_count=0,
                estimated_tokens_before=0,
                estimated_tokens_after=0,
                summary_added=False,
            )

        original_count = len(messages)
        tokens_before = self._estimate_tokens(messages)

        # Check if trimming is needed
        if (
            len(messages) <= self.max_messages
            and tokens_before <= self.max_tokens
        ):
            return TrimResult(
                messages=messages,
                trimmed_count=0,
                original_count=original_count,
                estimated_tokens_before=tokens_before,
                estimated_tokens_after=tokens_before,
                summary_added=False,
            )

        # Separate system messages if configured to keep them
        system_messages: list[BaseMessage] = []
        non_system_messages: list[BaseMessage] = []

        for msg in messages:
            if self.keep_system and isinstance(msg, SystemMessage):
                system_messages.append(msg)
            else:
                non_system_messages.append(msg)

        # Calculate how many non-system messages we can keep
        system_tokens = self._estimate_tokens(system_messages)
        available_tokens = self.max_tokens - system_tokens
        available_slots = self.max_messages - len(system_messages)

        # Keep the most recent messages
        trimmed_messages, trimmed_content = self._select_recent_messages(
            non_system_messages,
            max_count=available_slots,
            max_tokens=available_tokens,
        )

        # Optionally summarize trimmed content
        summary_added = False
        if self.summarize_trimmed and trimmed_content and llm:
            summary = await self._summarize_content(trimmed_content, llm)
            if summary:
                # Insert summary as a system message after existing system messages
                summary_msg = SystemMessage(
                    content=f"[Summary of earlier conversation]: {summary}"
                )
                trimmed_messages.insert(0, summary_msg)
                summary_added = True

        # Combine system messages with kept messages
        final_messages = system_messages + trimmed_messages

        # Update stats
        trimmed_count = original_count - len(final_messages)
        if summary_added:
            trimmed_count -= 1  # Don't count the summary as a trim

        self._total_trims += 1
        self._total_messages_trimmed += trimmed_count

        tokens_after = self._estimate_tokens(final_messages)

        logger.info(
            f"Trimmed messages: {original_count} -> {len(final_messages)} "
            f"(tokens: {tokens_before} -> {tokens_after})"
        )

        return TrimResult(
            messages=final_messages,
            trimmed_count=trimmed_count,
            original_count=original_count,
            estimated_tokens_before=tokens_before,
            estimated_tokens_after=tokens_after,
            summary_added=summary_added,
        )

    def _select_recent_messages(
        self,
        messages: list[BaseMessage],
        max_count: int,
        max_tokens: int,
    ) -> tuple[list[BaseMessage], list[BaseMessage]]:
        """
        Select most recent messages within limits.

        Args:
            messages: Messages to select from (non-system)
            max_count: Maximum number to keep
            max_tokens: Maximum tokens to keep

        Returns:
            Tuple of (kept_messages, trimmed_messages)
        """
        if not messages:
            return [], []

        # Start from the end (most recent)
        kept: list[BaseMessage] = []
        trimmed: list[BaseMessage] = []
        current_tokens = 0

        for msg in reversed(messages):
            msg_tokens = self._estimate_message_tokens(msg)

            if (
                len(kept) < max_count
                and current_tokens + msg_tokens <= max_tokens
            ):
                kept.insert(0, msg)  # Insert at beginning to maintain order
                current_tokens += msg_tokens
            else:
                trimmed.insert(0, msg)

        return kept, trimmed

    def _estimate_tokens(self, messages: list[BaseMessage]) -> int:
        """Estimate total token count for messages."""
        return sum(self._estimate_message_tokens(msg) for msg in messages)

    def _estimate_message_tokens(self, message: BaseMessage) -> int:
        """Estimate token count for a single message."""
        # Content tokens
        content = message.content if isinstance(message.content, str) else ""
        content_tokens = int(len(content) * self.TOKENS_PER_CHAR)

        # Add overhead for message structure
        overhead = 4  # Approximate overhead per message

        return content_tokens + overhead

    async def _summarize_content(
        self,
        messages: list[BaseMessage],
        llm: Any,
    ) -> str | None:
        """
        Summarize trimmed messages.

        Args:
            messages: Messages to summarize
            llm: LLM to use for summarization

        Returns:
            Summary string or None if summarization fails
        """
        try:
            content_parts = []
            for msg in messages:
                role = self._get_role(msg)
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                content_parts.append(f"{role}: {content[:500]}")  # Truncate long messages

            combined = "\n".join(content_parts)

            prompt = f"""Summarize the following conversation in 2-3 sentences, \
capturing the key points and any decisions made:

{combined}

Summary:"""

            response = await llm.ainvoke(prompt)
            return str(response.content) if response.content else None

        except Exception as e:
            logger.warning(f"Failed to summarize trimmed content: {e}")
            return None

    def _get_role(self, message: BaseMessage) -> str:
        """Get role string for a message."""
        if isinstance(message, SystemMessage):
            return "System"
        elif isinstance(message, HumanMessage):
            return "Human"
        elif isinstance(message, AIMessage):
            return "AI"
        else:
            return "Unknown"

    def get_stats(self) -> dict[str, Any]:
        """Get trimming statistics."""
        return {
            "total_trims": self._total_trims,
            "total_messages_trimmed": self._total_messages_trimmed,
            "config": {
                "max_messages": self.max_messages,
                "max_tokens": self.max_tokens,
                "keep_system": self.keep_system,
                "summarize_trimmed": self.summarize_trimmed,
            },
        }

    def reset_stats(self) -> None:
        """Reset trimming statistics."""
        self._total_trims = 0
        self._total_messages_trimmed = 0


class ConversationWindow:
    """
    Sliding window for conversation history.

    Automatically trims messages as new ones are added,
    maintaining a fixed-size context window.

    Usage:
        window = ConversationWindow(max_messages=10)
        window.add(HumanMessage(content="Hello"))
        window.add(AIMessage(content="Hi there!"))
        messages = window.get_messages()
    """

    def __init__(
        self,
        max_messages: int = 20,
        max_tokens: int = 8000,
    ) -> None:
        """
        Initialize conversation window.

        Args:
            max_messages: Maximum messages in window
            max_tokens: Maximum tokens in window
        """
        self._messages: list[BaseMessage] = []
        self._trimmer = MessageTrimmer(
            max_messages=max_messages,
            max_tokens=max_tokens,
            summarize_trimmed=False,
        )

    def add(self, message: BaseMessage) -> None:
        """Add a message to the window."""
        self._messages.append(message)

    def add_many(self, messages: list[BaseMessage]) -> None:
        """Add multiple messages to the window."""
        self._messages.extend(messages)

    async def get_messages(self) -> list[BaseMessage]:
        """Get trimmed messages from the window."""
        result = await self._trimmer.trim(self._messages)
        self._messages = result.messages
        return result.messages

    def clear(self) -> None:
        """Clear all messages from the window."""
        self._messages = []

    @property
    def message_count(self) -> int:
        """Get current message count (before trimming)."""
        return len(self._messages)


# Factory function for common configurations
def create_trimmer(
    preset: Literal["aggressive", "balanced", "conservative"] = "balanced",
    with_summarization: bool = False,
) -> MessageTrimmer:
    """
    Create a trimmer with preset configuration.

    Args:
        preset: Configuration preset
            - aggressive: 10 messages, 4000 tokens
            - balanced: 20 messages, 8000 tokens
            - conservative: 50 messages, 16000 tokens
        with_summarization: Whether to enable summarization

    Returns:
        Configured MessageTrimmer
    """
    presets = {
        "aggressive": {"max_messages": 10, "max_tokens": 4000},
        "balanced": {"max_messages": 20, "max_tokens": 8000},
        "conservative": {"max_messages": 50, "max_tokens": 16000},
    }

    config = presets[preset]
    return MessageTrimmer(
        max_messages=config["max_messages"],
        max_tokens=config["max_tokens"],
        summarize_trimmed=with_summarization,
    )
