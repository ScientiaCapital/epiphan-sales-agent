"""Tests for LLM client routing."""




class TestLLMRouter:
    """Tests for LLMRouter."""

    def test_get_model_returns_claude_for_personalization(self):
        """Test that personalization tasks use Claude."""
        from app.services.llm.clients import LLMRouter

        router = LLMRouter()
        model = router.get_model("personalization")

        assert model == router.claude

    def test_get_model_returns_claude_for_synthesis(self):
        """Test that synthesis tasks use Claude."""
        from app.services.llm.clients import LLMRouter

        router = LLMRouter()
        model = router.get_model("synthesis")

        assert model == router.claude

    def test_get_model_returns_claude_for_generation(self):
        """Test that generation tasks use Claude."""
        from app.services.llm.clients import LLMRouter

        router = LLMRouter()
        model = router.get_model("generation")

        assert model == router.claude

    def test_get_model_returns_claude_for_research(self):
        """Test that research tasks use Claude."""
        from app.services.llm.clients import LLMRouter

        router = LLMRouter()
        model = router.get_model("research")

        assert model == router.claude

    def test_get_model_returns_cerebras_for_fast_tasks(self):
        """Test that fast tasks use Cerebras."""
        from app.services.llm.clients import LLMRouter

        router = LLMRouter()
        model = router.get_model("lookup")

        assert model == router.cerebras

    def test_get_model_returns_openrouter_for_fallback(self):
        """Test that fallback flag uses OpenRouter."""
        from app.services.llm.clients import LLMRouter

        router = LLMRouter()
        model = router.get_model("personalization", fallback=True)

        assert model == router.openrouter

    def test_router_initializes_all_clients(self):
        """Test that router initializes all LLM clients."""
        from app.services.llm.clients import LLMRouter

        router = LLMRouter()

        assert router.claude is not None
        assert router.cerebras is not None
        assert router.deepseek is not None
        assert router.openrouter is not None

    def test_quality_tasks_constant(self):
        """Test QUALITY_TASKS contains expected task types."""
        from app.services.llm.clients import LLMRouter

        expected = {"personalization", "synthesis", "generation", "research"}
        assert expected == LLMRouter.QUALITY_TASKS

    def test_get_model_unknown_task_uses_cerebras(self):
        """Test that unknown task types default to Cerebras (fast)."""
        from app.services.llm.clients import LLMRouter

        router = LLMRouter()
        model = router.get_model("unknown_task")

        assert model == router.cerebras
