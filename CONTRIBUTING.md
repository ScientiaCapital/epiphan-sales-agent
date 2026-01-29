# Contributing to Epiphan Sales Agent

Guidelines for contributing code, documentation, and features.

---

## Code Style

### Linting with Ruff

We use [ruff](https://docs.astral.sh/ruff/) for Python linting:

```bash
# Check for issues
cd backend && uv run ruff check .

# Auto-fix issues
cd backend && uv run ruff check . --fix

# Format code
cd backend && uv run ruff format .
```

### Type Checking with mypy

```bash
cd backend && uv run mypy app/
```

Note: Some type stubs are missing (fastapi, hubspot). These are known issues.

### Code Conventions

- **Imports**: Use absolute imports from `app.`
- **Type hints**: Required for all function signatures
- **Docstrings**: Google style, required for public functions
- **Line length**: 88 characters (ruff default)
- **Quotes**: Double quotes for strings

Example:

```python
from app.data.schemas import PersonaProfile


def get_persona_by_id(persona_id: str) -> PersonaProfile | None:
    """Lookup persona by ID.

    Args:
        persona_id: The persona identifier (e.g., "av_director")

    Returns:
        PersonaProfile if found, None otherwise
    """
    for persona in PERSONAS:
        if persona.id == persona_id:
            return persona
    return None
```

---

## Testing

### Running Tests

```bash
# All tests
cd backend && uv run pytest tests/ -v

# Specific module
uv run pytest tests/unit/test_qualification_tools.py -v

# With coverage
uv run pytest tests/ --cov=app --cov-report=term-missing
```

### Test Requirements

- **Unit tests required** for all new tools and functions
- **Target coverage**: 80%+ for new code
- **Test file naming**: `test_<module_name>.py`
- **Test function naming**: `test_<function_name>_<scenario>`

Example:

```python
def test_classify_company_size_enterprise():
    """Enterprise companies (1000+) should score 10 points."""
    category, score, reason = classify_company_size(5000)
    assert category == "Enterprise"
    assert score == 10


def test_classify_company_size_unknown():
    """Unknown employee count should score 0 points."""
    category, score, reason = classify_company_size(None)
    assert category == "Unknown"
    assert score == 0
```

---

## Git Workflow

### Branch Naming

```
feature/<short-description>   # New features
fix/<short-description>       # Bug fixes
docs/<short-description>      # Documentation
refactor/<short-description>  # Code refactoring
```

### Commit Messages

Use conventional commits format:

```
feat: Add Qualification Agent with 5-dimension ICP scoring
fix: Correct persona matching for L&D Director
docs: Update quickstart with API examples
refactor: Extract scoring weights to constants
test: Add 76 tests for qualification tools
```

### Pull Request Process

1. **Create branch** from `main`
2. **Make changes** with tests
3. **Run checks** locally:
   ```bash
   cd backend
   uv run ruff check .
   uv run pytest tests/ -v
   ```
4. **Push branch** and open PR
5. **Describe changes** in PR description
6. **Request review** from team

### PR Description Template

```markdown
## Summary
Brief description of what this PR does.

## Changes
- Change 1
- Change 2

## Testing
- [ ] Unit tests added
- [ ] All tests passing
- [ ] Linting passes

## Related Issues
Closes #123
```

---

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app
│   ├── api/
│   │   └── routes/          # API endpoints
│   ├── data/
│   │   ├── schemas.py       # Pydantic models
│   │   ├── personas.py      # 8 buyer personas
│   │   ├── persona_warm_scripts.py  # ACQP scripts
│   │   └── competitors.py   # Battlecards
│   └── services/
│       ├── langgraph/       # AI agents
│       │   ├── agents/      # Agent implementations
│       │   ├── tools/       # Agent tools
│       │   └── states.py    # State schemas
│       ├── enrichment/      # Apollo, Clearbit
│       └── integrations/    # HubSpot
└── tests/
    ├── unit/                # Unit tests
    └── integration/         # Integration tests
```

### Adding a New Agent

1. Create state schema in `services/langgraph/states.py`
2. Create tools in `services/langgraph/tools/<agent>_tools.py`
3. Create agent in `services/langgraph/agents/<agent>_agent.py`
4. Add API route in `api/routes/agents.py`
5. Add tests in `tests/unit/`

---

## Documentation

### Updating Docs

Documentation lives in `docs/`:

```
docs/
├── README.md                 # Navigation hub
├── getting-started/
├── architecture/
├── agents/
├── sales-playbook/
├── integration/
└── reference/
```

When making code changes that affect:
- **API endpoints**: Update `docs/getting-started/quickstart.md`
- **Agents**: Update `docs/agents/overview.md` or specific agent doc
- **Personas/Scripts**: Update `docs/sales-playbook/`
- **Architecture**: Update `docs/architecture/`

### Documentation Style

- Use Markdown tables for structured data
- Include code examples where helpful
- Keep explanations concise and practical
- Link to related docs

---

## Questions?

Open an issue or reach out to the team.
