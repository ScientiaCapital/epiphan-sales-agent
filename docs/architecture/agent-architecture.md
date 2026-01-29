# Agent Architecture

LangGraph patterns, state management, and best practices for the Epiphan Sales Agent.

---

## LangGraph Fundamentals

### Graph API vs Functional API

We use the **Graph API** because:
- Complex decision trees with branching
- Parallel processing (enrichment tasks)
- Multi-agent coordination
- Explicit state management

```python
from langgraph.graph import StateGraph

# Define graph
graph = StateGraph(QualificationState)
graph.add_node("classify_size", classify_size_node)
graph.add_node("classify_vertical", classify_vertical_node)
graph.add_edge("classify_size", "classify_vertical")
```

### State Management

State is defined using TypedDict with explicit types:

```python
from typing import TypedDict

class QualificationState(TypedDict):
    lead_data: dict
    company_size_score: int
    vertical_score: int
    tier: str
    confidence: float
```

**Reducers** control how state updates are applied:

```python
from operator import add
from typing import Annotated

class ResearchState(TypedDict):
    sources_found: Annotated[list[str], add]  # Accumulates via add
    current_summary: str  # Replaces (default behavior)
```

---

## Node Design Patterns

### Single Responsibility

Each node performs one action:

```python
def classify_size_node(state: QualificationState) -> dict:
    """Classify company by size - ONLY size classification."""
    employees = state["lead_data"].get("employees")
    category, score, reason = classify_company_size(employees)
    return {
        "company_size_score": score,
        "company_size_category": category,
        "company_size_reason": reason,
    }
```

### State Updates

Nodes return only the fields they update:

```python
# Good: Returns only updated fields
def process_node(state):
    result = do_work(state["input"])
    return {"output": result}  # Only "output" is updated

# Bad: Don't return entire state
def process_node(state):
    state["output"] = do_work(state["input"])
    return state  # Avoid this
```

---

## Conditional Routing

Route based on state values using edge functions:

```python
def route_by_tier(state: QualificationState) -> str:
    """Route lead to appropriate handler based on tier."""
    tier = state.get("tier", "NOT_ICP")
    if tier == "TIER_1":
        return "high_priority_handler"
    elif tier == "TIER_2":
        return "standard_handler"
    elif tier == "TIER_3":
        return "nurture_handler"
    else:
        return "disqualify_handler"

# Add conditional edge
graph.add_conditional_edges(
    "assign_tier",
    route_by_tier,
    {
        "high_priority_handler": "high_priority_handler",
        "standard_handler": "standard_handler",
        "nurture_handler": "nurture_handler",
        "disqualify_handler": "disqualify_handler",
    }
)
```

---

## Command API

Combine state updates and routing in one return:

```python
from langgraph.types import Command

def qualify_lead(state):
    score = calculate_icp_score(state)

    if score >= 70:
        return Command(
            update={"tier": "TIER_1", "score": score},
            goto="high_priority_queue"
        )
    elif score >= 50:
        return Command(
            update={"tier": "TIER_2", "score": score},
            goto="standard_queue"
        )
    else:
        return Command(
            update={"tier": "TIER_3", "score": score},
            goto="nurture_queue"
        )
```

---

## Parallel Execution

### Send API for Batch Processing

Process multiple leads concurrently:

```python
from langgraph.types import Send

def fan_out_leads(state):
    """Spawn parallel processing for each lead."""
    return [
        Send("process_single_lead", {"lead": lead})
        for lead in state["leads"]
    ]

graph.add_conditional_edges("start", fan_out_leads)
```

### Async Parallel Enrichment

```python
import asyncio

async def enrich_lead_parallel(state):
    """Run Apollo + Clearbit + web scraper in parallel."""
    apollo_task = asyncio.create_task(apollo_client.enrich(state["company"]))
    clearbit_task = asyncio.create_task(clearbit_client.enrich(state["email"]))
    scraper_task = asyncio.create_task(scraper.get_data(state["website"]))

    results = await asyncio.gather(apollo_task, clearbit_task, scraper_task)

    return {
        "apollo_data": results[0],
        "clearbit_data": results[1],
        "scraped_data": results[2],
    }
```

---

## Persistence

### Checkpointing with PostgresSaver

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Create checkpointer
checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)

# Compile graph with checkpointer
compiled_graph = graph.compile(checkpointer=checkpointer)

# Invoke with thread_id for persistence
config = {"configurable": {"thread_id": lead_id}}
result = compiled_graph.invoke(input_state, config=config)
```

### State Recovery

Resume from last checkpoint:

```python
# Get current state
state = compiled_graph.get_state(config)

# Get state history
history = list(compiled_graph.get_state_history(config))

# Resume from specific checkpoint
result = compiled_graph.invoke(None, config={
    "configurable": {
        "thread_id": lead_id,
        "checkpoint_id": checkpoint_id
    }
})
```

---

## Human-in-the-Loop

### Interrupt Patterns

Pause for human approval before actions:

```python
from langgraph.types import interrupt

def email_generation_node(state):
    email = generate_personalized_email(state)

    # Pause for human review
    reviewed = interrupt({
        "action": "review_email",
        "email": email,
        "lead": state["lead_name"]
    })

    return {"email": reviewed, "status": "approved"}
```

### Resume After Approval

```python
# After human reviews
config = {"configurable": {"thread_id": lead_id}}
result = compiled_graph.invoke(
    {"human_input": approved_email},
    config=config
)
```

**Use Cases:**
- Approval before sending outreach emails
- Review LLM-generated scripts
- Validate qualification scores
- Approve CRM updates

---

## Streaming

### Five Streaming Modes

| Mode | Output | Use Case |
|------|--------|----------|
| `updates` | Changed state only | Efficient progress tracking |
| `values` | Full state snapshot | Complete state visibility |
| `messages` | Token-by-token LLM output | Real-time user feedback |
| `custom` | Arbitrary events | Custom progress notifications |
| `debug` | Execution trace | Debugging |

### Streaming Implementation

```python
# Stream updates for progress tracking
async for event in compiled_graph.astream(inputs, stream_mode="updates"):
    print(f"Step: {event}")

# Stream custom events
async for event in compiled_graph.astream(inputs, stream_mode="custom"):
    if event == ("custom", "researching_apollo"):
        notify_user("Enriching from Apollo...")
    elif event == ("custom", "generating_script"):
        notify_user("Personalizing call script...")
```

---

## Subgraph Composition

### Independent Subgraphs

Each agent has its own state:

```python
# Research agent with private state
research_graph = StateGraph(ResearchState)
research_graph.add_node("search", search_node)
research_graph.add_node("synthesize", synthesize_node)
research_compiled = research_graph.compile()

# Parent orchestrator calls research as subgraph
def research_node(state):
    # Transform parent state → subgraph state
    research_input = {"query": state["lead"]["company"]}
    result = research_compiled.invoke(research_input)
    # Map results back to parent state
    return {"enrichment_data": result}
```

### Shared State Subgraphs

When agents need common context:

```python
# Script selection needs research results
def script_selection_node(state):
    # Access shared state directly
    persona = state["persona"]
    research = state["enrichment_data"]

    script = select_script(persona, research)
    return {"selected_script": script}
```

---

## Time-Travel Debugging

Analyze and replay agent decisions:

```python
# 1. Get execution history
history = list(compiled_graph.get_state_history(config))

# 2. Find problematic checkpoint
for state in history:
    print(f"Checkpoint: {state.config['checkpoint_id']}")
    print(f"Score: {state.values.get('score')}")

# 3. Modify state and replay
compiled_graph.update_state(
    config,
    {"vertical_score": 10}  # Adjust score
)

# 4. Resume from modified state
result = compiled_graph.invoke(None, config=config)
```

**Use Cases:**
- Debug why qualification score was low
- Test alternative persona approaches
- Replay with different enrichment data

---

## Memory Patterns

### Short-Term Memory (Per Thread)

Store conversation context within a single lead interaction:

```python
class ConversationState(TypedDict):
    messages: Annotated[list[dict], add_messages]  # Accumulates
    lead_context: dict
```

### Long-Term Memory (Cross-Thread)

Persist learnings across deals:

```python
from langgraph.store.postgres import PostgresStore

store = PostgresStore.from_conn_string(DATABASE_URL)

# Store reference customer data
store.put(
    namespace=("reference_customers", "higher_ed"),
    key="nc_state",
    value={"rooms": 300, "team_size": 3, "case_study": "..."}
)

# Retrieve across conversations
results = store.search(
    namespace=("reference_customers",),
    query="university with large room count"
)
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Storing formatted text in state | Inflexible for different outputs | Store raw data, format on output |
| Ignoring reducer logic | Message accumulation fails | Use `Annotated[list, add]` |
| Blocking I/O in nodes | Slow sequential execution | Use `async def` and `asyncio` |
| Over-complex nodes | Hard to debug and test | Single responsibility per node |
| Ignoring serialization | Checkpointing fails | All state must be JSON-serializable |

---

## See Also

- [System Overview](system-overview.md) - High-level architecture
- [Agents Overview](../agents/overview.md) - Individual agent details
- [LangGraph Patterns](../reference/langgraph-patterns.md) - Extended reference
- [DEEPAGENTS_REFERENCE.md](../DEEPAGENTS_REFERENCE.md) - DeepAgents framework
