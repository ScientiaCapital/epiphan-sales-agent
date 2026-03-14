"""Stage-specific and DISC-specific coaching tactics.

Ported from souffleur-core/src/tactics.rs.
"""

from app.data.coaching_schemas import CallStage, DiscType

STAGE_TACTICS: dict[CallStage, str] = {
    CallStage.OPENING: (
        "Build rapport quickly. Match energy. State purpose clearly. "
        "Ask an open-ended question to transition to discovery. Keep it under 60 seconds. "
        "Do NOT mention demos, bookings, or next steps yet. "
        "GATEKEEPER CHECK: If the person says they're not the right contact, "
        "switch immediately to getting the decision-maker's name/email — "
        "do NOT try to pitch or discover through a gatekeeper."
    ),
    CallStage.DISCOVERY: (
        "SPIN Selling: Situation + Problem questions. Do NOT pitch yet. "
        "Listen 70%, talk 30%. Dig for pain points. "
        'Ask "Tell me more about..." and "What happens when..." style questions. '
        "Do NOT mention demos or next steps yet — stay in discovery mode."
    ),
    CallStage.QUALIFICATION: (
        "MEDDIC framework: check Metrics, Economic Buyer, Decision Criteria, "
        "Decision Process, Identify Pain, Champion. "
        '"Who owns the budget for this?" and "What does your approval process look like?" '
        "Track all 6 letters. Use SPIN Implication questions to deepen gaps."
    ),
    CallStage.DEMO: (
        "Tie every feature to a specific pain point they mentioned. "
        "Don't feature-dump. Use \"You mentioned [pain] — here's how we solve that...\" pattern. "
        'Pause for reactions. Ask "Does this address your concern about...?"'
    ),
    CallStage.NEGOTIATION: (
        "Never offer a discount without getting something in return "
        "(longer contract, larger order, case study). "
        'Frame everything as ROI, not cost. Use "investment" language. '
        "Anchor high. If they push on price, expand scope discussion. "
        "PRICE WALL: If budget is truly fixed and below range, suggest phased deployment, "
        "different product tier, or lease options — don't keep pushing full price."
    ),
    CallStage.OBJECTION_HANDLING: (
        "Price objection → reframe as TCO/ROI. Competitor objection → highlight differentiators, "
        "don't trash-talk. Timing objection → quantify opportunity cost of waiting. "
        '"I understand your concern. Let me address that..." '
        "Always acknowledge before countering."
    ),
    CallStage.CLOSING: (
        "Summarize all agreements and value points. Clear next steps with dates. "
        '"What do you need to make a decision?" or '
        '"Is there anything preventing us from moving forward?" '
        'Trial close: "If we can address X, would you be ready to proceed?"'
    ),
    CallStage.SUPPORT: (
        "Listen empathetically. Don't upsell during support — build trust first. "
        'Solve the problem. After resolution, ask "Is there anything else I can help with?" '
        "Document the issue for follow-up."
    ),
    CallStage.RENEWAL: (
        "Highlight ROI achieved since last purchase. Reference their usage data. "
        "Present expansion opportunities. Ask about changing needs. "
        '"Based on your growth, here\'s what I\'d recommend..." '
        "Offer multi-year incentives."
    ),
}

DISC_TACTICS: dict[DiscType, str] = {
    DiscType.DOMINANT: (
        "Lead with data and ROI. Be direct, skip rapport. "
        "Focus on outcomes and bottom line."
    ),
    DiscType.INFLUENTIAL: (
        "Use stories, make it collaborative. Engage their vision. "
        "Keep energy high."
    ),
    DiscType.STEADY: (
        "Slow down, reassure on support. Don't rush decisions. "
        "Emphasize partnership and stability."
    ),
    DiscType.CONSCIENTIOUS: (
        "Lead with data and specs. Quantify the gap. "
        "Respect their evaluation timeline. Send documentation after call."
    ),
}

SALES_COACHING_SYSTEM_PROMPT = (
    "You are an expert real-time sales coach for Epiphan Video, "
    "a B2B hardware/software company selling video production and streaming solutions.\n\n"
    "Your role: analyze the live conversation between [Mic] (salesperson) and [Audio] (customer), "
    "then give background coaching to [Mic]. Never speak to [Audio]. Never roleplay as [Mic].\n\n"
    "Your coaching response must be 10 words or fewer, readable in under 5 seconds.\n\n"
    "Refer to your loaded context (RULES, products, competitors, objections) for detailed methodology."
)


def get_stage_tactics(stage: CallStage) -> str:
    """Get formatted stage tactics for prompt injection."""
    tactics = STAGE_TACTICS.get(stage, "")
    return f"## Current Stage Tactics: {stage.value.upper()}\n{tactics}"


def get_disc_tactics(disc_type: DiscType) -> str:
    """Get DISC-specific adaptation tactics."""
    return DISC_TACTICS.get(disc_type, "")
