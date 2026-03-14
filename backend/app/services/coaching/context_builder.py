"""Context builder — layered system prompt assembly for coaching.

Ported from souffleur-core/src/context_builder.rs.
Assembles multi-layer prompts: static base → stage tactics → MEDDIC/partner → DISC → cross-call.
"""

from __future__ import annotations

from app.data.coaching_schemas import (
    MEDDIC_CRITERION_NAMES,
    PARTNER_CRITERION_NAMES,
    AccumulatedState,
    AudienceType,
    BuyerDisc,
    CallStage,
    CrossCallContext,
    DiscConfidence,
    DiscType,
    MeddicTracker,
    PartnerProgress,
)
from app.services.coaching.tactics import (
    SALES_COACHING_SYSTEM_PROMPT,
    get_disc_tactics,
    get_stage_tactics,
)


def build_coach_system_prompt(
    stage: CallStage,
    audience: AudienceType,
    acc: AccumulatedState,
    topics: list[str],
    objections: list[str],
    cross_call: CrossCallContext | None = None,
) -> str:
    """Build the full system prompt for a coaching flush."""
    sections: list[str] = []

    # Layer 3: Static coaching base
    sections.append(SALES_COACHING_SYSTEM_PROMPT)

    # Layer 3: Stage-specific tactics
    sections.append(get_stage_tactics(stage))

    # Layer 2: State tracking — audience-dependent
    if audience == AudienceType.DIRECT_SALE:
        sections.append(format_meddic_section(acc.meddic))
    else:
        sections.append(format_partner_progress_section(acc.partner))

    # Layer 2: Buyer DISC profile (applies to both audience types)
    if acc.disc.disc_type != DiscType.UNKNOWN and acc.disc.confidence != DiscConfidence.LOW:
        sections.append(format_disc_section(acc.disc))

    # Layer 2: Cross-call context
    if cross_call is not None:
        sections.append(format_cross_call_section(cross_call))

    # Layer 1: Session context (topics, objections)
    if topics or objections:
        sections.append(format_session_context(topics, objections))

    return "\n\n".join(sections)


def format_meddic_section(meddic: MeddicTracker) -> str:
    """Format MEDDIC tracker as checkmark/cross display."""
    score = meddic.score()
    criteria = meddic.criteria()

    items: list[str] = []
    for c, name in zip(criteria, MEDDIC_CRITERION_NAMES, strict=True):
        if c.confirmed:
            if c.evidence:
                items.append(f"\u2713 {name} — {c.evidence}")
            else:
                items.append(f"\u2713 {name}")
        else:
            items.append(f"\u2717 {name}")

    lines = [f"## MEDDIC STATUS ({score}/6)"]
    for item in items:
        lines.append(f"- {item}")

    if score < 6:
        # Derive gaps from criteria already in scope — avoids second iteration
        priority = [
            name for c, name in zip(criteria, MEDDIC_CRITERION_NAMES, strict=True)
            if not c.confirmed
        ][:2]
        lines.append(f"Priority: Identify {' and '.join(priority)} next.")

    return "\n".join(lines)


def format_partner_progress_section(partner: PartnerProgress) -> str:
    """Format partner progress as checkmark/cross display."""
    values = partner.field_values()
    score = sum(values)

    lines = [f"## PARTNER PROGRESS ({score}/6)"]
    for val, name in zip(values, PARTNER_CRITERION_NAMES, strict=True):
        icon = "\u2713" if val else "\u2717"
        lines.append(f"- {icon} {name}")

    if score < 6:
        priority = [n for v, n in zip(values, PARTNER_CRITERION_NAMES, strict=True) if not v][:2]
        lines.append(f"Priority: {' and '.join(priority)} next.")

    if partner.displacement_opportunities:
        opps = ", ".join(f'"{o}"' for o in partner.displacement_opportunities)
        lines.append(f"Displacement opportunities: {opps}")
    if partner.active_projects > 0:
        lines.append(f"Active projects mentioned: {partner.active_projects}")

    return "\n".join(lines)


def format_disc_section(disc: BuyerDisc) -> str:
    """Format DISC buyer profile."""
    tactic = get_disc_tactics(disc.disc_type)
    disc_name = disc.disc_type.value.capitalize()
    return (
        f"## BUYER PROFILE\n"
        f"Type: {disc_name} ({disc.confidence.value} confidence)\n"
        f"Adapt: {tactic}"
    )


def format_session_context(topics: list[str], objections: list[str]) -> str:
    """Format session topics and objections."""
    lines = ["## SESSION STATE"]
    if topics:
        lines.append(f"Topics discussed: {', '.join(topics)}")
    if objections:
        lines.append(f"Objections raised: {', '.join(objections)}")
    return "\n".join(lines)


def format_cross_call_section(ctx: CrossCallContext) -> str:
    """Format cross-call context from prior conversations."""
    lines = ["## CROSS-CALL CONTEXT"]
    lines.append(f"Previous calls: {ctx.total_previous_calls} calls")
    if ctx.last_stage_reached:
        lines.append(f"Last stage reached: {ctx.last_stage_reached}")
    if ctx.confirmed_pains:
        pains = ", ".join(f'"{p}"' for p in ctx.confirmed_pains)
        lines.append(f"Confirmed pain: {pains}")
    if ctx.open_commitments:
        commits = ", ".join(f'"{c}"' for c in ctx.open_commitments)
        lines.append(f"Open commitments: {commits}")
    if ctx.unresolved_objections:
        objs = ", ".join(f'"{o}"' for o in ctx.unresolved_objections)
        lines.append(f"Unresolved objections: {objs}")
    if ctx.recurring_topics:
        lines.append(f"Recurring topics: {', '.join(ctx.recurring_topics)}")
    return "\n".join(lines)
