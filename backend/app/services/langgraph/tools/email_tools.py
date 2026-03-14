"""Tools for Email Personalization Agent.

Provides email templates, personalization hooks extraction,
and prompt building for LLM-based email generation.
"""

from typing import Any

from app.data.lead_schemas import Lead
from app.services.langgraph.states import ResearchBrief

# Email templates for different sequence steps
EMAIL_TEMPLATES = {
    "pattern_interrupt": {
        "subject_patterns": [
            "Quick question about {company}'s {topic}",
            "{first_name}, noticed something about {company}",
            "Idea for {company}'s {topic}",
            "{company} + video capture?",
        ],
        "structure": {
            "opener": "pattern_interrupt",  # Unexpected angle
            "body": "value_proposition",
            "cta": "soft_ask",
        },
        "tone": "casual_professional",
        "length": "short",  # 3-4 sentences
    },
    "pain_point": {
        "subject_patterns": [
            "The {pain_point} problem at {company}",
            "{first_name}, solving {pain_point}",
            "How {similar_company} fixed {pain_point}",
            "Re: {topic} at {company}",
        ],
        "structure": {
            "opener": "pain_acknowledgment",
            "body": "case_study_reference",
            "cta": "specific_ask",
        },
        "tone": "empathetic_professional",
        "length": "medium",  # 5-7 sentences
    },
    "breakup": {
        "subject_patterns": [
            "Closing the loop, {first_name}",
            "Should I close your file?",
            "One last thing before I go",
            "Giving up (for now)",
        ],
        "structure": {
            "opener": "acknowledge_silence",
            "body": "final_value",
            "cta": "yes_no_question",
        },
        "tone": "direct_friendly",
        "length": "very_short",  # 2-3 sentences
    },
    "nurture": {
        "subject_patterns": [
            "Thought you'd find this interesting, {first_name}",
            "Resource: {topic}",
            "{industry} insights for {company}",
            "Quick read on {topic}",
        ],
        "structure": {
            "opener": "value_first",
            "body": "educational_content",
            "cta": "passive_engagement",
        },
        "tone": "helpful_expert",
        "length": "medium",
    },
}


# Pain points by persona
PERSONA_PAIN_POINTS = {
    "av_director": [
        "Manual recording and scheduling is time-consuming",
        "Inconsistent video quality across rooms",
        "Difficult to scale lecture capture",
        "Integration challenges with existing AV systems",
        "Limited analytics on content usage",
    ],
    "ld_director": [
        "Creating engaging training content is expensive",
        "Measuring training effectiveness is difficult",
        "Onboarding takes too long",
        "Compliance training is tedious",
        "Remote training lacks engagement",
    ],
    "technical_director": [
        "Complex streaming workflows",
        "Reliability concerns for live events",
        "Integration with production equipment",
        "Scaling for multiple simultaneous events",
        "Post-production bottlenecks",
    ],
    "simulation_director": [
        "Capturing multi-angle simulation scenarios",
        "Debriefing requires manual video editing",
        "Difficult to standardize evaluation",
        "Storage and retrieval of simulation recordings",
        "Real-time feedback during simulations",
    ],
    "court_admin": [
        "Court recording compliance requirements",
        "Managing multiple courtroom recordings",
        "Secure storage and retention policies",
        "Integration with case management systems",
        "Supporting hybrid court proceedings",
    ],
    "corp_comms_director": [
        "Producing professional town halls is complex",
        "Reaching distributed workforce",
        "Measuring employee engagement",
        "On-demand access to past communications",
        "Executive presentation quality",
    ],
    "ehs_manager": [
        "Documenting safety training completion",
        "Capturing field safety inspections",
        "Incident documentation and review",
        "Multilingual training requirements",
        "Proving compliance during audits",
    ],
    "law_firm_it": [
        "Secure deposition recording",
        "Supporting hybrid depositions",
        "Integration with legal document management",
        "Chain of custody for video evidence",
        "Client confidentiality requirements",
    ],
}

# Generic pain points for unknown personas
GENERIC_PAIN_POINTS = [
    "Manual video workflows are inefficient",
    "Scaling video capture is challenging",
    "Integration with existing systems is complex",
    "Video quality consistency is difficult",
    "Analytics and reporting are limited",
]


# CTAs by sequence step
SEQUENCE_CTAS = {
    1: "Would a 15-minute call be worth your time to explore this?",
    2: "Happy to share how {similar_company} addressed this - interested?",
    3: "Should I close your file, or is there a better time to connect?",
    4: "No need to reply - just thought this might be useful.",
}


def get_email_template(email_type: str) -> dict[str, Any] | None:
    """
    Get email template for a specific type.

    Args:
        email_type: Type of email (pattern_interrupt, pain_point, breakup, nurture)

    Returns:
        Template dict or None if not found
    """
    return EMAIL_TEMPLATES.get(email_type)


def extract_personalization_hooks(
    research_brief: ResearchBrief,
) -> list[dict[str, str]]:
    """
    Extract personalization hooks from research brief.

    Args:
        research_brief: Research brief with company intelligence

    Returns:
        List of hooks with type and content
    """
    hooks = []

    # News-based hooks
    for news in research_brief.get("recent_news", [])[:3]:
        title = news.get("title", "")
        if title:
            hooks.append({
                "type": "news",
                "content": title,
                "usage": f"I noticed {title[:50]}...",
            })

    # Talking point hooks
    for point in research_brief.get("talking_points", [])[:3]:
        hooks.append({
            "type": "talking_point",
            "content": point,
            "usage": point,
        })

    # Company overview hook
    overview = research_brief.get("company_overview", "")
    if overview and len(overview) > 50:
        hooks.append({
            "type": "company",
            "content": overview[:200],
            "usage": f"Given {overview[:100]}...",
        })

    return hooks


def get_pain_points_for_persona(persona_id: str) -> list[str]:
    """
    Get pain points relevant to a specific persona.

    Args:
        persona_id: Persona identifier

    Returns:
        List of pain points
    """
    return PERSONA_PAIN_POINTS.get(persona_id, GENERIC_PAIN_POINTS)


def get_cta_for_sequence_step(step: int) -> str:
    """
    Get appropriate CTA for a sequence step.

    Args:
        step: Sequence step (1-4)

    Returns:
        CTA string
    """
    return SEQUENCE_CTAS.get(step, SEQUENCE_CTAS[1])


def build_email_prompt(
    lead: Lead,
    research_brief: ResearchBrief,
    email_type: str,
    sequence_step: int,
    pain_points: list[str],
    personalization_hooks: list[str],
) -> str:
    """
    Build LLM prompt for email generation.

    Args:
        lead: Target lead
        research_brief: Research intelligence
        email_type: Type of email to generate
        sequence_step: Current sequence step (1-4)
        pain_points: Relevant pain points
        personalization_hooks: Hooks for personalization

    Returns:
        Formatted prompt for LLM
    """
    template = get_email_template(email_type) or EMAIL_TEMPLATES["pattern_interrupt"]

    prompt = f"""Generate a personalized sales email for:

**Recipient:**
- Name: {lead.first_name} {lead.last_name or ''}
- Company: {lead.company}
- Title: {lead.title or 'Unknown'}
- Email: {lead.email}

**Company Intelligence:**
{research_brief.get('company_overview', 'No overview available')}

**Personalization Hooks:**
{chr(10).join(f'- {hook}' for hook in personalization_hooks) if personalization_hooks else '- No specific hooks'}

**Relevant Pain Points:**
{chr(10).join(f'- {pain}' for pain in pain_points[:3]) if pain_points else '- General video capture challenges'}

**Email Requirements:**
- Type: {email_type.replace('_', ' ').title()}
- Sequence Step: {sequence_step} of 4
- Tone: {template.get('tone', 'professional')}
- Length: {template.get('length', 'short')} (keep it concise)
- CTA: {get_cta_for_sequence_step(sequence_step)}

**Subject Line Patterns (choose one or adapt):**
{chr(10).join(f'- {p}' for p in list(template.get('subject_patterns', []))[:3])}

Generate a compelling, personalized email that uses at least one personalization hook naturally.
Do NOT include a signature placeholder or [Name] tag — just the email body text.
"""

    return prompt
