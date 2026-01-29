# LangChain DeepAgents Framework Reference Guide

> **Last Updated:** 2026-01-29
> **Version:** LangGraph 1.0.7 | LangChain 1.2.7
> **Purpose:** Team reference for implementing intelligent AI agents

---

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start](#2-quick-start)
3. [Customization](#3-customization)
4. [Storage Backends](#4-storage-backends)
5. [Subagents](#5-subagents)
6. [Human-in-the-Loop](#6-human-in-the-loop)
7. [Long-Term Memory](#7-long-term-memory)
8. [Skills System](#8-skills-system)
9. [Middleware](#9-middleware)
10. [CLI Reference](#10-cli-reference)
11. [Application to Our Project](#11-application-to-our-project)

---

## 1. Overview

### What is DeepAgents?

**DeepAgents** is a Python library for building sophisticated AI agents capable of handling complex, multi-step workflows. Built on **LangGraph** and inspired by Claude Code, Deep Research, and Manus.

### Core Components

| Component | Purpose |
|-----------|---------|
| **Planning Tools** | Built-in `write_todos` for task decomposition |
| **File System Management** | `ls`, `read_file`, `write_file`, `edit_file` for context offloading |
| **Subagent Spawning** | `task` tool for specialized context isolation |
| **Persistent Memory** | Integration with LangGraph's Store for cross-thread memory |

### When to Use DeepAgents

| Use DeepAgents When | Use Simpler Alternatives When |
|---------------------|-------------------------------|
| Multi-step task decomposition needed | Simple single-step tasks |
| Large context management required | Small, bounded context |
| Work delegation to specialists | No delegation needed |
| Cross-conversation memory required | Stateless operations |

### Ecosystem Integration

```
┌─────────────────────────────────────────┐
│            DeepAgents                   │
├─────────────────────────────────────────┤
│  LangGraph - Graph execution & state    │
│  LangChain - Tool integrations          │
│  LangSmith - Observability & deployment │
└─────────────────────────────────────────┘
```

---

## 2. Quick Start

### Installation

```bash
# Using pip
pip install deepagents tavily-python

# Using uv
uv add deepagents tavily-python

# Using poetry
poetry add deepagents tavily-python
```

### Environment Setup

```bash
export ANTHROPIC_API_KEY="your-api-key"
export TAVILY_API_KEY="your-tavily-api-key"  # Optional: for web search
```

### Basic Agent Creation

```python
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

# Initialize search client (optional)
tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search using Tavily."""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

# Create the agent
agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",  # Default model
    tools=[internet_search],
    system_prompt="You are an expert researcher."
)

# Invoke the agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "What is LangGraph?"}]
})

print(result["messages"][-1].content)
```

---

## 3. Customization

### Six Customization Dimensions

| Dimension | Description |
|-----------|-------------|
| **Model Selection** | Choose different LLM providers and models |
| **System Prompt** | Customize agent behavior with specific instructions |
| **Tools** | Extend capabilities with custom functions |
| **Backend** | Configure storage and filesystem handling |
| **Skills** | Add task-specific expertise loaded progressively |
| **Memory** | Persistent context via AGENTS.md files |

### Model Customization

```python
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

# Using provider:model format
model = init_chat_model(model="openai:gpt-5")
agent = create_deep_agent(model=model)

# Using LangChain model object for granular control
from langchain_ollama import ChatOllama

model = init_chat_model(
    model=ChatOllama(
        model="llama3.1",
        temperature=0,
    )
)
agent = create_deep_agent(model=model)
```

### System Prompt Customization

```python
research_instructions = """\
You are an expert researcher. Your job is to conduct
thorough research, and then write a polished report.
"""

agent = create_deep_agent(
    system_prompt=research_instructions,
)
```

### Custom Tools Integration

```python
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

agent = create_deep_agent(
    tools=[internet_search]
)
```

### Configuration Parameters Reference

| Parameter | Purpose | Default |
|-----------|---------|---------|
| `model` | LLM to use | `claude-sonnet-4-5-20250929` |
| `system_prompt` | Custom agent instructions | Framework default |
| `tools` | Custom function integrations | `[]` |
| `backend` | Storage/filesystem handler | `StateBackend` |
| `skills` | Task-specific expertise files | `[]` |
| `memory` | AGENTS.md context files | `[]` |
| `checkpointer` | State persistence | Required for HITL |
| `interrupt_on` | Operations requiring approval | `{}` |
| `store` | Centralized storage | Optional |
| `subagents` | Specialized sub-workers | `[]` |

---

## 4. Storage Backends

### Available Backends

| Backend | Storage Type | Persistence | Best Use Case |
|---------|-------------|-------------|---------------|
| **StateBackend** | LangGraph agent state | Per-thread (ephemeral) | Scratch pad, intermediate results |
| **FilesystemBackend** | Local disk | Permanent | Local dev CLIs, CI/CD pipelines |
| **StoreBackend** | LangGraph Store | Cross-thread durable | Production deployments |
| **CompositeBackend** | Router | Mixed | Combining ephemeral + persistent |

### StateBackend (Default - Ephemeral)

```python
from deepagents import create_deep_agent

# Default behavior
agent = create_deep_agent()

# Explicit
agent = create_deep_agent(backend=lambda rt: StateBackend(rt))
```

### FilesystemBackend (Local Disk)

```python
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    backend=FilesystemBackend(root_dir=".", virtual_mode=True)
)
```

**Security Warning:** Always set `virtual_mode=True` to prevent path traversal attacks.

### StoreBackend (Persistent)

```python
from langgraph.store.memory import InMemoryStore
from deepagents.backends import StoreBackend

agent = create_deep_agent(
    backend=lambda rt: StoreBackend(rt),
    store=InMemoryStore()
)
```

### CompositeBackend (Router)

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

composite_backend = lambda rt: CompositeBackend(
    default=StateBackend(rt),           # Default: ephemeral
    routes={
        "/memories/": StoreBackend(rt), # Persistent
    }
)

agent = create_deep_agent(
    backend=composite_backend,
    store=InMemoryStore()
)
```

**Routing Behavior:**
| Path | Backend |
|------|---------|
| `/workspace/plan.md` | StateBackend (ephemeral) |
| `/memories/agent.md` | StoreBackend (persistent) |

---

## 5. Subagents

### What Are Subagents?

Subagents are delegated agents that handle specialized tasks within a larger agent system. They solve the **context bloat problem** by isolating detailed work.

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Context Isolation** | Main agent stays focused without intermediate clutter |
| **Specialization** | Custom instructions and tool sets per domain |
| **Model Flexibility** | Each subagent can use different models |
| **Security** | Minimal tool exposure reduces risk |

### Creating Subagents

```python
from deepagents import create_deep_agent

research_subagent = {
    "name": "research-agent",
    "description": "Conducts in-depth research using web search",
    "system_prompt": """You are a thorough researcher. Your job is to:
    1. Break down the research question into searchable queries
    2. Use internet_search to find relevant information
    3. Synthesize findings into a comprehensive summary
    4. Cite sources when making claims

    Keep response under 500 words.""",
    "tools": [internet_search],
    "model": "openai:gpt-4o",  # Optional: different model
}

agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    subagents=[research_subagent]
)
```

### Multi-Agent Patterns

```python
subagents = [
    {
        "name": "data-collector",
        "description": "Gathers raw data from various sources",
        "system_prompt": "Collect comprehensive data on the topic",
        "tools": [web_search, api_call, database_query],
    },
    {
        "name": "data-analyzer",
        "description": "Analyzes collected data for insights",
        "system_prompt": "Analyze data and extract key insights",
        "tools": [statistical_analysis],
    },
    {
        "name": "report-writer",
        "description": "Writes polished reports from analysis",
        "system_prompt": "Create professional reports from insights",
        "tools": [format_document],
    },
]

agent = create_deep_agent(
    system_prompt="Coordinate data analysis and reporting. Use subagents for specialized tasks.",
    subagents=subagents
)
```

### Best Practices

1. **Write clear descriptions** - Help main agent decide when to delegate
2. **Keep system prompts detailed** - Include output format and length limits
3. **Minimize tool sets** - Only provide tools subagents actually need
4. **Instruct main agent to delegate** - Add explicit delegation guidance

---

## 6. Human-in-the-Loop

### Purpose

Enable sensitive tool operations to require human approval before execution.

### Workflow

```
Agent proposes tool → Interrupt check → Human reviews → Decision applied
                                           ↓
                               Approve / Edit / Reject
```

### Configuration

```python
from langchain.tools import tool
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

@tool
def delete_file(path: str) -> str:
    """Delete a file from the filesystem."""
    return f"Deleted {path}"

checkpointer = MemorySaver()  # REQUIRED for HITL

agent = create_deep_agent(
    tools=[delete_file],
    interrupt_on={"delete_file": True},
    checkpointer=checkpointer
)
```

### Handling Interrupts

```python
import uuid
from langgraph.types import Command

config = {"configurable": {"thread_id": str(uuid.uuid4())}}

result = agent.invoke({
    "messages": [{"role": "user", "content": "Delete temp.txt"}]
}, config=config)

if result.get("__interrupt__"):
    interrupts = result["__interrupt__"][0].value

    # Human reviews and decides
    decisions = [{"type": "approve"}]  # or "reject" or "edit"

    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=config  # MUST use same config
    )
```

### Decision Types

| Decision | Behavior |
|----------|----------|
| `"approve"` | Execute tool with original arguments |
| `"edit"` | Modify arguments before execution |
| `"reject"` | Skip tool execution entirely |

### Editing Arguments

```python
decisions = [{
    "type": "edit",
    "edited_action": {
        "name": "send_email",
        "args": {
            "to": "team@company.com",
            "subject": "Updated Subject",
            "body": "Modified content"
        }
    }
}]
```

---

## 7. Long-Term Memory

### Architecture

DeepAgents supports persistent memory across conversation threads through a `CompositeBackend` that routes file operations.

| Storage Type | Backend | Persistence |
|--------------|---------|-------------|
| **Short-term** | StateBackend | Single thread only |
| **Long-term** | StoreBackend | Cross-thread, survives restarts |

### Configuration

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

def make_backend(runtime):
    return CompositeBackend(
        default=StateBackend(runtime),       # Ephemeral files
        routes={
            "/memories/": StoreBackend(runtime)  # Persistent files
        }
    )

agent = create_deep_agent(
    store=InMemoryStore(),
    backend=make_backend,
    checkpointer=checkpointer
)
```

### Cross-Thread Memory Access

```python
import uuid

# Thread 1: Write persistent data
config1 = {"configurable": {"thread_id": str(uuid.uuid4())}}
agent.invoke({
    "messages": [{"role": "user", "content": "Save preferences to /memories/prefs.txt"}]
}, config=config1)

# Thread 2: Access same data (different thread!)
config2 = {"configurable": {"thread_id": str(uuid.uuid4())}}
agent.invoke({
    "messages": [{"role": "user", "content": "What are my preferences?"}]
}, config=config2)
```

### Production Setup (PostgreSQL)

```python
from langgraph.store.postgres import PostgresStore
import os

store_ctx = PostgresStore.from_conn_string(os.environ["DATABASE_URL"])
store = store_ctx.__enter__()
store.setup()

agent = create_deep_agent(
    store=store,
    backend=lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={"/memories/": StoreBackend(rt)}
    )
)
```

---

## 8. Skills System

### What Are Skills?

Skills are reusable, specialized capabilities that extend agent functionality through progressive disclosure - agents learn about capabilities as needed.

### SKILL.md Format

```markdown
---
name: skill-name
description: Brief explanation of when to use this skill
---

# Skill Name

## Description
Clear explanation of what this skill does.

## Usage
Example commands showing how to use this skill.

## Implementation Details
Technical information about how the skill works.

## Examples
Concrete examples demonstrating the skill in action.
```

### Directory Structure

```
~/.deepagents/agent/skills/          # Global skills
  ├── web-research/
  │   └── SKILL.md
  └── arxiv-search/
      └── SKILL.md

.deepagents/skills/                   # Project-specific skills
  └── custom-skill/
      └── SKILL.md
```

### Registering Skills

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    skills=["./skills/"],           # Path to skills directory
    checkpointer=MemorySaver()
)
```

### Using StoreBackend for Skills

```python
from deepagents.backends import StoreBackend
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
store.put(
    namespace=("filesystem",),
    key="/skills/web-research/SKILL.md",
    value=skill_content
)

agent = create_deep_agent(
    backend=(lambda rt: StoreBackend(rt)),
    store=store,
    skills=["./skills/"]
)
```

---

## 9. Middleware

### Available Middleware

| Middleware | Purpose |
|------------|---------|
| **TodoListMiddleware** | Task planning and tracking |
| **FilesystemMiddleware** | File operations with backend routing |
| **SubAgentMiddleware** | Subagent spawning and coordination |
| **SummarizationMiddleware** | Context compression |
| **CachingMiddleware** | Response caching |

### Using Middleware

```python
from langchain.agents import create_agent
from deepagents.middleware.filesystem import FilesystemMiddleware

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    middleware=[
        FilesystemMiddleware(
            backend=lambda rt: CompositeBackend(
                default=StateBackend(rt),
                routes={"/memories/": StoreBackend(rt)}
            ),
            system_prompt="Custom filesystem instructions"
        )
    ]
)
```

---

## 10. CLI Reference

### Installation

```bash
# Global install
uv tool install deepagents-cli

# Run without install
uvx deepagents-cli

# pip
pip install deepagents-cli
```

### Commands

| Command | Description |
|---------|-------------|
| `deepagents` | Start interactive session |
| `deepagents list` | View configured agents |
| `deepagents skills create NAME` | Create new skill |
| `deepagents skills list` | List skills |
| `deepagents threads list` | Show sessions |
| `deepagents reset --agent NAME` | Clear agent memory |

### Command-Line Options

```bash
deepagents --agent NAME              # Use named agent
deepagents --auto-approve            # Skip approval prompts
deepagents --resume / -r             # Resume recent session
deepagents --model MODEL_NAME        # Specify model
deepagents --sandbox TYPE            # Use remote sandbox
```

### Built-In Tools

| Tool | Purpose | Requires Approval |
|------|---------|-------------------|
| `ls`, `read_file` | File operations | No |
| `write_file`, `edit_file` | File modification | Yes |
| `glob`, `grep` | File searching | No |
| `shell`, `execute` | Command execution | Yes |
| `web_search`, `fetch_url` | Web access | Yes |
| `task` | Subagent delegation | Yes |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+E` | Open external editor |
| `Shift+Tab` | Toggle auto-approve |
| `@filename` | Auto-complete and inject file |
| `/remember` | Update memory/skills |
| `/tokens` | Show token usage |

---

## 11. Application to Our Project

### How This Applies to epiphan-sales-agent

Based on our implementation plan, here's how DeepAgents patterns map to our architecture:

#### Orchestrator Agent Implementation

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

# Our specialized subagents
subagents = [
    {
        "name": "qualification-agent",
        "description": "Scores leads against 5-dimension ICP criteria",
        "tools": [qualify_lead, get_icp_weights],
    },
    {
        "name": "research-agent",
        "description": "Enriches leads via Apollo, Clearbit, web scraping",
        "tools": [apollo_enrich, clearbit_lookup, scrape_website],
    },
    {
        "name": "script-selection-agent",
        "description": "Selects ACQP warm call scripts based on persona",
        "tools": [get_persona_scripts, select_script],
    },
    {
        "name": "email-agent",
        "description": "Generates personalized outreach emails",
        "tools": [generate_email, personalize_content],
    },
]

orchestrator = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    system_prompt="""You are the BDR pipeline orchestrator.
    Coordinate lead qualification, research, script selection, and email generation.
    For each lead:
    1. First qualify using qualification-agent
    2. If Tier 1/2, enrich using research-agent
    3. Select appropriate script using script-selection-agent
    4. Generate email using email-agent
    """,
    subagents=subagents,
    checkpointer=MemorySaver(),
)
```

#### Long-Term Memory for Reference Customers

```python
# Store reference customers in persistent memory
agent = create_deep_agent(
    store=PostgresStore.from_conn_string(DATABASE_URL),
    backend=lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/memories/reference_customers/": StoreBackend(rt),
            "/memories/persona_data/": StoreBackend(rt),
        }
    )
)
```

#### Human-in-the-Loop for Email Sending

```python
agent = create_deep_agent(
    tools=[send_email, schedule_call],
    interrupt_on={
        "send_email": True,      # Require approval before sending
        "schedule_call": True,   # Require approval before scheduling
    },
    checkpointer=MemorySaver()
)
```

### Recommended Next Steps

1. **Phase 1**: Implement lead ingestion endpoint with schema mapping
2. **Phase 2**: Create orchestrator agent using subagent pattern
3. **Phase 3**: Add checkpointing for state persistence
4. **Phase 4**: Integrate persona aliases and objection prediction

---

## Sources

- [LangGraph 1.0 Release](https://www.blog.langchain.com/langchain-langgraph-1dot0/)
- [DeepAgents Overview](https://docs.langchain.com/oss/python/deepagents/overview)
- [DeepAgents Customization](https://docs.langchain.com/oss/python/deepagents/customization)
- [DeepAgents Backends](https://docs.langchain.com/oss/python/deepagents/backends)
- [DeepAgents Subagents](https://docs.langchain.com/oss/python/deepagents/subagents)
- [DeepAgents Human-in-the-Loop](https://docs.langchain.com/oss/python/deepagents/human-in-the-loop)
- [DeepAgents Long-Term Memory](https://docs.langchain.com/oss/python/deepagents/long-term-memory)
- [DeepAgents Skills](https://docs.langchain.com/oss/python/deepagents/skills)
- [DeepAgents CLI](https://docs.langchain.com/oss/python/deepagents/cli)
- [GitHub Repository](https://github.com/langchain-ai/deepagents)
