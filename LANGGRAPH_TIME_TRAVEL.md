# LangGraph Time-Travel: Complete Guide

## Overview

LangGraph's time-travel functionality enables examining decision-making processes in non-deterministic systems (powered by language models) by allowing execution resumption from prior checkpoints. This supports three primary use cases:

1. **Understand Reasoning** - Trace through agent decisions and thought processes
2. **Debug Mistakes** - Identify where things went wrong in execution
3. **Explore Alternatives** - Test different paths without re-running from scratch

---

## Core Concepts

### What is Time Travel in LangGraph?

Time travel refers to the ability to:
- Pause execution at any checkpoint
- Review the state at that point
- Modify state values
- Resume execution from that modified checkpoint
- Explore alternative execution paths

This creates a branching history of executions, enabling non-linear debugging and exploration.

### Why It Matters

In non-deterministic systems (like LLM-powered agents), you often can't simply re-run the graph to reproduce a state because the LLM may generate different outputs. Time travel lets you:
- Lock in specific LLM outputs and test branches
- Understand why an agent made a particular decision
- Modify intermediate results and continue from there
- Compare outcomes of different choices

---

## State Replay Mechanisms

### Four-Step Execution Flow

Time travel follows a sequential four-step process:

#### Step 1: Initial Execution
```
Start → Execute graph via invoke() or stream() → Generate checkpoints
```
- Run the graph with starting inputs
- LangGraph automatically creates checkpoints at each node
- Each checkpoint captures the state at that execution point

#### Step 2: Checkpoint Identification
```
Get history → Locate specific checkpoint ID → Select target state
```
- Use `get_state_history()` to retrieve all prior states
- States are returned in **reverse chronological order** (newest first)
- Each state has an associated checkpoint ID

#### Step 3: Optional State Modification
```
Select checkpoint → Call update_state() → Modify values → Create fork
```
- Use `update_state()` to alter graph state at a checkpoint
- Creates a new checkpoint variant (fork in history)
- Maintains thread association with original execution

#### Step 4: Execution Resumption
```
Pass new config → Invoke with None input → Continue from checkpoint
```
- Call `invoke(None, new_config)` with the modified checkpoint config
- Graph resumes execution from that point forward
- Remaining nodes execute with updated state

### State Persistence

- **Thread ID**: UUID-based identifier tracking execution lineage
- **Checkpoint ID**: Unique identifier for each state snapshot
- **Config**: Contains thread_id and checkpoint_id for targeting specific execution points
- **History**: Maintains complete lineage enabling branching exploration

---

## Implementation Details

### Setup Requirements

#### Dependencies
```bash
pip install langchain_core langchain-anthropic langgraph
```

**Required packages:**
- `langchain_core` - Core abstractions
- `langchain-anthropic` - Claude LLM integration
- `langgraph` - Graph framework with checkpointing

#### Checkpointer Configuration
```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
```

- `InMemorySaver` - Local in-memory persistence (development/testing)
- Alternative: PostgreSQL-backed checkpointer for production

#### Thread Tracking
```python
import uuid

config = {"configurable": {"thread_id": str(uuid.uuid4())}}
```

- UUID-based thread identification
- Same thread_id across multiple invocations maintains history
- Different thread_ids create separate execution lineages

### Graph Architecture Pattern

Time travel works with any LangGraph structure, but typical pattern:

```
START → Node 1 (generate) → Node 2 (process) → Node 3 (finalize) → END
         ↓ Checkpoint 1     ↓ Checkpoint 2     ↓ Checkpoint 3
```

- Each node execution creates a checkpoint
- Checkpoints capture input and output states
- History enables rewinding to any checkpoint

### Key State Management Methods

| Method | Purpose | Return |
|--------|---------|--------|
| `invoke(input, config)` | Execute graph | Final state |
| `stream(input, config)` | Execute with streaming | State updates |
| `get_state_history(config)` | Retrieve execution history | List[StateSnapshot] |
| `update_state(config, values)` | Modify state at checkpoint | New config for modified checkpoint |

---

## Complete Code Example

### 1. Setup & Configuration

```python
import os
import getpass
import uuid
from typing_extensions import TypedDict, NotRequired

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

# Initialize API key
def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("ANTHROPIC_API_KEY")

# Initialize LLM
llm = ChatAnthropic(model="claude-sonnet-4-5-20250929")
```

**Explanation:**
- Sets up environment variables for API authentication
- Initializes Claude Sonnet model for LLM operations
- Imports necessary LangGraph components

### 2. Define State Schema

```python
class State(TypedDict):
    topic: NotRequired[str]
    joke: NotRequired[str]
```

**Explanation:**
- `TypedDict` defines the state structure
- `NotRequired` fields may or may not be present during execution
- State evolves as nodes add/modify values
- Type hints enable IDE autocomplete and validation

### 3. Define Node Functions

```python
def generate_topic(state: State):
    """Generate a joke topic using LLM"""
    msg = llm.invoke("Give me a funny topic for a joke")
    return {"topic": msg.content}

def write_joke(state: State):
    """Write a joke based on the generated topic"""
    msg = llm.invoke(f"Write a short joke about {state['topic']}")
    return {"joke": msg.content}
```

**Explanation:**
- **Node 1 (generate_topic)**: Uses Claude to generate a humorous topic
  - Input: Empty state
  - Output: State with `topic` field populated
  - Checkpoint created after execution

- **Node 2 (write_joke)**: Uses Claude to write joke based on topic
  - Input: State with `topic` from previous node
  - Output: State with `joke` field populated
  - Checkpoint created after execution

### 4. Build & Compile Graph

```python
workflow = StateGraph(State)
workflow.add_node("generate_topic", generate_topic)
workflow.add_node("write_joke", write_joke)

workflow.add_edge(START, "generate_topic")
workflow.add_edge("generate_topic", "write_joke")
workflow.add_edge("write_joke", END)

checkpointer = InMemorySaver()
graph = workflow.compile(checkpointer=checkpointer)
```

**Explanation:**
- `StateGraph(State)` - Create graph with defined state schema
- `add_node()` - Register node functions in graph
- `add_edge()` - Connect nodes and define execution flow
- `compile(checkpointer=)` - Enable checkpointing for time travel
  - Checkpointer required for `get_state_history()` and `update_state()`

### 5. Initial Execution

```python
# Create unique thread for this execution
config = {"configurable": {"thread_id": str(uuid.uuid4())}}

# Execute graph
initial_state = graph.invoke({}, config)

print(f"Topic: {initial_state['topic']}")
print(f"Joke: {initial_state['joke']}")
```

**Output example:**
```
Topic: Why did the quantum physicist break up with the chicken?
Joke: Because their relationship existed in a superposition of on and off,
and the chicken refused to decohere into commitment. When observed,
it always chose to leave.
```

---

## Time Travel in Action

### Step 1: Retrieve Execution History

```python
# Get all checkpoints for the thread
states = list(graph.get_state_history(config))

print(f"Total checkpoints: {len(states)}")
for i, state in enumerate(states):
    print(f"\nCheckpoint {i}:")
    print(f"  Config: {state.config}")
    print(f"  State values: {state.values}")
```

**Output example:**
```
Total checkpoints: 3

Checkpoint 0:
  Config: {'configurable': {'thread_id': 'abc123', 'checkpoint_id': 'v1'}}
  State values: {'topic': 'quantum chickens', 'joke': 'Why did...'}

Checkpoint 1:
  Config: {'configurable': {'thread_id': 'abc123', 'checkpoint_id': 'v0'}}
  State values: {'topic': 'quantum chickens'}

Checkpoint 2:
  Config: {'configurable': {'thread_id': 'abc123', 'checkpoint_id': 'v-1'}}
  State values: {}
```

**Key observations:**
- States returned in **reverse chronological order** (newest first)
- Checkpoint 0: Final state (after both nodes)
- Checkpoint 1: Intermediate state (after generate_topic, before write_joke)
- Checkpoint 2: Initial state (before any execution)

### Step 2: Select Checkpoint to Resume From

```python
# Select the state before the joke was written
selected_state = states[1]  # State after generate_topic

print(f"Resuming from topic: {selected_state.values['topic']}")
print(f"This state is before: write_joke node")
```

**Explanation:**
- Select checkpoint 1 (intermediate state)
- At this point, topic was generated but joke not yet written
- We can now modify the topic and regenerate the joke

### Step 3: Modify State at Checkpoint

```python
# Create a fork by modifying the topic
new_config = graph.update_state(
    selected_state.config,
    values={"topic": "chickens crossing the road"}
)

print(f"Original topic: {selected_state.values['topic']}")
print(f"Modified topic: chickens crossing the road")
print(f"New checkpoint config: {new_config}")
```

**Explanation:**
- `update_state()` takes the checkpoint config and new values
- Creates a new checkpoint with modified state
- Returns new config pointing to the forked checkpoint
- Original checkpoint remains unchanged (non-destructive)

### Step 4: Resume Execution from Modified Checkpoint

```python
# Execute remaining nodes from the modified checkpoint
result = graph.invoke(None, new_config)

print(f"\nOriginal joke about '{states[1].values['topic']}':")
print(f"{initial_state['joke']}\n")

print(f"New joke about 'chickens crossing the road':")
print(f"{result['joke']}")
```

**Output example:**
```
Original joke about 'quantum chickens':
Why did the quantum physicist break up with the chicken?
Because their relationship existed in a superposition...

New joke about 'chickens crossing the road':
Why did the chicken cross the road?
To escape the existential crisis on the other side!
```

**Key points:**
- `invoke(None, new_config)` - None as input means "continue from checkpoint"
- Graph skips generate_topic (already executed)
- Executes write_joke with new topic
- Fresh LLM call uses modified topic as input

---

## Advanced Patterns

### Multiple Modifications

```python
# Create multiple branches from same checkpoint
configs = []

topics = [
    "chickens",
    "ducks",
    "turkeys"
]

for topic in topics:
    new_config = graph.update_state(
        selected_state.config,
        values={"topic": topic}
    )
    configs.append((topic, new_config))

# Execute all branches
for topic, config in configs:
    result = graph.invoke(None, config)
    print(f"Joke about {topic}: {result['joke']}\n")
```

**Use case:** A/B testing different intermediate states

### State Modification with Partial Updates

```python
# Only update specific fields
new_config = graph.update_state(
    selected_state.config,
    values={"topic": "new topic"}
    # 'joke' remains None/unset
)
```

**Explanation:**
- Partial updates don't overwrite unspecified fields
- Allows precise state manipulation

### Exploring Decision Trees

```python
def explore_checkpoint_tree(graph, config, depth=0):
    """Recursively explore checkpoint branches"""
    states = list(graph.get_state_history(config))

    for i, state in enumerate(states):
        indent = "  " * depth
        print(f"{indent}Checkpoint {i}: {state.values}")

        # Could create branches here with update_state()

explore_checkpoint_tree(graph, config)
```

---

## Common Use Cases

### 1. Debugging Failed Execution

```python
# Run graph that might fail
try:
    result = graph.invoke({"input": data}, config)
except Exception as e:
    print(f"Failed at: {e}")

    # Review history to understand failure point
    states = list(graph.get_state_history(config))

    for state in states:
        print(f"State: {state.values}")
        # Identify where things went wrong
```

### 2. A/B Testing Agent Outputs

```python
# Get state before decision node
states = list(graph.get_state_history(config))
decision_checkpoint = states[1]

# Test two different values
for test_value in ["option_a", "option_b"]:
    test_config = graph.update_state(
        decision_checkpoint.config,
        values={"decision": test_value}
    )
    result = graph.invoke(None, test_config)
    print(f"Outcome with {test_value}: {result}")
```

### 3. Interactive Debugging

```python
def interactive_debug(graph, config):
    """Manual time travel through checkpoints"""
    states = list(graph.get_state_history(config))

    for i, state in enumerate(states):
        print(f"\n{i}. {state.values}")

        if input("Modify this state? (y/n): ").lower() == "y":
            new_value = input("New topic value: ")
            new_config = graph.update_state(
                state.config,
                values={"topic": new_value}
            )
            result = graph.invoke(None, new_config)
            print(f"Result: {result}")
            return

interactive_debug(graph, config)
```

---

## Best Practices

### 1. Use Meaningful Thread IDs

```python
# Bad: Random UUID without context
config = {"configurable": {"thread_id": str(uuid.uuid4())}}

# Good: Descriptive identifier
config = {"configurable": {"thread_id": f"user_123_conversation_456"}}
```

### 2. Enable Checkpointing in Compilation

```python
# Always compile with checkpointer for time travel
graph = workflow.compile(checkpointer=InMemorySaver())

# Without checkpointer, get_state_history() will fail
# graph = workflow.compile()  # Don't do this if using time travel
```

### 3. Store Config for Later Access

```python
# Save thread_id for future resumption
execution_record = {
    "thread_id": config["configurable"]["thread_id"],
    "timestamp": datetime.now(),
    "result": result
}

# Later: Retrieve history using saved thread_id
saved_config = {"configurable": {"thread_id": execution_record["thread_id"]}}
states = list(graph.get_state_history(saved_config))
```

### 4. Understand State Ordering

```python
# Remember: get_state_history() returns newest first
states = list(graph.get_state_history(config))
# states[0] = Final state
# states[-1] = Initial state

# To work chronologically, reverse the list
states_chronological = list(reversed(states))
```

### 5. Plan Your Graph Structure

```python
# Time travel works better with fine-grained checkpoints
# This creates more checkpoints:
workflow.add_edge(START, "step_1")
workflow.add_edge("step_1", "step_2")
workflow.add_edge("step_2", "step_3")
workflow.add_edge("step_3", END)

# vs. monolithic nodes:
# workflow.add_edge(START, "do_everything")
# workflow.add_edge("do_everything", END)
```

---

## Limitations & Considerations

### State History Lifetime

- **InMemorySaver**: Lost on process restart
- **Database checkpointer**: Persists across restarts
- **TTL**: Consider cleanup policies for long-running services

### Cost Implications

- Each `invoke()` call with modified state = new LLM calls
- Testing multiple branches can increase API costs
- Plan state modifications strategically

### Non-Determinism

- LLM outputs vary between calls (even with temperature=0)
- Use seeding or specific prompts for reproducibility
- Time travel doesn't guarantee identical outputs on resumption

### Performance

- Large state histories can consume memory (InMemorySaver)
- `get_state_history()` returns all checkpoints
- Consider pagination for long-running graphs

---

## Integration with Epiphan Sales Agent

### Potential Applications

**Lead Research Agent:**
```python
# Examine enrichment steps
states = list(graph.get_state_history(config))

# Modify lead data at checkpoint
new_config = graph.update_state(
    states[2].config,
    values={"company_size": "enterprise"}
)

# Re-run qualification with different data
result = graph.invoke(None, new_config)
```

**Qualification Agent:**
```python
# Debug ICP scoring at each dimension
# Modify one dimension and see impact on overall score
# Test different dimension weights
```

**Email Personalization Agent:**
```python
# Review persona selection step
# Change persona and regenerate email
# A/B test different persona choices
```

---

## Summary

LangGraph time travel enables:

1. **Checkpoint-based execution pausing** - Capture state at any point
2. **State history retrieval** - Access prior execution snapshots
3. **Non-destructive modification** - Fork execution paths
4. **Resumed execution** - Continue from modified checkpoints
5. **Debugging and exploration** - Understand LLM agent behavior

The four-step workflow (Execute → Identify → Modify → Resume) provides a powerful debugging and exploration framework for non-deterministic systems.
