# Worktree Task: Warm Lead Persona-Specific Talk Tracks

## Mission
Create persona-specific warm lead talk tracks that combine trigger context (what action they took) with persona pain points (who they are). Update BOTH projects to stay in sync.

## Context
- Tim is new BDR at Epiphan Video with **100,000+ warm inbound leads** (NOT cold)
- Current warm scripts in `scripts.py` are organized by **trigger type** (content download, webinar, demo request)
- Missing: **persona-specific** customization for warm calls
- An AV Director downloading a case study should get different messaging than an L&D Director

## Primary Focus Personas
1. **AV Director** (Higher Education) - manages 50-500+ rooms, understaffed, remote troubleshooting pain
2. **L&D Director** (Corporate) - can't scale content, SME knowledge loss, production bottleneck

## Secondary Personas
3. Technical Director (House of Worship/Live Events)
4. Simulation Center Director (Healthcare)
5. Court Administrator (Government)

## Deliverables

### 1. Update Python Scripts (`/Users/tmk/Desktop/tk_projects/epiphan-sales-agent/backend/app/data/`)

**File to modify:** `scripts.py`
- Add new data structure: `PERSONA_WARM_SCRIPTS`
- Combine trigger types with persona-specific messaging
- Include persona-specific discovery questions
- Include "what to listen for" cues
- Include persona-specific objection handling

**Schema pattern:**
```python
PersonaWarmScript(
    persona_id="av_director",
    persona_name="AV Director",
    trigger_type=TriggerType.CONTENT_DOWNLOAD,
    acknowledge="...",  # Persona-aware acknowledgment
    connect="...",      # Pain-point specific connection
    qualify="...",      # Persona-specific qualification
    propose="...",      # Tailored next step
    discovery_questions=[...],  # Persona-specific
    listen_for=[...],   # Buying signals specific to this persona
    objection_pivots=[...],  # Persona-specific objections
)
```

### 2. Update BDR Playbook Markdown (`/Users/tmk/Desktop/tk_projects/epiphan-bdr-playbook/playbook/sales-scripts/`)

**Create new file:** `warm-inbound-by-persona.md`
- Mirror the Python structure in readable markdown
- Include call flow diagrams
- Quick reference format for live calls

### 3. Update Schemas if Needed (`/Users/tmk/Desktop/tk_projects/epiphan-sales-agent/backend/app/data/schemas.py`)
- Add `PersonaWarmScript` dataclass
- Add any new enums needed

## Existing Resources to Reference

**Personas (full details):**
- `/Users/tmk/Desktop/tk_projects/epiphan-sales-agent/backend/app/data/personas.py`

**Current warm scripts (by trigger):**
- `/Users/tmk/Desktop/tk_projects/epiphan-sales-agent/backend/app/data/scripts.py` (lines 261-476)

**Current cold scripts (by vertical):**
- Same file, lines 12-258

**Persona cards (markdown):**
- `/Users/tmk/Desktop/tk_projects/epiphan-bdr-playbook/playbook/persona-cards/av-director.md`
- `/Users/tmk/Desktop/tk_projects/epiphan-bdr-playbook/playbook/persona-cards/ld-director.md`

## Key Insight

**Current state:** Trigger-based warm scripts
```
Content Download → Same script for everyone
Webinar Attended → Same script for everyone
Demo Request → Same script for everyone
```

**Target state:** Persona + Trigger matrix
```
AV Director + Content Download → "I saw you downloaded the NC State case study. Managing 300+ rooms with a small team resonated with you?"
L&D Director + Content Download → "I saw you downloaded our training ROI guide. Is scaling content creation the bottleneck?"
```

## Quality Checklist
- [x] All 5 personas have warm scripts for top 4 triggers (content, webinar, demo, pricing)
- [x] Each script references persona-specific pain points
- [x] Discovery questions match persona card questions
- [x] Objection pivots match persona card objections
- [x] Python code passes lint/type checks
- [ ] Markdown is formatted for quick reference
- [ ] Both projects updated and committed

## Code Quality Follow-ups (Completed 2026-01-25)

### 1. Typed Return for `get_warm_script_for_call()`
- Added `WarmCallScript` Pydantic model to `schemas.py`
- Changed return type from `dict | None` to `WarmCallScript | None`
- Updated tests to use attribute access instead of dict subscripting

### 2. Added `__all__` Exports
All 9 data modules now have explicit `__all__` exports:
- `schemas.py` (31 symbols)
- `scripts.py` (8 symbols)
- `persona_warm_scripts.py` (8 symbols)
- `personas.py`, `competitors.py`, `discovery.py`, `stories.py`, `templates.py`, `market_intel.py`

### 3. Fixed Pydantic V2 Deprecation Warnings
- Replaced all 8 `class Config:` blocks with `model_config = ConfigDict(...)`
- Removed `Optional[X]` in favor of `X | None` (ruff auto-fix)

## Git Workflow
1. Work on this branch: `feature/warm-persona-scripts`
2. Commit frequently with clear messages
3. When complete, create PR or notify main session

## Ports Allocated
- 8100 (API if needed)
- 8101 (Frontend if needed)
