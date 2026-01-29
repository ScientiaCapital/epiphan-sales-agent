# LangGraph Patterns Reference

Key patterns from the LangChain/LangGraph documentation, adapted for the Epiphan Sales Agent.

---

## When to Use Graph API vs Functional API

### Use Graph API (Our Choice)

- Complex decision trees and branching
- Parallel processing (enrichment tasks)
- Team collaboration (modular agent definitions)
- Explicit state management
- Multi-agent orchestration

### Use Functional API

- Sequential operations without complex logic
- Minimal code changes to existing procedural code
- Rapid prototyping
- Function-scoped state

**Our decision:** Graph API for all 5 agents due to multi-step workflows and conditional routing.

---

## Architecture Patterns

### 1. Orchestrator-Worker Pattern

Central orchestrator delegates to specialized workers.

```
┌──────────────────────────────────────────────────┐
│                  ORCHESTRATOR                     │
│                                                   │
│   Route by task type → Delegate → Synthesize     │
│                                                   │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│   │  Research   │  │   Script    │  │  Email  │ │
│   │   Worker    │  │   Worker    │  │ Worker  │ │
│   └─────────────┘  └─────────────┘  └─────────┘ │
└──────────────────────────────────────────────────┘
```

**Use for:** Multi-stage qualification process

### 2. Evaluator-Optimizer Pattern

One LLM generates, another evaluates; iterate until acceptable.

```
Generate → Evaluate → (Pass? → Output) or (Fail? → Refine → Generate)
```

**Use for:** Email/script quality validation

### 3. Routing Pattern

Initial classification directs inputs to specialized handlers.

```python
def route_by_persona(state):
    persona = state.get("persona_type")
    routing = {
        "av_director": "av_director_handler",
        "ld_director": "ld_director_handler",
        "technical_director": "technical_director_handler",
        # ... etc.
    }
    return routing.get(persona, "default_handler")
```

**Use for:** Persona-specific script selection

### 4. Prompt Chaining Pattern

Sequential LLM calls where each processes previous output.

```
Research → Extract Key Points → Personalize Script → Format Output
```

**Use for:** Research → personalization → email generation

---

## State Management

### TypedDict Schemas

Define explicit types for all state:

```python
from typing import TypedDict, Annotated
from operator import add

class QualificationState(TypedDict):
    lead_data: dict
    scores: dict
    tier: str
    messages: Annotated[list[dict], add]  # Accumulates
```

### Reducers

Control how updates are applied:

| Pattern | Behavior | Use Case |
|---------|----------|----------|
| Default | Replace value | Single values (tier, score) |
| `add` | Accumulate list | Messages, sources found |
| Custom | Merge dicts | Complex nested updates |

### Store Raw Data, Format on Output

```python
# Good: Store raw data
state["enrichment"] = {"apollo": {...}, "clearbit": {...}}

# Format when needed
def format_for_output(state):
    return f"Company: {state['enrichment']['clearbit']['name']}"
```

---

## Conditional Routing

### Basic Routing

```python
def route_by_tier(state) -> str:
    score = state.get("score", 0)
    if score >= 70:
        return "tier_1_handler"
    elif score >= 50:
        return "tier_2_handler"
    elif score >= 30:
        return "tier_3_handler"
    else:
        return "disqualify_handler"

graph.add_conditional_edges(
    "score_lead",
    route_by_tier,
    {
        "tier_1_handler": "tier_1_handler",
        "tier_2_handler": "tier_2_handler",
        "tier_3_handler": "tier_3_handler",
        "disqualify_handler": "disqualify_handler",
    }
)
```

### Command API (Combined Update + Route)

```python
from langgraph.types import Command

def qualify_lead(state):
    score = calculate_score(state)
    tier = assign_tier(score)

    return Command(
        update={"score": score, "tier": tier},
        goto=f"{tier.lower()}_handler"
    )
```

---

## Parallel Execution

### Send API for Map-Reduce

Process multiple items concurrently:

```python
from langgraph.types import Send

def process_leads_parallel(state):
    """Spawn parallel processing for each lead."""
    return [
        Send("process_single_lead", {"lead": lead})
        for lead in state["leads"]
    ]
```

### Async Parallel with asyncio

```python
import asyncio

async def enrich_parallel(state):
    """Run enrichment services in parallel."""
    tasks = [
        asyncio.create_task(apollo_enrich(state["email"])),
        asyncio.create_task(clearbit_enrich(state["domain"])),
        asyncio.create_task(scrape_website(state["website"])),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        "apollo_data": results[0] if not isinstance(results[0], Exception) else None,
        "clearbit_data": results[1] if not isinstance(results[1], Exception) else None,
        "scraped_data": results[2] if not isinstance(results[2], Exception) else None,
    }
```

---

## Persistence

### PostgresSaver for Production

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
compiled_graph = graph.compile(checkpointer=checkpointer)

# Each lead gets a unique thread_id
config = {"configurable": {"thread_id": f"lead_{lead_id}"}}
result = compiled_graph.invoke(input_state, config=config)
```

### Durability Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `"exit"` | Save only at end | Best performance |
| `"async"` | Async checkpointing | Balanced (recommended) |
| `"sync"` | Synchronous writes | Maximum safety |

### State Recovery

```python
# Get current state
state = compiled_graph.get_state(config)

# Get history
history = list(compiled_graph.get_state_history(config))

# Resume from checkpoint
result = compiled_graph.invoke(None, config=config)
```

---

## Streaming

### Five Streaming Modes

| Mode | Output | Use Case |
|------|--------|----------|
| `"updates"` | Changed state only | Efficient progress tracking |
| `"values"` | Full state snapshot | Complete visibility |
| `"messages"` | Token-by-token LLM output | Real-time user feedback |
| `"custom"` | Arbitrary events | Custom progress notifications |
| `"debug"` | Execution trace | Debugging |

### Implementation

```python
# Stream progress updates
async for event in compiled_graph.astream(inputs, stream_mode="updates"):
    print(f"Step completed: {event}")

# Stream custom events for UI
async for event in compiled_graph.astream(inputs, stream_mode="custom"):
    if event[0] == "custom":
        status = event[1]
        update_ui(status)
```

---

## Human-in-the-Loop

### Interrupt Before Action

```python
from langgraph.types import interrupt

def send_email_node(state):
    email = generate_email(state)

    # Pause for human review
    approval = interrupt({
        "action": "review_email",
        "email": email,
        "recipient": state["lead_email"]
    })

    if approval["approved"]:
        send_email(email, state["lead_email"])
        return {"email_sent": True}
    else:
        return {"email_sent": False, "reason": approval.get("reason")}
```

### Resume After Review

```python
# Human reviews and approves
result = compiled_graph.invoke(
    {"human_input": {"approved": True}},
    config=config
)
```

**Use Cases:**
- Approval before sending emails
- Review generated scripts
- Validate qualification scores
- Approve CRM updates

---

## Subgraph Composition

### Independent Subgraphs

Each agent has private state:

```python
# Research agent with own state
research_graph = StateGraph(ResearchState)
research_compiled = research_graph.compile()

# Parent calls research
def research_node(parent_state):
    research_input = {"query": parent_state["company"]}
    result = research_compiled.invoke(research_input)
    return {"enrichment": result}
```

### Shared State Subgraphs

When agents need shared context:

```python
# Script agent shares state with parent
def script_node(state):
    # Access shared state directly
    persona = state["persona"]
    research = state["enrichment"]
    script = select_script(persona, research)
    return {"script": script}
```

---

## Time-Travel Debugging

Analyze and replay agent decisions:

```python
# 1. Get execution history
config = {"configurable": {"thread_id": lead_id}}
history = list(compiled_graph.get_state_history(config))

# 2. Find problematic checkpoint
for i, state in enumerate(history):
    print(f"Step {i}: score={state.values.get('score')}, tier={state.values.get('tier')}")

# 3. Modify state
compiled_graph.update_state(
    config,
    {"vertical_score": 10}  # Adjust
)

# 4. Replay from modified state
result = compiled_graph.invoke(None, config=config)
```

**Use Cases:**
- Debug low qualification scores
- Test alternative persona approaches
- Replay with different enrichment data

---

## Memory Patterns

### Short-Term (Per Thread)

```python
class ConversationState(TypedDict):
    messages: Annotated[list[dict], add_messages]
    lead_context: dict
```

### Long-Term (Cross-Thread)

```python
from langgraph.store.postgres import PostgresStore

store = PostgresStore.from_conn_string(DATABASE_URL)

# Store reference customer
store.put(
    namespace=("reference_customers", "higher_ed"),
    key="nc_state",
    value={"rooms": 300, "team_size": 3}
)

# Retrieve across threads
results = store.search(
    namespace=("reference_customers",),
    query="university large room count"
)
```

---

## Error Handling Strategy

| Error Type | Handling |
|------------|----------|
| Transient (API timeout) | Automatic retry with backoff |
| LLM-recoverable (bad output) | State loop with refined prompt |
| User-fixable (missing info) | Interrupt for human input |
| Unexpected | Surface for debugging |

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
async def call_apollo(email: str):
    return await apollo_client.enrich(email)
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Storing formatted text in state | Inflexible | Store raw data |
| Ignoring reducers | Message loss | Use `Annotated[list, add]` |
| Blocking I/O | Slow execution | Use async |
| Complex nodes | Hard to debug | Single responsibility |
| Ignoring serialization | Checkpointing fails | JSON-serializable state |
| Global memory namespace | Collisions | Use tuples like `(user_id, "data")` |

---

## See Also

- [Agent Architecture](../architecture/agent-architecture.md) - Implementation details
- [DEEPAGENTS_REFERENCE.md](../DEEPAGENTS_REFERENCE.md) - DeepAgents framework
- [System Overview](../architecture/system-overview.md) - Full architecture
