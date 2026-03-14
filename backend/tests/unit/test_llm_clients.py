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

    def test_get_model_returns_openrouter_fast_for_lookup(self):
        """Test that fast tasks use OpenRouter fast (DeepSeek V3)."""
        from app.services.llm.clients import LLMRouter

        router = LLMRouter()
        model = router.get_model("lookup")

        assert model == router.openrouter_fast

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
        assert router.openrouter_fast is not None
        assert router.deepseek is not None
        assert router.openrouter is not None

    def test_quality_tasks_constant(self):
        """Test QUALITY_TASKS contains expected task types."""
        from app.services.llm.clients import LLMRouter

        expected = {"personalization", "synthesis", "generation", "research"}
        assert expected == LLMRouter.QUALITY_TASKS

    def test_get_model_unknown_task_uses_openrouter_fast(self):
        """Test that unknown task types default to OpenRouter fast."""
        from app.services.llm.clients import LLMRouter

        router = LLMRouter()
        model = router.get_model("unknown_task")

        assert model == router.openrouter_fast

    def test_openrouter_fast_uses_deepseek_model(self):
        """Test that openrouter_fast uses DeepSeek V3 model."""
        from app.services.llm.clients import LLMRouter

        router = LLMRouter()
        client = router.openrouter_fast

        assert client.model_name == "deepseek/deepseek-chat-v3-0324"
