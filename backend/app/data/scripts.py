"""Cold call and warm inbound scripts from Epiphan BDR Playbook."""

from app.data.schemas import (
    ColdCallScript,
    ObjectionPivot,
    PersonaType,
    TriggerType,
    Vertical,
    WarmCallScript,
    WarmInboundScript,
    WarmInboundVariation,
)

__all__ = [
    # Constants
    "COLD_CALL_SCRIPTS",
    "WARM_INBOUND_SCRIPTS",
    "WARM_INBOUND_OBJECTIONS",
    "SPEED_TO_LEAD_STATS",
    "READY_TO_BUY_SIGNALS",
    # Functions
    "get_script_by_vertical",
    "get_warm_script_by_trigger",
    "get_warm_script_for_call",
]

COLD_CALL_SCRIPTS: list[ColdCallScript] = [
    ColdCallScript(
        id="higher_ed",
        vertical=Vertical.HIGHER_ED,
        vertical_icon="🎓",
        target_persona="AV Director, Classroom Technology Manager",
        pattern_interrupt="Hey [Name], this is Tim from Epiphan Video - got 30 seconds?",
        value_hook="NC State manages 300+ lecture capture rooms with a team of 3 using our Pearl system. They went from constant firefighting to remote fleet management.",
        pain_question="What's your biggest headache with managing classroom recording equipment?",
        permission="Do you have two minutes to hear how they did it?",
        pivot="I hear that a lot. What about managing these remotely - is that something you're dealing with?",
        why_it_works=[
            "NC State is peer institution - immediate credibility",
            "300+ rooms speaks to scale",
            "'Team of 3' addresses understaffing reality",
            "'Remote fleet management' is the solution, not features",
        ],
        objection_pivots=[
            ObjectionPivot(
                objection="We use Panopto/Kaltura",
                response="Perfect - Pearl integrates natively with both. We're the hardware that feeds your video platform. NC State uses us with Panopto.",
            ),
            ObjectionPivot(
                objection="We're not looking right now",
                response="Totally understand. When's your next refresh cycle or construction project? I can follow up when timing is better.",
            ),
            ObjectionPivot(
                objection="We're happy with current setup",
                response="Great to hear. Quick question - how much time does your team spend on-site troubleshooting? That's usually where we help most.",
            ),
            ObjectionPivot(
                objection="Just send me information",
                response="Happy to. What's most useful - a case study from NC State, or the fleet management dashboard demo? I want to send what's relevant.",
            ),
        ],
    ),
    ColdCallScript(
        id="corporate",
        vertical=Vertical.CORPORATE,
        vertical_icon="🏢",
        target_persona="VP of L&D, Corp Comms Director",
        pattern_interrupt="Hey [Name], this is Tim from Epiphan Video - got 30 seconds?",
        value_hook="OpenAI calls our Pearl system 'the workhorse of our streams' - broadcast quality without a production team.",
        pain_question="What's your biggest challenge creating high-quality training or leadership communications?",
        permission="Do you have two minutes to hear how they did it?",
        pivot="I hear that. What about getting broadcast quality without relying on external production? Is that something you're dealing with?",
        why_it_works=[
            "OpenAI is aspirational reference - tech credibility",
            "'Workhorse' implies reliability",
            "'Without production team' addresses resource constraint",
            "Focus on outcome (quality) not features",
        ],
        objection_pivots=[
            ObjectionPivot(
                objection="We just use Teams/Zoom",
                response="Teams caps at 720p and any mobile participant degrades quality. For leadership comms, you need broadcast quality. Pearl delivers that.",
            ),
            ObjectionPivot(
                objection="IT handles this",
                response="Got it - who in IT should I talk to about recording infrastructure? I want to make sure I'm reaching the right person.",
            ),
            ObjectionPivot(
                objection="We outsource production",
                response="What's that costing annually? Most see ROI in year one switching to Pearl. Worth a quick comparison?",
            ),
            ObjectionPivot(
                objection="Not the right time",
                response="When would be better? I can follow up when you're planning next year's budget or a specific project.",
            ),
        ],
    ),
    ColdCallScript(
        id="healthcare",
        vertical=Vertical.HEALTHCARE,
        vertical_icon="🏥",
        target_persona="Simulation Center Director",
        pattern_interrupt="Hey [Name], this is Tim from Epiphan Video - got 30 seconds?",
        value_hook="Medical schools use Pearl for sim lab recording - PHI never leaves your network, fully HIPAA-compliant.",
        pain_question="What's your biggest concern recording clinical simulations while staying HIPAA compliant?",
        permission="Do you have two minutes to hear how they solved it?",
        pivot="Makes sense. What about multi-angle capture for debriefing - is that something you're dealing with?",
        why_it_works=[
            "HIPAA compliance is top concern",
            "'PHI never leaves network' addresses cloud anxiety",
            "Medical schools = peer credibility",
            "Focus on compliance, not features",
        ],
        objection_pivots=[
            ObjectionPivot(
                objection="We use SimCapture already",
                response="Perfect - Pearl feeds into SimCapture as the hardware layer. Same workflow, better multi-angle capture. We integrate natively.",
            ),
            ObjectionPivot(
                objection="Budget is tight",
                response="Pearl-2 at $7,999 vs. OR-specific systems at $50K+. For simulation, it's 90% less cost. Worth a comparison?",
            ),
            ObjectionPivot(
                objection="IT handles this",
                response="Who in IT should I talk to? I want to connect with whoever manages simulation technology.",
            ),
            ObjectionPivot(
                objection="We're not looking",
                response="When's your next SSH accreditation visit? That's usually when simulation recording becomes priority.",
            ),
        ],
    ),
    ColdCallScript(
        id="house_of_worship",
        vertical=Vertical.HOUSE_OF_WORSHIP,
        vertical_icon="⛪",
        target_persona="Technical Director, Media Director",
        pattern_interrupt="Hey [Name], this is Tim from Epiphan Video - got 30 seconds?",
        value_hook="Churches use our Pearl Mini because volunteers can run it - 5-minute training, no PC to crash on Sunday.",
        pain_question="What's your biggest concern about the stream failing during service?",
        permission="Do you have two minutes to hear how they solved it?",
        pivot="Totally get it. How often do you have to train new volunteers? That's usually where we help most.",
        why_it_works=[
            "Volunteers are the reality",
            "'5-minute training' addresses turnover",
            "'No PC to crash' is the key differentiator",
            "'Sunday' speaks to mission-critical timing",
        ],
        objection_pivots=[
            ObjectionPivot(
                objection="We use vMix/OBS",
                response="Those are great until Windows updates mid-service. Hardware doesn't have that problem. Pearl just works.",
            ),
            ObjectionPivot(
                objection="Our volunteers handle complex stuff",
                response="How often do you have volunteer turnover? Simple means less retraining every time someone new joins.",
            ),
            ObjectionPivot(
                objection="Budget is tight",
                response="Pearl Mini at $3,999 is a one-time cost. No subscriptions. Compare that to your streaming platform monthly fees.",
            ),
            ObjectionPivot(
                objection="We're a small congregation",
                response="Pearl Nano at $1,999 is designed for smaller setups. Same reliability, smaller price.",
            ),
        ],
    ),
    ColdCallScript(
        id="government",
        vertical=Vertical.GOVERNMENT,
        vertical_icon="🏛️",
        target_persona="Court Administrator, Clerk of Court",
        pattern_interrupt="Hey [Name], this is Tim from Epiphan Video - got 30 seconds?",
        value_hook="Courts are switching to Pearl because 1.78 million hearings go unrecorded annually due to court reporter shortages.",
        pain_question="What's your biggest challenge capturing the record for all proceedings right now?",
        permission="Do you have two minutes to hear how other courts solved it?",
        pivot="I hear that. What about the court reporter shortage - is that affecting your operations?",
        why_it_works=[
            "1.78M statistic is compelling",
            "Court reporter shortage is nationwide crisis",
            "'Capturing the record' speaks to their mission",
            "Positions Pearl as solution to real problem",
        ],
        objection_pivots=[
            ObjectionPivot(
                objection="Judges prefer court reporters",
                response="Electronic recording supplements, not replaces. It's for the 1.78M hearings without any record today.",
            ),
            ObjectionPivot(
                objection="Our state doesn't allow it",
                response="33 of 35 states now permit electronic recording. Let me check your specific state - things may have changed.",
            ),
            ObjectionPivot(
                objection="Procurement is complex",
                response="We're on TIPS and Sourcewell for cooperative purchasing. Makes it much simpler.",
            ),
            ObjectionPivot(
                objection="We have JAVS",
                response="JAVS is excellent for courts. Pearl works for other government applications too - Open Meeting Law, public hearings. Worth a comparison?",
            ),
        ],
    ),
    ColdCallScript(
        id="live_events",
        vertical=Vertical.LIVE_EVENTS,
        vertical_icon="🎬",
        target_persona="Technical Director, Production Director",
        pattern_interrupt="Hey [Name], this is Tim from Epiphan Video - got 30 seconds?",
        value_hook="Production companies choose Pearl because hardware doesn't blue-screen during a $50K event like PC-based systems.",
        pain_question="What's your biggest concern about reliability during high-stakes live events?",
        permission="Do you have two minutes to hear how they handle it?",
        pivot="Makes sense. What's your backup plan when equipment fails? That's usually where we help.",
        why_it_works=[
            "'$50K event' speaks to stakes",
            "'Blue-screen' is visceral fear",
            "'Hardware vs. PC' is clear differentiator",
            "Production companies = peer credibility",
        ],
        objection_pivots=[
            ObjectionPivot(
                objection="We use TriCaster",
                response="TriCaster is great for production. Pearl is great for reliable recording. Many use both - TriCaster for switching, Pearl for redundant recording.",
            ),
            ObjectionPivot(
                objection="vMix is our backup",
                response="vMix on Windows is a great tool until it's not. Hardware backup doesn't have Windows update surprises.",
            ),
            ObjectionPivot(
                objection="We rent equipment",
                response="What's your annual rental spend? Pearl at $7,999 pays for itself quickly vs. ongoing rental.",
            ),
            ObjectionPivot(
                objection="Too expensive",
                response="What's the cost of losing footage from a $50K event? Pearl is insurance for your most important recordings.",
            ),
        ],
    ),
    ColdCallScript(
        id="industrial",
        vertical=Vertical.INDUSTRIAL,
        vertical_icon="🏭",
        target_persona="Training Manager, EHS Manager",
        pattern_interrupt="Hey [Name], this is Tim from Epiphan Video - got 30 seconds?",
        value_hook="Manufacturers use Pearl to capture expert knowledge before it retires - 2.7 million boomers leaving the workforce take 30 years of know-how.",
        pain_question="What's your biggest challenge transferring expertise from senior workers to new hires?",
        permission="Do you have two minutes to hear how they handle it?",
        pivot="I hear that. What happens when your most experienced person retires next year?",
        why_it_works=[
            "2.7M boomers is compelling statistic",
            "'30 years of know-how' speaks to urgency",
            "Knowledge transfer is real problem",
            "Emotional connection to retirement reality",
        ],
        objection_pivots=[
            ObjectionPivot(
                objection="We have a training program",
                response="How much of it captures your senior experts on video? That's the knowledge that walks out the door.",
            ),
            ObjectionPivot(
                objection="Our LMS handles this",
                response="Your LMS delivers content - Pearl creates it. Record your best trainer once, train 1,000 employees.",
            ),
            ObjectionPivot(
                objection="OSHA training is our focus",
                response="Video documentation of safety training is OSHA-compliant evidence. Pearl captures the proof.",
            ),
            ObjectionPivot(
                objection="ROI is unclear",
                response="What does it cost to train one new hire? Now multiply by turnover. Recording experts once saves that every time.",
            ),
        ],
    ),
]


WARM_INBOUND_SCRIPTS: list[WarmInboundScript] = [
    WarmInboundScript(
        id="content_download",
        trigger_type=TriggerType.CONTENT_DOWNLOAD,
        trigger_icon="📄",
        hubspot_signal="Downloaded whitepaper, case study, or datasheet",
        acknowledge="Hi [Name], this is Tim from Epiphan Video. I saw you downloaded our [content name] - thanks for checking that out.",
        connect="Most people exploring that are looking at [common challenge]. Is that on your radar?",
        qualify="Are you actively evaluating solutions, or just researching for now?",
        propose="Would it help to have a quick call to answer any questions from what you read?",
        variations=[
            WarmInboundVariation(
                context="Case study download",
                script="I saw you grabbed the NC State case study. They had similar challenges with managing 300+ rooms. Is scale something you're dealing with?",
            ),
            WarmInboundVariation(
                context="Datasheet download",
                script="Are you actively sizing a solution, or comparing options right now?",
            ),
            WarmInboundVariation(
                context="Whitepaper download",
                script="What specifically caught your interest about [topic]? I can point you to the most relevant resources.",
            ),
        ],
    ),
    WarmInboundScript(
        id="webinar_attended",
        trigger_type=TriggerType.WEBINAR_ATTENDED,
        trigger_icon="🎥",
        hubspot_signal="Registered for or attended webinar",
        acknowledge="Hi [Name], this is Tim from Epiphan Video. I saw you attended our [webinar title] - thanks for joining.",
        connect="Did any of the [topic] content resonate with what you're working on?",
        qualify="Are you dealing with [key challenge from webinar] at [Company]?",
        propose="Would a follow-up conversation be helpful to dig into your specific situation?",
        variations=[
            WarmInboundVariation(
                context="Registered but didn't attend",
                script="Quick question - what specifically caught your interest about [topic]? I can send the recording if you missed it.",
            ),
            WarmInboundVariation(
                context="Asked question during webinar",
                script="I wanted to make sure you got a complete answer to your question about [topic]. Is [brief answer] addressing what you were thinking?",
            ),
        ],
    ),
    WarmInboundScript(
        id="demo_request",
        trigger_type=TriggerType.DEMO_REQUEST,
        trigger_icon="🎯",
        hubspot_signal="Submitted demo request form (HIGHEST INTENT)",
        acknowledge="Hi [Name], this is Tim from Epiphan Video. Got your demo request - wanted to get that scheduled while it's fresh.",
        connect="Before we book time, what's driving the interest? Is this for [likely use case]?",
        qualify="Is this for a specific project with a timeline, or building a business case?",
        propose="Let me get you on the calendar - what works better, early or later this week?",
        variations=[
            WarmInboundVariation(
                context="Specific use case mentioned",
                script="You mentioned [use case] - perfect. I'll tailor the demo to focus on that. What's your timeline for making a decision?",
            ),
        ],
    ),
    WarmInboundScript(
        id="pricing_page",
        trigger_type=TriggerType.PRICING_PAGE,
        trigger_icon="💰",
        hubspot_signal="Visited pricing page (high intent behavior)",
        acknowledge="Hi [Name], this is Tim from Epiphan Video. I noticed you were checking out our pricing page.",
        connect="Are you putting together a budget, or comparing options right now?",
        qualify="What's the scope - single unit or fleet deployment?",
        propose="I can walk you through pricing for your specific situation. Do you have a few minutes?",
        variations=[
            WarmInboundVariation(
                context="Multiple pricing page visits",
                script="I saw you've been back to pricing a couple times. Are there specific questions I can help answer?",
            ),
        ],
    ),
    WarmInboundScript(
        id="contact_form",
        trigger_type=TriggerType.CONTACT_FORM,
        trigger_icon="📝",
        hubspot_signal="Submitted general contact form",
        acknowledge="Hi [Name], this is Tim from Epiphan Video. I got your inquiry - thanks for reaching out.",
        connect="What prompted you to get in touch?",
        qualify="Are you evaluating solutions for [likely use case], or something else?",
        propose="Happy to help - what would be most useful right now?",
        variations=[
            WarmInboundVariation(
                context="Specific question in form",
                script="[Brief answer to their question]. But what's behind the question? Are you evaluating solutions for [likely use case]?",
            ),
        ],
    ),
    WarmInboundScript(
        id="trade_show",
        trigger_type=TriggerType.TRADE_SHOW,
        trigger_icon="🎪",
        hubspot_signal="Scanned badge or added to list at trade show",
        acknowledge="Hi [Name], this is Tim from Epiphan Video. We connected at [show name] - thanks for stopping by.",
        connect="What stood out to you from what you saw at our booth?",
        qualify="Is [what they looked at] something you're actively evaluating?",
        propose="Would a follow-up demo be helpful now that you're back in the office?",
        variations=[
            WarmInboundVariation(
                context="Within 48 hours of show",
                script="I wanted to follow up while it's fresh - what stood out from what you saw?",
            ),
            WarmInboundVariation(
                context="3-7 days after show",
                script="Now that you're back in the office, is [what they looked at] still a priority?",
            ),
        ],
    ),
    WarmInboundScript(
        id="referral",
        trigger_type=TriggerType.REFERRAL,
        trigger_icon="🤝",
        hubspot_signal="Referred by existing customer or partner",
        acknowledge="Hi [Name], this is Tim from Epiphan Video. [Referrer name] suggested I reach out.",
        connect="What's going on at [Company] that made them think of us?",
        qualify="[Referrer] uses Pearl for [use case] - sounds like you might benefit from something similar?",
        propose="Would a quick call be helpful to explore how we might help?",
        variations=[
            WarmInboundVariation(
                context="Strong referrer relationship",
                script="[Referrer] speaks highly of your team. They mentioned you might be dealing with [challenge]. Is that accurate?",
            ),
        ],
    ),
    WarmInboundScript(
        id="return_visitor",
        trigger_type=TriggerType.RETURN_VISITOR,
        trigger_icon="🔄",
        hubspot_signal="Return visit after previous engagement",
        acknowledge="Hi [Name], this is Tim from Epiphan Video. I noticed you're back on our site.",
        connect="Something changed - is this just timing now?",
        qualify="Where did things land last time? Still evaluating, or priorities shifted?",
        propose="Would it help to pick up where we left off?",
        variations=[
            WarmInboundVariation(
                context="Previous demo, no decision",
                script="We did a demo back in [month] - wanted to check in. Where did things land?",
            ),
            WarmInboundVariation(
                context="Cold lead showing activity",
                script="I see you're back looking at [product/content]. Did something change on your end?",
            ),
        ],
    ),
]


# Universal objections for warm calls
WARM_INBOUND_OBJECTIONS = [
    {
        "objection": "Just researching",
        "response": "What triggered the research? Sometimes a quick call saves hours of Googling.",
    },
    {
        "objection": "Not ready for sales call",
        "response": "What questions could I answer without a full pitch?",
    },
    {
        "objection": "Send more info",
        "response": "Happy to. What specifically would be most useful - pricing, case studies, technical specs?",
    },
    {
        "objection": "My boss handles this",
        "response": "Got it. Would it help if I sent you something you could share with them? What would resonate?",
    },
    {
        "objection": "We're still early",
        "response": "Makes sense. What's your timeline looking like? I can check back when it's more relevant.",
    },
    {
        "objection": "Timing isn't right",
        "response": "When does timing get better? I'll put a note to reconnect then.",
    },
]

# Speed-to-lead statistics
SPEED_TO_LEAD_STATS = [
    {"response_time": "< 5 minutes", "conversion_impact": "9x more likely to convert"},
    {"response_time": "5-30 minutes", "conversion_impact": "4x more likely to convert"},
    {"response_time": "30-60 minutes", "conversion_impact": "2x more likely to convert"},
    {"response_time": "> 1 hour", "conversion_impact": "Baseline conversion"},
    {"response_time": "> 24 hours", "conversion_impact": "Lead is likely cold"},
]

# Ready-to-buy signals (accelerate, don't slow down)
READY_TO_BUY_SIGNALS = [
    "We have budget this quarter",
    "My boss asked me to look into this",
    "We need this for [specific event/date]",
    "We're comparing you to [competitor]",
    "What's your fastest implementation?",
    "Can you do a demo this week?",
    "Who else do I need to involve?",
]


def get_script_by_vertical(vertical: Vertical) -> ColdCallScript | None:
    """Get cold call script for a vertical."""
    for script in COLD_CALL_SCRIPTS:
        if script.vertical == vertical:
            return script
    return None


def get_warm_script_by_trigger(trigger: TriggerType) -> WarmInboundScript | None:
    """Get warm inbound script for a trigger type."""
    for script in WARM_INBOUND_SCRIPTS:
        if script.trigger_type == trigger:
            return script
    return None


def get_warm_script_for_call(
    trigger_type: TriggerType,
    persona_type: PersonaType | None = None,
) -> WarmCallScript | None:
    """Get the best warm script for a call based on persona and trigger.

    This is the primary integration point for warm inbound calls. It:
    1. First tries to find a persona-specific script (persona + trigger)
    2. Falls back to a generic trigger-based script if no persona match

    Args:
        trigger_type: What action the lead took (content download, demo request, etc.)
        persona_type: Who the lead is (AV Director, L&D Director, etc.), or None if unknown

    Returns:
        WarmCallScript with ACQP fields (acknowledge, connect, qualify, propose) and metadata,
        or None if no script available for this trigger.

    Example:
        >>> script = get_warm_script_for_call(
        ...     trigger_type=TriggerType.CONTENT_DOWNLOAD,
        ...     persona_type=PersonaType.AV_DIRECTOR
        ... )
        >>> print(script.acknowledge)
        "Hi [Name], this is Tim from Epiphan Video..."
    """
    from app.data.persona_warm_scripts import get_warm_script_for_persona_trigger

    # Try persona-specific script first
    if persona_type is not None:
        persona_variation = get_warm_script_for_persona_trigger(persona_type, trigger_type)
        if persona_variation is not None:
            return WarmCallScript(
                acknowledge=persona_variation.acknowledge,
                connect=persona_variation.connect,
                qualify=persona_variation.qualify,
                propose=persona_variation.propose,
                discovery_questions=persona_variation.discovery_questions,
                what_to_listen_for=persona_variation.what_to_listen_for,
                source="persona_specific",
                persona_type=persona_type.value,
                trigger_type=trigger_type.value,
            )

    # Fall back to generic trigger-based script
    generic_script = get_warm_script_by_trigger(trigger_type)
    if generic_script is not None:
        return WarmCallScript(
            acknowledge=generic_script.acknowledge,
            connect=generic_script.connect,
            qualify=generic_script.qualify,
            propose=generic_script.propose,
            discovery_questions=[],  # Generic scripts don't have these
            what_to_listen_for=[],
            source="trigger_generic",
            persona_type=persona_type.value if persona_type else None,
            trigger_type=trigger_type.value,
        )

    return None
