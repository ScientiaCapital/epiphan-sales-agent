"""Tools for Script Selection Agent.

Provides functions to look up warm scripts (by persona+trigger),
cold scripts (by vertical), and persona profiles.
"""

from typing import Any

from langchain_core.tools import ToolException

from app.data.persona_warm_scripts import get_warm_script_for_persona_trigger
from app.data.personas import get_persona_by_id
from app.data.schemas import PersonaType, TriggerType, Vertical
from app.data.scripts import get_script_by_vertical


def get_warm_script(
    persona_id: str,
    trigger: str,
) -> dict[str, Any]:
    """
    Get warm call script for persona and trigger.

    Args:
        persona_id: Persona ID (av_director, ld_director, etc.)
        trigger: Trigger type (demo_request, content_download, etc.)

    Returns:
        Script dict

    Raises:
        ToolException: If persona/trigger combination not found
    """
    # Convert string IDs to enums
    try:
        persona_type = PersonaType(persona_id)
        trigger_type = TriggerType(trigger)
    except ValueError as e:
        raise ToolException(
            f"Invalid persona '{persona_id}' or trigger '{trigger}': {e}",
        ) from e

    script = get_warm_script_for_persona_trigger(persona_type, trigger_type)
    if not script:
        raise ToolException(
            f"No warm script found for persona '{persona_id}' with trigger '{trigger}'",
        )

    return {
        "persona_id": persona_id,
        "trigger": trigger,
        "acknowledge": script.acknowledge,
        "connect": script.connect,
        "qualify": script.qualify,
        "propose": script.propose,
        "discovery_questions": script.discovery_questions,
        "what_to_listen_for": script.what_to_listen_for,
        "objection_handlers": [],  # Handled at persona level
    }


def get_cold_script(vertical: str) -> dict[str, Any]:
    """
    Get cold call script for vertical.

    Args:
        vertical: Vertical ID (higher_ed, corporate, etc.)

    Returns:
        Script dict

    Raises:
        ToolException: If vertical not found
    """
    # Convert string to enum
    try:
        vertical_enum = Vertical(vertical)
    except ValueError as e:
        raise ToolException(
            f"Invalid vertical '{vertical}': {e}",
        ) from e

    script = get_script_by_vertical(vertical_enum)
    if not script:
        raise ToolException(
            f"No cold script found for vertical '{vertical}'",
        )

    return {
        "vertical": script.vertical,  # Already a string due to use_enum_values
        "target_persona": script.target_persona,
        "pattern_interrupt": script.pattern_interrupt,
        "value_hook": script.value_hook,
        "pain_question": script.pain_question,
        "permission": script.permission,
        "pivot": script.pivot,
        "why_it_works": script.why_it_works,
        "objection_pivots": (
            [{"objection": o.objection, "response": o.response} for o in script.objection_pivots]
            if script.objection_pivots
            else []
        ),
    }


def get_persona_profile(persona_id: str) -> dict[str, Any]:
    """
    Get full persona profile.

    Args:
        persona_id: Persona ID

    Returns:
        Persona profile dict

    Raises:
        ToolException: If persona not found
    """
    persona = get_persona_by_id(persona_id)
    if not persona:
        raise ToolException(
            f"Persona not found: {persona_id}",
        )

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
            {"objection": o.objection, "response": o.response} for o in persona.objections
        ],
        "buying_signals": {
            "high": persona.buying_signals.high,
            "medium": persona.buying_signals.medium,
        },
    }
