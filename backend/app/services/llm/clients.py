"""LLM client routing for multi-model support.

Routes to appropriate model based on task:
- Claude: personalization, synthesis, generation, research (quality)
- Cerebras/DeepSeek: lookup, fast tasks (speed)
- OpenRouter: fallback for all
"""

from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from app.core.config import settings


class LLMRouter:
    """Route to appropriate LLM based on task requirements."""

    # Task types that require high-quality output
    QUALITY_TASKS = {"personalization", "synthesis", "generation", "research"}

    def __init__(self) -> None:
        """Initialize all LLM clients."""
        self._claude: ChatAnthropic | None = None
        self._cerebras: ChatOpenAI | None = None
        self._deepseek: ChatOpenAI | None = None
        self._openrouter: ChatOpenAI | None = None

    @property
    def claude(self) -> ChatAnthropic:
        """Lazy-load Claude client."""
        if self._claude is None:
            self._claude = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                api_key=settings.anthropic_api_key,
                max_tokens=4096,
            )
        return self._claude

    @property
    def cerebras(self) -> ChatOpenAI:
        """Lazy-load Cerebras client."""
        if self._cerebras is None:
            self._cerebras = ChatOpenAI(
                base_url=settings.cerebras_api_base,
                api_key=settings.cerebras_api_key,
                model="llama-3.3-70b",
                max_tokens=2048,
            )
        return self._cerebras

    @property
    def deepseek(self) -> ChatOpenAI:
        """Lazy-load DeepSeek client."""
        if self._deepseek is None:
            self._deepseek = ChatOpenAI(
                base_url="https://api.deepseek.com/v1",
                api_key=settings.deepseek_api_key,
                model="deepseek-chat",
                max_tokens=2048,
            )
        return self._deepseek

    @property
    def openrouter(self) -> ChatOpenAI:
        """Lazy-load OpenRouter client (fallback)."""
        if self._openrouter is None:
            self._openrouter = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key,
                model="anthropic/claude-3.5-sonnet",
                max_tokens=4096,
            )
        return self._openrouter

    def get_model(
        self,
        task: str,
        fallback: bool = False,
    ) -> ChatAnthropic | ChatOpenAI:
        """
        Get appropriate model for task type.

        Args:
            task: Task type (personalization, synthesis, lookup, etc.)
            fallback: If True, use OpenRouter regardless of task

        Returns:
            LLM client instance
        """
        if fallback:
            return self.openrouter

        if task in self.QUALITY_TASKS:
            return self.claude

        return self.cerebras


@lru_cache
def get_llm_router() -> LLMRouter:
    """Get cached LLMRouter instance."""
    return LLMRouter()


# Singleton instance
llm_router = LLMRouter()
