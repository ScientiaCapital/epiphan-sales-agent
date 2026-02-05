"""Tests for message trimmer.

Tests cover:
- Message count limiting
- Token count limiting
- System message preservation
- Summarization
- ConversationWindow
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.services.langgraph.memory.trimmer import (
    ConversationWindow,
    MessageTrimmer,
    TrimResult,
    create_trimmer,
)


class TestTrimResult:
    """Tests for TrimResult dataclass."""

    def test_was_trimmed_true(self) -> None:
        """Test was_trimmed returns True when messages trimmed."""
        result = TrimResult(
            messages=[],
            trimmed_count=5,
            original_count=10,
            estimated_tokens_before=1000,
            estimated_tokens_after=500,
            summary_added=False,
        )
        assert result.was_trimmed is True

    def test_was_trimmed_false(self) -> None:
        """Test was_trimmed returns False when no messages trimmed."""
        result = TrimResult(
            messages=[],
            trimmed_count=0,
            original_count=10,
            estimated_tokens_before=1000,
            estimated_tokens_after=1000,
            summary_added=False,
        )
        assert result.was_trimmed is False

    def test_reduction_percentage(self) -> None:
        """Test reduction percentage calculation."""
        result = TrimResult(
            messages=[],
            trimmed_count=5,
            original_count=10,
            estimated_tokens_before=1000,
            estimated_tokens_after=500,
            summary_added=False,
        )
        assert result.reduction_percentage == 50.0

    def test_reduction_percentage_zero_original(self) -> None:
        """Test reduction percentage with zero original count."""
        result = TrimResult(
            messages=[],
            trimmed_count=0,
            original_count=0,
            estimated_tokens_before=0,
            estimated_tokens_after=0,
            summary_added=False,
        )
        assert result.reduction_percentage == 0.0


class TestMessageTrimmer:
    """Tests for MessageTrimmer class."""

    @pytest.fixture
    def trimmer(self) -> MessageTrimmer:
        """Create trimmer with test configuration."""
        return MessageTrimmer(
            max_messages=5,
            max_tokens=1000,
        )

    @pytest.fixture
    def sample_messages(self) -> list[HumanMessage | AIMessage]:
        """Create sample conversation messages."""
        return [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
            HumanMessage(content="How are you?"),
            AIMessage(content="I'm doing well, thanks!"),
            HumanMessage(content="What's the weather?"),
            AIMessage(content="I can't check the weather."),
            HumanMessage(content="Thanks anyway"),
            AIMessage(content="You're welcome!"),
        ]

    @pytest.mark.asyncio
    async def test_no_trim_when_within_limits(self, trimmer: MessageTrimmer) -> None:
        """Test that no trimming occurs when within limits."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi!"),
        ]

        result = await trimmer.trim(messages)

        assert result.trimmed_count == 0
        assert len(result.messages) == 2

    @pytest.mark.asyncio
    async def test_trims_to_max_messages(
        self, trimmer: MessageTrimmer, sample_messages: list[HumanMessage | AIMessage]
    ) -> None:
        """Test trimming to max message count."""
        result = await trimmer.trim(sample_messages)

        assert len(result.messages) <= 5
        assert result.trimmed_count > 0

    @pytest.mark.asyncio
    async def test_keeps_most_recent(
        self, trimmer: MessageTrimmer, sample_messages: list[HumanMessage | AIMessage]
    ) -> None:
        """Test that most recent messages are kept."""
        result = await trimmer.trim(sample_messages)

        # Last message should be preserved
        assert result.messages[-1].content == "You're welcome!"

    @pytest.mark.asyncio
    async def test_preserves_system_messages(self) -> None:
        """Test that system messages are always kept."""
        trimmer = MessageTrimmer(max_messages=3, keep_system=True)
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Hello"),
            AIMessage(content="Hi!"),
            HumanMessage(content="How are you?"),
            AIMessage(content="I'm well!"),
            HumanMessage(content="Great!"),
        ]

        result = await trimmer.trim(messages)

        # System message should be preserved
        assert any(
            isinstance(m, SystemMessage)
            for m in result.messages
        )
        assert result.messages[0].content == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_handles_empty_messages(self, trimmer: MessageTrimmer) -> None:
        """Test handling empty message list."""
        result = await trimmer.trim([])

        assert result.messages == []
        assert result.trimmed_count == 0
        assert result.original_count == 0

    @pytest.mark.asyncio
    async def test_token_estimation(self, trimmer: MessageTrimmer) -> None:
        """Test token count estimation."""
        messages = [
            HumanMessage(content="a" * 100),  # ~25 tokens
        ]

        result = await trimmer.trim(messages)

        # Should estimate tokens based on content length
        assert result.estimated_tokens_before > 0
        assert result.estimated_tokens_after > 0

    @pytest.mark.asyncio
    async def test_trims_to_token_limit(self) -> None:
        """Test trimming when token limit is exceeded."""
        trimmer = MessageTrimmer(
            max_messages=100,  # High message limit
            max_tokens=50,  # Low token limit
        )
        messages = [
            HumanMessage(content="a" * 100),  # ~25 tokens each
            AIMessage(content="b" * 100),
            HumanMessage(content="c" * 100),
            AIMessage(content="d" * 100),
        ]

        result = await trimmer.trim(messages)

        # Should be trimmed due to token limit
        assert result.estimated_tokens_after <= 50 + 50  # Allow some overhead

    @pytest.mark.asyncio
    async def test_summarization_when_enabled(self) -> None:
        """Test that summarization is called when enabled."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Summary of conversation")
        )

        trimmer = MessageTrimmer(
            max_messages=2,
            summarize_trimmed=True,
        )
        messages = [
            HumanMessage(content="First message"),
            AIMessage(content="First response"),
            HumanMessage(content="Second message"),
            AIMessage(content="Second response"),
            HumanMessage(content="Third message"),
        ]

        result = await trimmer.trim(messages, llm=mock_llm)

        assert result.summary_added is True
        mock_llm.ainvoke.assert_called_once()

    def test_get_stats(self, trimmer: MessageTrimmer) -> None:
        """Test getting trimmer statistics."""
        stats = trimmer.get_stats()

        assert "total_trims" in stats
        assert "total_messages_trimmed" in stats
        assert "config" in stats
        assert stats["config"]["max_messages"] == 5

    @pytest.mark.asyncio
    async def test_stats_update_on_trim(
        self, trimmer: MessageTrimmer, sample_messages: list[HumanMessage | AIMessage]
    ) -> None:
        """Test that stats update after trimming."""
        await trimmer.trim(sample_messages)

        stats = trimmer.get_stats()
        assert stats["total_trims"] == 1
        assert stats["total_messages_trimmed"] > 0

    def test_reset_stats(self, trimmer: MessageTrimmer) -> None:
        """Test resetting statistics."""
        trimmer._total_trims = 10
        trimmer._total_messages_trimmed = 50

        trimmer.reset_stats()

        stats = trimmer.get_stats()
        assert stats["total_trims"] == 0
        assert stats["total_messages_trimmed"] == 0


class TestConversationWindow:
    """Tests for ConversationWindow class."""

    @pytest.fixture
    def window(self) -> ConversationWindow:
        """Create conversation window."""
        return ConversationWindow(max_messages=5, max_tokens=1000)

    def test_add_message(self, window: ConversationWindow) -> None:
        """Test adding a single message."""
        window.add(HumanMessage(content="Hello"))

        assert window.message_count == 1

    def test_add_many_messages(self, window: ConversationWindow) -> None:
        """Test adding multiple messages."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi!"),
        ]
        window.add_many(messages)

        assert window.message_count == 2

    @pytest.mark.asyncio
    async def test_get_messages_trims(self, window: ConversationWindow) -> None:
        """Test that get_messages trims when needed."""
        for i in range(10):
            window.add(HumanMessage(content=f"Message {i}"))

        messages = await window.get_messages()

        assert len(messages) <= 5

    def test_clear(self, window: ConversationWindow) -> None:
        """Test clearing the window."""
        window.add(HumanMessage(content="Hello"))
        window.clear()

        assert window.message_count == 0


class TestCreateTrimmer:
    """Tests for create_trimmer factory function."""

    def test_aggressive_preset(self) -> None:
        """Test aggressive trimmer configuration."""
        trimmer = create_trimmer(preset="aggressive")

        assert trimmer.max_messages == 10
        assert trimmer.max_tokens == 4000

    def test_balanced_preset(self) -> None:
        """Test balanced trimmer configuration."""
        trimmer = create_trimmer(preset="balanced")

        assert trimmer.max_messages == 20
        assert trimmer.max_tokens == 8000

    def test_conservative_preset(self) -> None:
        """Test conservative trimmer configuration."""
        trimmer = create_trimmer(preset="conservative")

        assert trimmer.max_messages == 50
        assert trimmer.max_tokens == 16000

    def test_with_summarization(self) -> None:
        """Test enabling summarization."""
        trimmer = create_trimmer(preset="balanced", with_summarization=True)

        assert trimmer.summarize_trimmed is True
