"""Memory management for LangGraph agents.

Provides:
- MessageTrimmer: Trim conversation history to prevent context overflow
- Short-term memory management with optional summarization
- SemanticMemory: Long-term pattern storage and semantic search
- UserMemoryStore: Cross-thread user preferences and context
- ConversationSummarizer: Intelligent conversation compression
"""

from app.services.langgraph.memory.semantic_store import SemanticMemory, semantic_memory
from app.services.langgraph.memory.summarizer import (
    ConversationSummarizer,
    SummarizationConfig,
    SummarizationResult,
)
from app.services.langgraph.memory.trimmer import MessageTrimmer, TrimResult
from app.services.langgraph.memory.user_store import (
    UserContext,
    UserMemoryStore,
    user_memory,
)

__all__ = [
    # Trimmer
    "MessageTrimmer",
    "TrimResult",
    # Semantic memory
    "SemanticMemory",
    "semantic_memory",
    # User memory
    "UserMemoryStore",
    "UserContext",
    "user_memory",
    # Summarizer
    "ConversationSummarizer",
    "SummarizationConfig",
    "SummarizationResult",
]
