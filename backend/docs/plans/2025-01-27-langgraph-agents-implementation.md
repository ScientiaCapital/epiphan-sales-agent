# LangGraph Sales Intelligence Agents - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build 4 LangGraph agents for BDR sales intelligence - script selection, lead research, email personalization, and competitor intelligence.

**Architecture:** Each agent is a LangGraph StateGraph with defined nodes, edges, and tools. LLM routing uses Claude for quality tasks, Cerebras/DeepSeek for speed. Agents share state schemas and can chain (Research → Email).

**Tech Stack:** LangGraph 0.2+, LangChain 0.3+, langchain-anthropic, httpx for API clients, BeautifulSoup for scraping.

---

## Phase 1: LLM Clients & Routing

### Task 1.1: Create LLM Client Infrastructure

**Files:**
- Create: `app/services/llm/__init__.py`
- Create: `app/services/llm/clients.py`
- Test: `tests/unit/test_llm_clients.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_llm_clients.py
"""Tests for LLM client routing."""

from unittest.mock import patch, MagicMock
import pytest


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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_llm_clients.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.llm'"

**Step 3: Write minimal implementation**

```python
# app/services/llm/__init__.py
"""LLM client services."""

from app.services.llm.clients import LLMRouter, llm_router

__all__ = ["LLMRouter", "llm_router"]
```

```python
# app/services/llm/clients.py
"""LLM client routing for multi-model support.

Routes to appropriate model based on task:
- Claude: personalization, synthesis, generation (quality)
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

    def __init__(self):
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
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_llm_clients.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add app/services/llm/ tests/unit/test_llm_clients.py
git commit -m "feat: add LLM client routing for multi-model support"
```

---

## Phase 2: Competitor Intelligence Agent

### Task 2.1: Create Agent State Schemas

**Files:**
- Create: `app/services/langgraph/states.py`
- Test: `tests/unit/test_langgraph_states.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_langgraph_states.py
"""Tests for LangGraph state schemas."""

import pytest
from typing import get_type_hints


class TestCompetitorIntelState:
    """Tests for CompetitorIntelState."""

    def test_state_has_required_fields(self):
        """Test that state has all required fields."""
        from app.services.langgraph.states import CompetitorIntelState

        hints = get_type_hints(CompetitorIntelState)

        assert "competitor_name" in hints
        assert "context" in hints
        assert "query_type" in hints
        assert "battlecard" in hints
        assert "response" in hints
        assert "proof_points" in hints

    def test_state_can_be_instantiated(self):
        """Test that state can be created with valid data."""
        from app.services.langgraph.states import CompetitorIntelState

        state: CompetitorIntelState = {
            "competitor_name": "blackmagic",
            "context": "They said ATEM is cheaper",
            "query_type": "claim",
            "battlecard": None,
            "relevant_differentiators": [],
            "response": "",
            "proof_points": [],
            "follow_up_question": None,
        }

        assert state["competitor_name"] == "blackmagic"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_langgraph_states.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# app/services/langgraph/states.py
"""LangGraph state schemas for all agents."""

from typing import TypedDict

from app.data.lead_schemas import Lead
from app.data.schemas import CompetitorBattlecard, PersonaProfile


class CompetitorIntelState(TypedDict):
    """State for Competitor Intelligence Agent."""

    # Inputs
    competitor_name: str
    context: str
    query_type: str  # "claim" | "objection" | "comparison"

    # Intermediate
    battlecard: CompetitorBattlecard | None
    relevant_differentiators: list[dict]

    # Output
    response: str
    proof_points: list[str]
    follow_up_question: str | None


class ScriptSelectionState(TypedDict):
    """State for Script Selection Agent."""

    # Inputs
    lead: Lead
    persona_match: str | None
    trigger: str | None
    call_type: str  # "warm" | "cold"

    # Intermediate
    base_script: dict | None
    lead_context: str | None
    persona_profile: PersonaProfile | None

    # Output
    personalized_script: str
    talking_points: list[str]
    objection_responses: list[dict]


class ResearchBrief(TypedDict):
    """Synthesized research output."""

    company_overview: str
    recent_news: list[dict]
    talking_points: list[str]
    risk_factors: list[str]
    linkedin_summary: str | None


class LeadResearchState(TypedDict):
    """State for Lead Research Agent."""

    # Inputs
    lead: Lead
    research_depth: str  # "quick" | "deep"

    # Tool outputs
    apollo_data: dict | None
    clearbit_data: dict | None
    news_articles: list[dict]
    linkedin_context: str | None

    # Output
    research_brief: ResearchBrief | None
    talking_points: list[str]
    risk_factors: list[str]


class EmailPersonalizationState(TypedDict):
    """State for Email Personalization Agent."""

    # Inputs
    lead: Lead
    research_brief: ResearchBrief | None
    persona: PersonaProfile | None
    sequence_step: int  # 1-4
    email_type: str  # pattern_interrupt, pain_point, breakup, nurture

    # Intermediate
    pain_points: list[str]
    personalization_hooks: list[str]

    # Output
    subject_line: str
    email_body: str
    follow_up_note: str | None
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_langgraph_states.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/langgraph/states.py tests/unit/test_langgraph_states.py
git commit -m "feat: add LangGraph state schemas for all agents"
```

---

### Task 2.2: Create Competitor Tools

**Files:**
- Create: `app/services/langgraph/tools/__init__.py`
- Create: `app/services/langgraph/tools/competitor_tools.py`
- Test: `tests/unit/test_competitor_tools.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_competitor_tools.py
"""Tests for competitor intelligence tools."""

import pytest


class TestGetBattlecard:
    """Tests for get_battlecard tool."""

    def test_returns_battlecard_for_valid_competitor(self):
        """Test returning battlecard for known competitor."""
        from app.services.langgraph.tools.competitor_tools import get_battlecard

        result = get_battlecard("blackmagic")

        assert result is not None
        assert result["id"] == "blackmagic_atem"
        assert "key_differentiators" in result

    def test_returns_none_for_unknown_competitor(self):
        """Test returning None for unknown competitor."""
        from app.services.langgraph.tools.competitor_tools import get_battlecard

        result = get_battlecard("unknown_competitor_xyz")

        assert result is None

    def test_matches_partial_name(self):
        """Test matching partial competitor name."""
        from app.services.langgraph.tools.competitor_tools import get_battlecard

        result = get_battlecard("atem")

        assert result is not None
        assert "blackmagic" in result["id"].lower() or "atem" in result["name"].lower()


class TestSearchDifferentiators:
    """Tests for search_differentiators tool."""

    def test_finds_differentiators_by_keyword(self):
        """Test finding differentiators by keyword."""
        from app.services.langgraph.tools.competitor_tools import search_differentiators

        result = search_differentiators("blackmagic_atem", "recording")

        assert len(result) > 0
        assert any("recording" in str(d).lower() for d in result)

    def test_returns_empty_for_no_match(self):
        """Test returning empty list when no match."""
        from app.services.langgraph.tools.competitor_tools import search_differentiators

        result = search_differentiators("blackmagic_atem", "xyznonexistent")

        assert result == []


class TestGetClaimResponses:
    """Tests for get_claim_responses tool."""

    def test_returns_claim_responses(self):
        """Test returning claim responses for competitor."""
        from app.services.langgraph.tools.competitor_tools import get_claim_responses

        result = get_claim_responses("blackmagic_atem")

        assert len(result) > 0
        assert all("claim" in r and "response" in r for r in result)

    def test_filters_by_keyword(self):
        """Test filtering claim responses by keyword."""
        from app.services.langgraph.tools.competitor_tools import get_claim_responses

        result = get_claim_responses("blackmagic_atem", keyword="cheaper")

        assert len(result) > 0
        assert any("cheaper" in r["claim"].lower() for r in result)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_competitor_tools.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/services/langgraph/tools/__init__.py
"""LangGraph tools for agents."""

from app.services.langgraph.tools.competitor_tools import (
    get_battlecard,
    search_differentiators,
    get_claim_responses,
)

__all__ = [
    "get_battlecard",
    "search_differentiators",
    "get_claim_responses",
]
```

```python
# app/services/langgraph/tools/competitor_tools.py
"""Tools for Competitor Intelligence Agent."""

from typing import Any

from app.data.competitors import COMPETITORS, get_competitor_by_id


def get_battlecard(competitor_name: str) -> dict[str, Any] | None:
    """
    Get battlecard for a competitor by name.

    Args:
        competitor_name: Full or partial competitor name

    Returns:
        Battlecard dict or None if not found
    """
    name_lower = competitor_name.lower().strip()

    # Try exact ID match first
    for competitor in COMPETITORS:
        if competitor.id == name_lower or name_lower in competitor.id:
            return _battlecard_to_dict(competitor)

    # Try name match
    for competitor in COMPETITORS:
        if name_lower in competitor.name.lower():
            return _battlecard_to_dict(competitor)

    # Try company match
    for competitor in COMPETITORS:
        if name_lower in competitor.company.lower():
            return _battlecard_to_dict(competitor)

    return None


def search_differentiators(
    competitor_id: str,
    keyword: str,
) -> list[dict[str, str]]:
    """
    Search differentiators by keyword.

    Args:
        competitor_id: Competitor ID
        keyword: Keyword to search for

    Returns:
        List of matching differentiators
    """
    competitor = get_competitor_by_id(competitor_id)
    if not competitor:
        return []

    keyword_lower = keyword.lower()
    matches = []

    for diff in competitor.key_differentiators:
        searchable = f"{diff.feature} {diff.competitor_capability} {diff.pearl_capability} {diff.why_it_matters}".lower()
        if keyword_lower in searchable:
            matches.append({
                "feature": diff.feature,
                "competitor": diff.competitor_capability,
                "pearl": diff.pearl_capability,
                "why_it_matters": diff.why_it_matters,
            })

    return matches


def get_claim_responses(
    competitor_id: str,
    keyword: str | None = None,
) -> list[dict[str, str]]:
    """
    Get claim/response pairs for a competitor.

    Args:
        competitor_id: Competitor ID
        keyword: Optional keyword to filter claims

    Returns:
        List of claim/response dicts
    """
    competitor = get_competitor_by_id(competitor_id)
    if not competitor:
        return []

    responses = []
    for claim in competitor.claims:
        if keyword:
            if keyword.lower() not in claim.claim.lower():
                continue
        responses.append({
            "claim": claim.claim,
            "response": claim.response,
        })

    return responses


def _battlecard_to_dict(competitor) -> dict[str, Any]:
    """Convert CompetitorBattlecard to dict."""
    return {
        "id": competitor.id,
        "name": competitor.name,
        "company": competitor.company,
        "price_range": competitor.price_range,
        "positioning": competitor.positioning,
        "market_context": competitor.market_context,
        "when_to_compete": competitor.when_to_compete,
        "when_to_walk_away": competitor.when_to_walk_away,
        "key_differentiators": [
            {
                "feature": d.feature,
                "competitor": d.competitor_capability,
                "pearl": d.pearl_capability,
                "why_it_matters": d.why_it_matters,
            }
            for d in competitor.key_differentiators
        ],
        "claims": [
            {"claim": c.claim, "response": c.response}
            for c in competitor.claims
        ],
        "talk_tracks": [
            {"scenario": t.scenario, "track": t.track}
            for t in competitor.talk_tracks
        ] if competitor.talk_tracks else [],
    }
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_competitor_tools.py -v`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add app/services/langgraph/tools/ tests/unit/test_competitor_tools.py
git commit -m "feat: add competitor intelligence tools"
```

---

### Task 2.3: Create Competitor Intelligence Agent

**Files:**
- Update: `app/services/langgraph/agents/__init__.py`
- Create: `app/services/langgraph/agents/competitor_intel.py`
- Test: `tests/unit/test_competitor_intel_agent.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_competitor_intel_agent.py
"""Tests for Competitor Intelligence Agent."""

from unittest.mock import patch, MagicMock, AsyncMock
import pytest


class TestCompetitorIntelAgent:
    """Tests for CompetitorIntelAgent."""

    @pytest.mark.asyncio
    async def test_responds_to_claim(self):
        """Test agent responds to competitor claim."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
                content="Calculate TCO: ATEM + PC + software = $3,000-5,000. Pearl Nano at $1,999 is all-in-one."
            ))

            result = await agent.run(
                competitor_name="blackmagic",
                context="The prospect said ATEM is cheaper upfront",
                query_type="claim",
            )

        assert result["response"] != ""
        assert "battlecard" in result
        assert isinstance(result["proof_points"], list)

    @pytest.mark.asyncio
    async def test_handles_unknown_competitor(self):
        """Test agent handles unknown competitor gracefully."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        result = await agent.run(
            competitor_name="unknown_xyz",
            context="They mentioned unknown_xyz",
            query_type="comparison",
        )

        assert "not found" in result["response"].lower() or result["battlecard"] is None

    @pytest.mark.asyncio
    async def test_includes_follow_up_question(self):
        """Test agent includes follow-up question."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
                content="Response here. FOLLOW_UP: What's their current recording setup?"
            ))

            result = await agent.run(
                competitor_name="blackmagic",
                context="They use ATEM",
                query_type="objection",
            )

        # Agent should extract or generate follow-up
        assert "follow_up_question" in result


class TestCompetitorIntelAgentGraph:
    """Tests for the LangGraph structure."""

    def test_graph_has_required_nodes(self):
        """Test that graph has all required nodes."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()
        graph = agent.graph

        # Check nodes exist
        assert "lookup_battlecard" in graph.nodes
        assert "match_context" in graph.nodes
        assert "generate_response" in graph.nodes

    def test_graph_compiles(self):
        """Test that graph compiles without error."""
        from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

        agent = CompetitorIntelAgent()

        # Should not raise
        compiled = agent.compiled_graph
        assert compiled is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_competitor_intel_agent.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/services/langgraph/agents/__init__.py
"""LangGraph agents for Epiphan Sales Intelligence."""

from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent

__all__ = ["CompetitorIntelAgent"]
```

```python
# app/services/langgraph/agents/competitor_intel.py
"""Competitor Intelligence Agent.

Provides real-time battlecard responses during sales calls.
Uses fast LLM (Cerebras/DeepSeek) for <2s response time.
"""

from typing import Any

from langgraph.graph import StateGraph, END

from app.services.langgraph.states import CompetitorIntelState
from app.services.langgraph.tools.competitor_tools import (
    get_battlecard,
    search_differentiators,
    get_claim_responses,
)
from app.services.llm.clients import llm_router


class CompetitorIntelAgent:
    """
    Agent for real-time competitor intelligence.

    Flow:
    1. lookup_battlecard - Find competitor battlecard
    2. match_context - Match context to relevant differentiators
    3. generate_response - Generate response using LLM
    """

    def __init__(self):
        """Initialize agent with LLM and graph."""
        self.llm = llm_router.get_model("lookup")  # Fast model
        self._graph: StateGraph | None = None
        self._compiled: Any = None

    @property
    def graph(self) -> StateGraph:
        """Build and return the state graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    @property
    def compiled_graph(self) -> Any:
        """Get compiled graph for execution."""
        if self._compiled is None:
            self._compiled = self.graph.compile()
        return self._compiled

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        graph = StateGraph(CompetitorIntelState)

        # Add nodes
        graph.add_node("lookup_battlecard", self._lookup_battlecard)
        graph.add_node("match_context", self._match_context)
        graph.add_node("generate_response", self._generate_response)

        # Add edges
        graph.set_entry_point("lookup_battlecard")
        graph.add_edge("lookup_battlecard", "match_context")
        graph.add_edge("match_context", "generate_response")
        graph.add_edge("generate_response", END)

        return graph

    async def run(
        self,
        competitor_name: str,
        context: str,
        query_type: str = "claim",
    ) -> dict[str, Any]:
        """
        Run the agent to generate competitor response.

        Args:
            competitor_name: Name of competitor mentioned
            context: What the prospect said
            query_type: Type of query (claim, objection, comparison)

        Returns:
            Dict with response, proof_points, follow_up_question
        """
        initial_state: CompetitorIntelState = {
            "competitor_name": competitor_name,
            "context": context,
            "query_type": query_type,
            "battlecard": None,
            "relevant_differentiators": [],
            "response": "",
            "proof_points": [],
            "follow_up_question": None,
        }

        # Run the graph
        final_state = await self.compiled_graph.ainvoke(initial_state)

        return {
            "response": final_state["response"],
            "proof_points": final_state["proof_points"],
            "follow_up_question": final_state["follow_up_question"],
            "battlecard": final_state["battlecard"],
        }

    async def _lookup_battlecard(
        self,
        state: CompetitorIntelState,
    ) -> dict[str, Any]:
        """Look up battlecard for competitor."""
        battlecard = get_battlecard(state["competitor_name"])
        return {"battlecard": battlecard}

    async def _match_context(
        self,
        state: CompetitorIntelState,
    ) -> dict[str, Any]:
        """Match context to relevant differentiators and claims."""
        if not state["battlecard"]:
            return {"relevant_differentiators": [], "proof_points": []}

        competitor_id = state["battlecard"]["id"]
        context_lower = state["context"].lower()

        # Find relevant differentiators
        differentiators = []
        for diff in state["battlecard"]["key_differentiators"]:
            searchable = f"{diff['feature']} {diff['competitor']} {diff['pearl']}".lower()
            # Check for keyword overlap
            context_words = set(context_lower.split())
            diff_words = set(searchable.split())
            if context_words.intersection(diff_words):
                differentiators.append(diff)

        # Get claim responses if query is about a claim
        proof_points = []
        if state["query_type"] == "claim":
            claims = get_claim_responses(competitor_id)
            for claim in claims:
                if any(word in claim["claim"].lower() for word in context_lower.split()):
                    proof_points.append(claim["response"])

        return {
            "relevant_differentiators": differentiators[:3],  # Top 3
            "proof_points": proof_points[:3],
        }

    async def _generate_response(
        self,
        state: CompetitorIntelState,
    ) -> dict[str, Any]:
        """Generate response using LLM."""
        if not state["battlecard"]:
            return {
                "response": f"I don't have specific battlecard data for {state['competitor_name']}. Let me get back to you with details.",
                "follow_up_question": "Can you tell me more about what they're offering?",
            }

        # Build prompt
        prompt = self._build_prompt(state)

        # Call LLM
        response = await self.llm.ainvoke(prompt)
        response_text = response.content

        # Extract follow-up if present
        follow_up = None
        if "FOLLOW_UP:" in response_text:
            parts = response_text.split("FOLLOW_UP:")
            response_text = parts[0].strip()
            follow_up = parts[1].strip() if len(parts) > 1 else None

        return {
            "response": response_text,
            "follow_up_question": follow_up,
        }

    def _build_prompt(self, state: CompetitorIntelState) -> str:
        """Build prompt for LLM."""
        battlecard = state["battlecard"]

        differentiators_text = ""
        if state["relevant_differentiators"]:
            differentiators_text = "\n".join([
                f"- {d['feature']}: They have {d['competitor']}, we have {d['pearl']}. {d['why_it_matters']}"
                for d in state["relevant_differentiators"]
            ])

        proof_points_text = ""
        if state["proof_points"]:
            proof_points_text = "\n".join([f"- {p}" for p in state["proof_points"]])

        return f"""You are a sales rep for Epiphan Video. A prospect mentioned competitor {battlecard['name']}.

COMPETITOR INFO:
- Name: {battlecard['name']}
- Positioning: {battlecard['positioning']}
- Price Range: {battlecard['price_range']}

RELEVANT DIFFERENTIATORS:
{differentiators_text or "No specific differentiators matched."}

EXISTING PROOF POINTS:
{proof_points_text or "No pre-written responses matched."}

PROSPECT SAID: "{state['context']}"

QUERY TYPE: {state['query_type']}

Generate a concise, confident response (2-3 sentences max) that addresses their concern.
Focus on value, not bashing the competitor.
End with FOLLOW_UP: and a discovery question to keep the conversation going.

RESPONSE:"""


# Singleton instance
competitor_intel_agent = CompetitorIntelAgent()
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_competitor_intel_agent.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add app/services/langgraph/agents/ tests/unit/test_competitor_intel_agent.py
git commit -m "feat: add Competitor Intelligence Agent with LangGraph"
```

---

## Phase 3: Script Selection Agent

### Task 3.1: Create Script Tools

**Files:**
- Create: `app/services/langgraph/tools/script_tools.py`
- Update: `app/services/langgraph/tools/__init__.py`
- Test: `tests/unit/test_script_tools.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_script_tools.py
"""Tests for script selection tools."""

import pytest


class TestGetWarmScript:
    """Tests for get_warm_script tool."""

    def test_returns_script_for_valid_persona_trigger(self):
        """Test returning script for valid persona and trigger."""
        from app.services.langgraph.tools.script_tools import get_warm_script

        result = get_warm_script("av_director", "demo_request")

        assert result is not None
        assert "opener" in result or "script" in result.lower() or "hook" in result

    def test_returns_none_for_invalid_persona(self):
        """Test returning None for invalid persona."""
        from app.services.langgraph.tools.script_tools import get_warm_script

        result = get_warm_script("invalid_persona", "demo_request")

        assert result is None


class TestGetColdScript:
    """Tests for get_cold_script tool."""

    def test_returns_script_for_valid_vertical(self):
        """Test returning script for valid vertical."""
        from app.services.langgraph.tools.script_tools import get_cold_script

        result = get_cold_script("higher_ed")

        assert result is not None
        assert "pattern_interrupt" in result
        assert "value_hook" in result

    def test_returns_none_for_invalid_vertical(self):
        """Test returning None for invalid vertical."""
        from app.services.langgraph.tools.script_tools import get_cold_script

        result = get_cold_script("invalid_vertical")

        assert result is None


class TestGetPersonaProfile:
    """Tests for get_persona_profile tool."""

    def test_returns_profile_for_valid_persona(self):
        """Test returning profile for valid persona ID."""
        from app.services.langgraph.tools.script_tools import get_persona_profile

        result = get_persona_profile("av_director")

        assert result is not None
        assert result["id"] == "av_director"
        assert "pain_points" in result
        assert "objections" in result

    def test_returns_none_for_invalid_persona(self):
        """Test returning None for invalid persona."""
        from app.services.langgraph.tools.script_tools import get_persona_profile

        result = get_persona_profile("invalid_xyz")

        assert result is None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_script_tools.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/services/langgraph/tools/script_tools.py
"""Tools for Script Selection Agent."""

from typing import Any

from app.data.personas import PERSONAS, get_persona_by_id
from app.data.scripts import COLD_CALL_SCRIPTS, get_script_by_vertical
from app.data.persona_warm_scripts import get_warm_script_for_persona


def get_warm_script(
    persona_id: str,
    trigger: str,
) -> dict[str, Any] | None:
    """
    Get warm call script for persona and trigger.

    Args:
        persona_id: Persona ID (av_director, ld_director, etc.)
        trigger: Trigger type (demo_request, content_download, etc.)

    Returns:
        Script dict or None if not found
    """
    script = get_warm_script_for_persona(persona_id, trigger)
    if not script:
        return None

    return {
        "persona_id": script.persona_id,
        "trigger": script.trigger,
        "opener": script.opener,
        "acknowledge": script.acknowledge,
        "context_bridge": script.context_bridge,
        "value_hook": script.value_hook,
        "discovery_questions": script.discovery_questions,
        "meeting_ask": script.meeting_ask,
        "objection_handlers": [
            {"objection": o.objection, "response": o.response}
            for o in script.objection_handlers
        ] if script.objection_handlers else [],
    }


def get_cold_script(vertical: str) -> dict[str, Any] | None:
    """
    Get cold call script for vertical.

    Args:
        vertical: Vertical ID (higher_ed, corporate, etc.)

    Returns:
        Script dict or None if not found
    """
    script = get_script_by_vertical(vertical)
    if not script:
        return None

    return {
        "vertical": script.vertical,
        "target_persona": script.target_persona,
        "pattern_interrupt": script.pattern_interrupt,
        "value_hook": script.value_hook,
        "pain_question": script.pain_question,
        "permission": script.permission,
        "pivot": script.pivot,
        "why_it_works": script.why_it_works,
        "objection_pivots": [
            {"objection": o.objection, "response": o.response}
            for o in script.objection_pivots
        ] if script.objection_pivots else [],
    }


def get_persona_profile(persona_id: str) -> dict[str, Any] | None:
    """
    Get full persona profile.

    Args:
        persona_id: Persona ID

    Returns:
        Persona profile dict or None if not found
    """
    persona = get_persona_by_id(persona_id)
    if not persona:
        return None

    return {
        "id": persona.id,
        "title": persona.title,
        "title_variations": persona.title_variations,
        "reports_to": persona.reports_to,
        "team_size": persona.team_size,
        "budget_authority": persona.budget_authority,
        "verticals": persona.verticals,
        "day_to_day": persona.day_to_day,
        "kpis": persona.kpis,
        "pain_points": [
            {
                "point": p.point,
                "emotional_impact": p.emotional_impact,
                "solution": p.solution,
            }
            for p in persona.pain_points
        ],
        "hot_buttons": persona.hot_buttons,
        "discovery_questions": persona.discovery_questions,
        "objections": [
            {"objection": o.objection, "response": o.response}
            for o in persona.objections
        ],
        "buying_signals": {
            "high": persona.buying_signals.high,
            "medium": persona.buying_signals.medium,
        },
    }
```

Update `__init__.py`:

```python
# app/services/langgraph/tools/__init__.py
"""LangGraph tools for agents."""

from app.services.langgraph.tools.competitor_tools import (
    get_battlecard,
    search_differentiators,
    get_claim_responses,
)
from app.services.langgraph.tools.script_tools import (
    get_warm_script,
    get_cold_script,
    get_persona_profile,
)

__all__ = [
    # Competitor tools
    "get_battlecard",
    "search_differentiators",
    "get_claim_responses",
    # Script tools
    "get_warm_script",
    "get_cold_script",
    "get_persona_profile",
]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_script_tools.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add app/services/langgraph/tools/ tests/unit/test_script_tools.py
git commit -m "feat: add script selection tools"
```

---

### Task 3.2: Create Script Selection Agent

**Files:**
- Create: `app/services/langgraph/agents/script_selection.py`
- Update: `app/services/langgraph/agents/__init__.py`
- Test: `tests/unit/test_script_selection_agent.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_script_selection_agent.py
"""Tests for Script Selection Agent."""

from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from app.data.lead_schemas import Lead


@pytest.fixture
def sample_lead():
    """Sample lead for testing."""
    return Lead(
        hubspot_id="123",
        email="sarah.johnson@university.edu",
        first_name="Sarah",
        last_name="Johnson",
        company="State University",
        title="AV Director",
    )


class TestScriptSelectionAgent:
    """Tests for ScriptSelectionAgent."""

    @pytest.mark.asyncio
    async def test_generates_warm_script(self, sample_lead):
        """Test agent generates personalized warm script."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
                content="Hey Sarah, this is Tim from Epiphan Video..."
            ))

            result = await agent.run(
                lead=sample_lead,
                persona_match="av_director",
                trigger="demo_request",
                call_type="warm",
            )

        assert result["personalized_script"] != ""
        assert isinstance(result["talking_points"], list)
        assert isinstance(result["objection_responses"], list)

    @pytest.mark.asyncio
    async def test_generates_cold_script(self, sample_lead):
        """Test agent generates personalized cold script."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
                content="Hey Sarah, this is Tim from Epiphan Video - got 30 seconds?"
            ))

            result = await agent.run(
                lead=sample_lead,
                persona_match="av_director",
                trigger=None,
                call_type="cold",
            )

        assert result["personalized_script"] != ""
        assert "Sarah" in result["personalized_script"] or mock_llm.ainvoke.called

    @pytest.mark.asyncio
    async def test_includes_objection_handlers(self, sample_lead):
        """Test agent includes relevant objection handlers."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()

        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
                content="Personalized script here"
            ))

            result = await agent.run(
                lead=sample_lead,
                persona_match="av_director",
                trigger="demo_request",
                call_type="warm",
            )

        assert len(result["objection_responses"]) > 0


class TestScriptSelectionAgentGraph:
    """Tests for the LangGraph structure."""

    def test_graph_has_required_nodes(self):
        """Test that graph has all required nodes."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()
        graph = agent.graph

        assert "load_script" in graph.nodes
        assert "extract_context" in graph.nodes
        assert "personalize" in graph.nodes

    def test_graph_compiles(self):
        """Test that graph compiles without error."""
        from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

        agent = ScriptSelectionAgent()
        compiled = agent.compiled_graph

        assert compiled is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_script_selection_agent.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/services/langgraph/agents/script_selection.py
"""Script Selection Agent.

Personalizes warm and cold call scripts based on lead context.
Uses Claude for high-quality personalization.
"""

from typing import Any

from langgraph.graph import StateGraph, END

from app.data.lead_schemas import Lead
from app.services.langgraph.states import ScriptSelectionState
from app.services.langgraph.tools.script_tools import (
    get_warm_script,
    get_cold_script,
    get_persona_profile,
)
from app.services.llm.clients import llm_router


class ScriptSelectionAgent:
    """
    Agent for selecting and personalizing call scripts.

    Flow:
    1. load_script - Load base script (warm or cold)
    2. extract_context - Extract relevant lead context
    3. personalize - Personalize script with LLM
    """

    def __init__(self):
        """Initialize agent with LLM and graph."""
        self.llm = llm_router.get_model("personalization")  # Claude
        self._graph: StateGraph | None = None
        self._compiled: Any = None

    @property
    def graph(self) -> StateGraph:
        """Build and return the state graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    @property
    def compiled_graph(self) -> Any:
        """Get compiled graph for execution."""
        if self._compiled is None:
            self._compiled = self.graph.compile()
        return self._compiled

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        graph = StateGraph(ScriptSelectionState)

        # Add nodes
        graph.add_node("load_script", self._load_script)
        graph.add_node("extract_context", self._extract_context)
        graph.add_node("personalize", self._personalize)

        # Add edges
        graph.set_entry_point("load_script")
        graph.add_edge("load_script", "extract_context")
        graph.add_edge("extract_context", "personalize")
        graph.add_edge("personalize", END)

        return graph

    async def run(
        self,
        lead: Lead,
        persona_match: str | None,
        trigger: str | None,
        call_type: str = "warm",
    ) -> dict[str, Any]:
        """
        Run the agent to generate personalized script.

        Args:
            lead: Lead to generate script for
            persona_match: Matched persona ID
            trigger: Trigger type (for warm calls)
            call_type: "warm" or "cold"

        Returns:
            Dict with personalized_script, talking_points, objection_responses
        """
        initial_state: ScriptSelectionState = {
            "lead": lead,
            "persona_match": persona_match,
            "trigger": trigger,
            "call_type": call_type,
            "base_script": None,
            "lead_context": None,
            "persona_profile": None,
            "personalized_script": "",
            "talking_points": [],
            "objection_responses": [],
        }

        # Run the graph
        final_state = await self.compiled_graph.ainvoke(initial_state)

        return {
            "personalized_script": final_state["personalized_script"],
            "talking_points": final_state["talking_points"],
            "objection_responses": final_state["objection_responses"],
        }

    async def _load_script(
        self,
        state: ScriptSelectionState,
    ) -> dict[str, Any]:
        """Load the base script based on call type."""
        persona_profile = None
        if state["persona_match"]:
            persona_profile = get_persona_profile(state["persona_match"])

        if state["call_type"] == "warm" and state["trigger"]:
            base_script = get_warm_script(
                state["persona_match"] or "av_director",
                state["trigger"],
            )
        else:
            # Cold call - use vertical from persona
            vertical = "corporate"  # default
            if persona_profile and persona_profile.get("verticals"):
                vertical = persona_profile["verticals"][0]
            base_script = get_cold_script(vertical)

        # Extract objection handlers from script
        objection_responses = []
        if base_script:
            handlers = base_script.get("objection_handlers") or base_script.get("objection_pivots", [])
            objection_responses = handlers[:5]  # Top 5

        return {
            "base_script": base_script,
            "persona_profile": persona_profile,
            "objection_responses": objection_responses,
        }

    async def _extract_context(
        self,
        state: ScriptSelectionState,
    ) -> dict[str, Any]:
        """Extract relevant context from lead."""
        lead = state["lead"]
        persona = state["persona_profile"]

        context_parts = []

        # Lead info
        if lead.first_name:
            context_parts.append(f"Name: {lead.first_name}")
        if lead.company:
            context_parts.append(f"Company: {lead.company}")
        if lead.title:
            context_parts.append(f"Title: {lead.title}")

        # Persona pain points
        if persona and persona.get("pain_points"):
            top_pains = persona["pain_points"][:3]
            pain_text = ", ".join([p["point"] for p in top_pains])
            context_parts.append(f"Likely pain points: {pain_text}")

        # Talking points from persona hot buttons
        talking_points = []
        if persona and persona.get("hot_buttons"):
            talking_points = persona["hot_buttons"][:5]

        return {
            "lead_context": "\n".join(context_parts),
            "talking_points": talking_points,
        }

    async def _personalize(
        self,
        state: ScriptSelectionState,
    ) -> dict[str, Any]:
        """Personalize script using LLM."""
        if not state["base_script"]:
            return {
                "personalized_script": "No script template available for this combination.",
            }

        prompt = self._build_prompt(state)
        response = await self.llm.ainvoke(prompt)

        return {
            "personalized_script": response.content,
        }

    def _build_prompt(self, state: ScriptSelectionState) -> str:
        """Build prompt for personalization."""
        script = state["base_script"]
        lead = state["lead"]

        if state["call_type"] == "warm":
            script_text = f"""
OPENER: {script.get('opener', '')}
ACKNOWLEDGE: {script.get('acknowledge', '')}
CONTEXT BRIDGE: {script.get('context_bridge', '')}
VALUE HOOK: {script.get('value_hook', '')}
MEETING ASK: {script.get('meeting_ask', '')}
"""
        else:
            script_text = f"""
PATTERN INTERRUPT: {script.get('pattern_interrupt', '')}
VALUE HOOK: {script.get('value_hook', '')}
PAIN QUESTION: {script.get('pain_question', '')}
PERMISSION: {script.get('permission', '')}
PIVOT: {script.get('pivot', '')}
"""

        return f"""You are a BDR for Epiphan Video. Personalize this call script for the specific lead.

LEAD CONTEXT:
{state['lead_context']}

BASE SCRIPT:
{script_text}

INSTRUCTIONS:
1. Replace [Name] with {lead.first_name or 'there'}
2. Make the value hook specific to their company/role if possible
3. Keep the structure but make it natural
4. Output ONLY the personalized script, ready to read

PERSONALIZED SCRIPT:"""


# Singleton instance
script_selection_agent = ScriptSelectionAgent()
```

Update `__init__.py`:

```python
# app/services/langgraph/agents/__init__.py
"""LangGraph agents for Epiphan Sales Intelligence."""

from app.services.langgraph.agents.competitor_intel import CompetitorIntelAgent
from app.services.langgraph.agents.script_selection import ScriptSelectionAgent

__all__ = ["CompetitorIntelAgent", "ScriptSelectionAgent"]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_script_selection_agent.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add app/services/langgraph/agents/ tests/unit/test_script_selection_agent.py
git commit -m "feat: add Script Selection Agent with LangGraph"
```

---

## Phase 4-7: Remaining Implementation

The remaining phases follow the same TDD pattern. Due to length, I'll summarize:

### Phase 4: Enrichment Clients
- Task 4.1: Apollo.io client (`app/services/enrichment/apollo.py`)
- Task 4.2: Clearbit client (`app/services/enrichment/clearbit.py`)
- Task 4.3: Web scraper utilities (`app/services/enrichment/scraper.py`)

### Phase 5: Lead Research Agent
- Task 5.1: Research tools (`app/services/langgraph/tools/research_tools.py`)
- Task 5.2: Lead Research Agent (`app/services/langgraph/agents/lead_research.py`)

### Phase 6: Email Personalization Agent
- Task 6.1: Email tools (`app/services/langgraph/tools/email_tools.py`)
- Task 6.2: Email Personalization Agent (`app/services/langgraph/agents/email_personalization.py`)

### Phase 7: API Endpoints
- Task 7.1: Agent API routes (`app/api/routes/agents.py`)
- Task 7.2: Batch processing endpoints
- Task 7.3: Register routes in main.py

---

## Verification

After all phases complete:

```bash
# Run all tests
cd backend && uv run pytest tests/unit/ -v

# Lint check
cd backend && uv run ruff check app/services/langgraph/ app/services/llm/ app/services/enrichment/ app/api/routes/agents.py

# Type check (optional)
cd backend && uv run mypy app/services/langgraph/
```

Expected: 72+ new tests passing, 0 lint errors.
