"""Tests for ConversationSummarizer.

Tests summarization triggers, message partitioning, key decision extraction,
LLM-backed summarization, and fallback behavior.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.services.langgraph.memory.summarizer import (
    ConversationSummarizer,
    SummarizationConfig,
    SummarizationResult,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def summarizer() -> ConversationSummarizer:
    """Summarizer with default config and no LLM."""
    return ConversationSummarizer()


@pytest.fixture
def strict_config() -> SummarizationConfig:
    """Config with low thresholds for easy triggering."""
    return SummarizationConfig(
        max_messages=5,
        max_estimated_tokens=100,
        preserve_last_n_turns=2,
    )


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Mock LLM that returns a summary response."""
    llm = AsyncMock()
    response = MagicMock()
    response.content = "Summary of the conversation: discussed pricing and timeline."
    llm.ainvoke.return_value = response
    return llm


def _make_conversation(n_turns: int) -> list[BaseMessage]:
    """Create a conversation with n human-AI turn pairs."""
    messages: list[BaseMessage] = []
    for i in range(n_turns):
        messages.append(HumanMessage(content=f"Human message {i}"))
        messages.append(AIMessage(content=f"AI response {i}"))
    return messages


# =============================================================================
# should_summarize
# =============================================================================


class TestShouldSummarize:
    """Test summarization trigger logic."""

    @pytest.mark.asyncio
    async def test_false_when_under_thresholds(self, summarizer: ConversationSummarizer) -> None:
        """No summarization needed for short conversations."""
        messages = _make_conversation(3)
        assert await summarizer.should_summarize(messages) is False

    @pytest.mark.asyncio
    async def test_true_when_message_count_exceeds_max(
        self, strict_config: SummarizationConfig
    ) -> None:
        """Triggers when message count exceeds max_messages."""
        s = ConversationSummarizer(config=strict_config)
        messages = _make_conversation(4)  # 8 messages > max 5
        assert await s.should_summarize(messages) is True

    @pytest.mark.asyncio
    async def test_true_when_tokens_exceed_max(
        self, strict_config: SummarizationConfig
    ) -> None:
        """Triggers when estimated tokens exceed max."""
        s = ConversationSummarizer(config=strict_config)
        # Each message ~15 chars * 0.25 = ~4 tokens. 3 messages = ~12.
        # But max is 100, so use long messages.
        messages = [HumanMessage(content="x" * 500)]  # 125 tokens > 100
        assert await s.should_summarize(messages) is True

    @pytest.mark.asyncio
    async def test_true_when_context_capacity_exceeded(self) -> None:
        """Triggers when context capacity threshold exceeded."""
        config = SummarizationConfig(
            max_messages=1000,
            max_estimated_tokens=100000,
            context_capacity_threshold=0.5,
        )
        s = ConversationSummarizer(config=config)
        # 2000 chars * 0.25 = 500 tokens. context_limit=800 => 500/800 = 0.625 > 0.5
        messages = [HumanMessage(content="x" * 2000)]
        assert await s.should_summarize(messages, context_limit=800) is True


# =============================================================================
# _partition_messages
# =============================================================================


class TestPartitionMessages:
    """Test message partitioning logic."""

    def test_preserves_system_messages(self, summarizer: ConversationSummarizer) -> None:
        """System messages are separated out."""
        messages: list[BaseMessage] = [
            SystemMessage(content="You are a sales agent."),
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
            HumanMessage(content="What can you do?"),
            AIMessage(content="I can help with sales."),
        ]
        # Default preserve_last_n_turns=5 so everything preserved
        system, to_summarize, to_preserve = summarizer._partition_messages(messages)
        assert len(system) == 1
        assert system[0].content == "You are a sales agent."

    def test_keeps_last_n_turns(self) -> None:
        """Preserves last N turn pairs."""
        config = SummarizationConfig(preserve_last_n_turns=2)
        s = ConversationSummarizer(config=config)
        messages: list[BaseMessage] = _make_conversation(5)  # 10 messages
        system, to_summarize, to_preserve = s._partition_messages(messages)
        # 2 turns * 2 = 4 preserved, 6 to summarize
        assert len(to_preserve) == 4
        assert len(to_summarize) == 6
        assert len(system) == 0

    def test_returns_empty_to_summarize_when_too_few(self) -> None:
        """Not enough messages for summarization returns empty to_summarize."""
        config = SummarizationConfig(preserve_last_n_turns=5)
        s = ConversationSummarizer(config=config)
        messages = _make_conversation(3)  # 6 messages < 10 preserve slots
        system, to_summarize, to_preserve = s._partition_messages(messages)
        assert to_summarize == []
        assert to_preserve == messages


# =============================================================================
# _extract_key_decisions
# =============================================================================


class TestExtractKeyDecisions:
    """Test key decision extraction from messages."""

    def test_finds_decision_indicators(self, summarizer: ConversationSummarizer) -> None:
        """Finds decisions in AI messages."""
        messages: list[BaseMessage] = [
            AIMessage(content="We decided to go with Tier 1 classification."),
            HumanMessage(content="Sounds good."),
        ]
        decisions = summarizer._extract_key_decisions(messages)
        assert len(decisions) >= 1
        assert any("decided to" in d.lower() for d in decisions)

    def test_limits_to_10_decisions(self, summarizer: ConversationSummarizer) -> None:
        """Decision list is capped at 10."""
        messages: list[BaseMessage] = []
        for i in range(15):
            messages.append(AIMessage(content=f"We decided to do action {i}. Done."))
        decisions = summarizer._extract_key_decisions(messages)
        assert len(decisions) <= 10

    def test_ignores_human_messages(self, summarizer: ConversationSummarizer) -> None:
        """Only AI messages are scanned for decisions."""
        messages: list[BaseMessage] = [
            HumanMessage(content="I decided to buy."),
        ]
        decisions = summarizer._extract_key_decisions(messages)
        assert decisions == []


# =============================================================================
# summarize
# =============================================================================


class TestSummarize:
    """Test LLM-backed summarization."""

    @pytest.mark.asyncio
    async def test_summarize_with_llm(self, mock_llm: AsyncMock) -> None:
        """Summarize produces result with mocked LLM."""
        config = SummarizationConfig(preserve_last_n_turns=1)
        s = ConversationSummarizer(config=config, llm=mock_llm)
        messages = _make_conversation(5)  # 10 messages
        result = await s.summarize(messages)

        assert isinstance(result, SummarizationResult)
        assert result.summary != ""
        assert result.summarized_count > 0
        assert result.original_count == 10
        assert len(result.preserved_messages) > 0
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_no_messages_to_summarize(self, summarizer: ConversationSummarizer) -> None:
        """Summarize returns early when too few messages."""
        messages = _make_conversation(2)  # 4 messages, default preserve=5 turns
        result = await summarizer.summarize(messages)
        assert result.summarized_count == 0
        assert result.preserved_messages == messages


# =============================================================================
# _fallback_summary
# =============================================================================


class TestFallbackSummary:
    """Test fallback summary generation without LLM."""

    def test_generates_text(self, summarizer: ConversationSummarizer) -> None:
        """Fallback produces a summary string."""
        messages: list[BaseMessage] = _make_conversation(3)
        decisions = ["Decided to proceed with Tier 1"]
        summary = summarizer._fallback_summary(messages, decisions)
        assert "6 messages summarized" in summary
        assert "Decided to proceed with Tier 1" in summary

    def test_handles_empty_decisions(self, summarizer: ConversationSummarizer) -> None:
        """Fallback works with no decisions."""
        messages = _make_conversation(2)
        summary = summarizer._fallback_summary(messages, [])
        assert "4 messages summarized" in summary


# =============================================================================
# _build_summary_content
# =============================================================================


class TestBuildSummaryContent:
    """Test content building for summarization prompt."""

    def test_truncates_long_messages(self, summarizer: ConversationSummarizer) -> None:
        """Long messages are truncated to 500 chars."""
        messages: list[BaseMessage] = [HumanMessage(content="x" * 1000)]
        content = summarizer._build_summary_content(messages)
        # "Human: " prefix + 500 chars
        assert len(content) < 600


# =============================================================================
# incremental_summarize
# =============================================================================


class TestIncrementalSummarize:
    """Test incremental summary updates."""

    @pytest.mark.asyncio
    async def test_incremental_with_llm(self, mock_llm: AsyncMock) -> None:
        """Incremental summarize calls LLM with existing summary."""
        s = ConversationSummarizer(llm=mock_llm)
        new_messages = [HumanMessage(content="New topic"), AIMessage(content="Noted")]
        result = await s.incremental_summarize("Previous summary here", new_messages)
        assert result != ""
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_incremental_fallback_on_llm_failure(self) -> None:
        """Incremental falls back when LLM raises."""
        failing_llm = AsyncMock()
        failing_llm.ainvoke.side_effect = RuntimeError("LLM down")
        s = ConversationSummarizer(llm=failing_llm)

        new_messages = [AIMessage(content="We decided to go ahead.")]
        result = await s.incremental_summarize("Old summary", new_messages)
        assert "Old summary" in result

    @pytest.mark.asyncio
    async def test_incremental_no_new_messages(self, summarizer: ConversationSummarizer) -> None:
        """Returns existing summary when no new messages."""
        result = await summarizer.incremental_summarize("Existing", [])
        assert result == "Existing"
