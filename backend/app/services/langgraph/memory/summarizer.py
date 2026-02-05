"""Conversation Summarizer for LangGraph agents.

Provides conversation summarization to manage long-running
agent sessions without losing critical context.

Features:
- Automatic detection of when summarization is needed
- Preservation of system messages and recent context
- Key decision extraction
- Incremental summarization for very long conversations

Usage:
    from app.services.langgraph.memory.summarizer import ConversationSummarizer

    summarizer = ConversationSummarizer()

    if await summarizer.should_summarize(messages):
        result = await summarizer.summarize(messages)
        # result.summary contains the condensed history
        # result.preserved_messages contains recent messages to keep
"""

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


@dataclass
class SummarizationResult:
    """Result of conversation summarization."""

    summary: str
    preserved_messages: list[BaseMessage]
    original_count: int
    summarized_count: int
    estimated_token_savings: int


@dataclass
class SummarizationConfig:
    """Configuration for conversation summarization."""

    # Trigger thresholds
    max_messages: int = 50
    max_estimated_tokens: int = 4000
    context_capacity_threshold: float = 0.85  # 85% of context

    # Preservation settings
    preserve_system_messages: bool = True
    preserve_last_n_turns: int = 5  # A turn = human + AI message

    # Summarization settings
    summary_max_tokens: int = 500
    include_key_decisions: bool = True


class ConversationSummarizer:
    """
    Summarize long conversations to manage context.

    Detects when conversations are getting too long and
    condenses older messages into a summary while preserving
    recent context and system messages.
    """

    # Rough token estimation: ~0.25 tokens per character
    TOKENS_PER_CHAR = 0.25

    def __init__(
        self,
        config: SummarizationConfig | None = None,
        llm: Any = None,
    ) -> None:
        """
        Initialize conversation summarizer.

        Args:
            config: Summarization configuration
            llm: LLM to use for summarization (defaults to Claude)
        """
        self.config = config or SummarizationConfig()
        self._llm = llm

    async def _get_llm(self) -> Any:
        """Get LLM for summarization."""
        if self._llm is None:
            from app.services.llm.clients import get_llm_router

            self._llm = get_llm_router().claude
        return self._llm

    def _estimate_tokens(self, messages: list[BaseMessage]) -> int:
        """Estimate token count for messages."""
        total_chars = 0
        for msg in messages:
            content = msg.content
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                # Handle multimodal content
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        total_chars += len(item["text"])
        return int(total_chars * self.TOKENS_PER_CHAR)

    async def should_summarize(
        self,
        messages: list[BaseMessage],
        context_limit: int | None = None,
    ) -> bool:
        """
        Determine if conversation needs summarization.

        Args:
            messages: Current conversation messages
            context_limit: Optional context window limit

        Returns:
            True if summarization is recommended
        """
        # Check message count
        if len(messages) > self.config.max_messages:
            return True

        # Check token estimate
        estimated_tokens = self._estimate_tokens(messages)
        if estimated_tokens > self.config.max_estimated_tokens:
            return True

        # Check context capacity if limit provided
        if context_limit:
            capacity_used = estimated_tokens / context_limit
            if capacity_used > self.config.context_capacity_threshold:
                return True

        return False

    def _partition_messages(
        self, messages: list[BaseMessage]
    ) -> tuple[list[BaseMessage], list[BaseMessage], list[BaseMessage]]:
        """
        Partition messages into system, to-summarize, and preserve groups.

        Args:
            messages: All conversation messages

        Returns:
            Tuple of (system_messages, messages_to_summarize, messages_to_preserve)
        """
        system_messages: list[BaseMessage] = []
        other_messages: list[BaseMessage] = []

        for msg in messages:
            if isinstance(msg, SystemMessage) and self.config.preserve_system_messages:
                system_messages.append(msg)
            else:
                other_messages.append(msg)

        # Calculate how many messages to preserve (turns * 2 for human + AI)
        preserve_count = self.config.preserve_last_n_turns * 2

        if len(other_messages) <= preserve_count:
            # Not enough messages to summarize
            return system_messages, [], other_messages

        to_summarize = other_messages[:-preserve_count]
        to_preserve = other_messages[-preserve_count:]

        return system_messages, to_summarize, to_preserve

    def _extract_key_decisions(
        self, messages: list[BaseMessage]
    ) -> list[str]:
        """
        Extract key decisions and conclusions from messages.

        Args:
            messages: Messages to extract decisions from

        Returns:
            List of key decisions/conclusions
        """
        decisions: list[str] = []

        # Look for decision indicators in AI messages
        decision_indicators = [
            "decided to",
            "conclusion:",
            "recommendation:",
            "selected",
            "chose",
            "the answer is",
            "tier 1",
            "tier 2",
            "tier 3",
            "qualified",
            "disqualified",
            "approved",
            "rejected",
        ]

        for msg in messages:
            if isinstance(msg, AIMessage):
                content = str(msg.content).lower()
                for indicator in decision_indicators:
                    if indicator in content:
                        # Extract the sentence containing the decision
                        sentences = str(msg.content).split(".")
                        for sentence in sentences:
                            if indicator in sentence.lower():
                                clean_sentence = sentence.strip()
                                if clean_sentence and len(clean_sentence) < 200:
                                    decisions.append(clean_sentence)
                                break
                        break

        return decisions[:10]  # Limit to 10 key decisions

    async def summarize(
        self, messages: list[BaseMessage]
    ) -> SummarizationResult:
        """
        Summarize conversation, preserving recent context.

        Args:
            messages: Full conversation messages

        Returns:
            SummarizationResult with summary and preserved messages
        """
        system_msgs, to_summarize, to_preserve = self._partition_messages(messages)

        if not to_summarize:
            # Nothing to summarize
            return SummarizationResult(
                summary="",
                preserved_messages=messages,
                original_count=len(messages),
                summarized_count=0,
                estimated_token_savings=0,
            )

        # Build summary prompt
        summary_content = self._build_summary_content(to_summarize)

        # Extract key decisions if configured
        key_decisions = []
        if self.config.include_key_decisions:
            key_decisions = self._extract_key_decisions(to_summarize)

        # Generate summary with LLM
        llm = await self._get_llm()
        summary_prompt = f"""Summarize this conversation excerpt concisely. Focus on:
1. Main topics discussed
2. Key findings or data gathered
3. Decisions made or conclusions reached
4. Any important context for continuing the conversation

Keep the summary under {self.config.summary_max_tokens} tokens.

Conversation to summarize:
{summary_content}

{"Key decisions identified: " + "; ".join(key_decisions) if key_decisions else ""}
"""

        try:
            response = await llm.ainvoke([HumanMessage(content=summary_prompt)])
            summary_text = str(response.content)
        except Exception:
            # Fallback to simple extraction if LLM fails
            summary_text = self._fallback_summary(to_summarize, key_decisions)

        # Calculate token savings
        original_tokens = self._estimate_tokens(to_summarize)
        summary_tokens = int(len(summary_text) * self.TOKENS_PER_CHAR)
        savings = max(0, original_tokens - summary_tokens)

        # Build preserved message list with summary as first AI message
        preserved = list(system_msgs)
        if summary_text:
            summary_msg = AIMessage(
                content=f"[Conversation Summary]\n{summary_text}"
            )
            preserved.append(summary_msg)
        preserved.extend(to_preserve)

        return SummarizationResult(
            summary=summary_text,
            preserved_messages=preserved,
            original_count=len(messages),
            summarized_count=len(to_summarize),
            estimated_token_savings=savings,
        )

    def _build_summary_content(self, messages: list[BaseMessage]) -> str:
        """Build content string for summarization."""
        parts = []
        for msg in messages:
            role = "Human" if isinstance(msg, HumanMessage) else "Assistant"
            content = str(msg.content)[:500]  # Truncate long messages
            parts.append(f"{role}: {content}")
        return "\n\n".join(parts)

    def _fallback_summary(
        self,
        messages: list[BaseMessage],
        key_decisions: list[str],
    ) -> str:
        """Generate fallback summary without LLM."""
        parts = [f"Previous conversation ({len(messages)} messages summarized):"]

        # Add first and last few messages
        if len(messages) >= 2:
            first_content = str(messages[0].content)[:100]
            parts.append(f"- Started with: {first_content}...")

        if key_decisions:
            parts.append("- Key decisions: " + "; ".join(key_decisions[:5]))

        if len(messages) >= 2:
            last_content = str(messages[-1].content)[:100]
            parts.append(f"- Most recently: {last_content}...")

        return "\n".join(parts)

    async def incremental_summarize(
        self,
        existing_summary: str,
        new_messages: list[BaseMessage],
    ) -> str:
        """
        Incrementally update an existing summary.

        Useful for very long conversations where re-summarizing
        everything would be expensive.

        Args:
            existing_summary: Previous summary
            new_messages: New messages since last summary

        Returns:
            Updated summary incorporating new messages
        """
        if not new_messages:
            return existing_summary

        new_content = self._build_summary_content(new_messages)
        key_decisions = self._extract_key_decisions(new_messages)

        llm = await self._get_llm()
        update_prompt = f"""Update this conversation summary with new information.
Keep the updated summary concise (under {self.config.summary_max_tokens} tokens).

Existing summary:
{existing_summary}

New conversation to incorporate:
{new_content}

{"New decisions: " + "; ".join(key_decisions) if key_decisions else ""}

Provide the updated summary:"""

        try:
            response = await llm.ainvoke([HumanMessage(content=update_prompt)])
            return str(response.content)
        except Exception:
            # Append key decisions to existing summary
            if key_decisions:
                return f"{existing_summary}\n\nAdditional: {'; '.join(key_decisions)}"
            return existing_summary
