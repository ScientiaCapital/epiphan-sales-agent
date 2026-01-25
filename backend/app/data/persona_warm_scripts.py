"""Persona-specific warm lead scripts.

Combines trigger context (what action they took) with persona pain points
(who they are) for highly targeted warm inbound calls.

Core Insight: An AV Director downloading a case study gets different
messaging than an L&D Director - they have completely different pain points!
"""

from app.data.schemas import (
    PersonaObjectionResponse,
    PersonaTriggerVariation,
    PersonaType,
    PersonaWarmContext,
    PersonaWarmScript,
    TriggerType,
)

# ============================================================================
# AV Director (Higher Education)
# Primary Pain: Too many rooms, too few people
# Reference Story: NC State - 300+ rooms, team of 3
# ============================================================================

AV_DIRECTOR_WARM_SCRIPT = PersonaWarmScript(
    id="av_director_warm",
    persona_type=PersonaType.AV_DIRECTOR,
    persona_title="AV Director",
    primary_pain="Too many rooms, too few people - understaffed teams managing 50-500+ spaces",
    value_proposition="Remote fleet management that lets small teams manage large room counts without constant on-site visits",
    reference_story="NC State: 300+ rooms managed by a team of 3 using Pearl's fleet management dashboard",
    trigger_variations=[
        # Content Download
        PersonaTriggerVariation(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Thanks for grabbing our [content] - I noticed you're at [University/Company]. Are you managing classroom technology there?",
            connect="Most AV directors who download that are dealing with the 'too many rooms, too few people' challenge. Is remote troubleshooting something you're dealing with?",
            qualify="How many rooms are you managing, and how big is your support team?",
            propose="NC State manages 300+ rooms with a team of 3 using our fleet management dashboard. Would a quick look at how they do it be useful?",
            discovery_questions=[
                "How many rooms/spaces do you currently manage?",
                "How many people on your team handle AV support?",
                "Can you troubleshoot remotely, or do you have to be on-site?",
                "When's your next major refresh or construction project?",
            ],
            what_to_listen_for=[
                "Team size relative to room count (understaffed = pain)",
                "Mentions of remote campus locations",
                "Complaints about travel time between buildings",
                "Construction projects or refresh cycles coming up",
            ],
        ),
        # Webinar Attended
        PersonaTriggerVariation(
            trigger_type=TriggerType.WEBINAR_ATTENDED,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Thanks for attending our [webinar title] - did any of the fleet management content resonate with what you're dealing with?",
            connect="A lot of AV directors who attend that webinar are struggling with the same thing - too many rooms for their team size. Is that familiar?",
            qualify="Are you managing multiple buildings or campuses? What does your support model look like?",
            propose="We showed NC State's setup in the webinar - would it help to see a more detailed walkthrough tailored to your environment?",
            discovery_questions=[
                "What specifically caught your interest about the webinar?",
                "How does your current remote management capability compare?",
                "What happens when equipment fails during a critical class?",
            ],
            what_to_listen_for=[
                "Questions about specific webinar content",
                "Mentions of pain points that align with NC State's challenges",
                "Interest in the dashboard or remote capabilities",
            ],
        ),
        # Demo Request (Highest Intent)
        PersonaTriggerVariation(
            trigger_type=TriggerType.DEMO_REQUEST,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Got your demo request - wanted to get that scheduled while it's fresh.",
            connect="Before we book time, what's driving the interest? Is this for managing a large room deployment?",
            qualify="Is this for a specific project with a timeline, or building a business case? How many rooms are we talking about?",
            propose="Perfect - let me get you on the calendar. I'll tailor the demo to show our fleet management dashboard since that's usually what makes the difference for AV teams. What works better, early or later this week?",
            discovery_questions=[
                "What's the scope - how many rooms?",
                "When do you need this deployed by?",
                "Who else needs to be involved in the evaluation?",
            ],
            what_to_listen_for=[
                "Specific project timeline (construction, refresh)",
                "Budget already allocated",
                "Mentions of evaluation committee or other stakeholders",
            ],
        ),
        # Pricing Page
        PersonaTriggerVariation(
            trigger_type=TriggerType.PRICING_PAGE,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. I noticed you were checking out our pricing page.",
            connect="Are you putting together a budget for a room deployment, or comparing options right now?",
            qualify="What's the scope - single unit or fleet deployment? How many rooms are you looking to equip?",
            propose="For fleet deployments, the per-room cost drops significantly. I can walk you through the volume pricing and show you what NC State pays for 300+ rooms. Would that be useful?",
            discovery_questions=[
                "What's your timeline for making a decision?",
                "Are you evaluating Pearl against anything else?",
                "Who else is involved in the budget approval?",
            ],
            what_to_listen_for=[
                "Budget cycle timing",
                "Competitors being evaluated",
                "Procurement process hints",
            ],
        ),
    ],
    objections=[
        PersonaObjectionResponse(
            objection="We're standardized on Crestron/Extron",
            response="Pearl integrates natively with Crestron and Extron control systems. It adds recording and streaming capability without replacing your ecosystem.",
            persona_context="AV Directors care about ecosystem compatibility - they've invested heavily in control systems.",
        ),
        PersonaObjectionResponse(
            objection="Too expensive upfront",
            response="Compare 5-year TCO: no recurring fees vs. software subscriptions. Plus, remote management reduces on-site support costs. NC State cut their support ticket volume by 40%.",
            persona_context="AV Directors think in TCO and support costs, not just purchase price.",
        ),
        PersonaObjectionResponse(
            objection="Current system works fine",
            response="How much time does your team spend traveling between buildings for troubleshooting? That's usually where we save teams 10+ hours a week.",
            persona_context="Pivot to time savings - AV Directors are always short on staff.",
        ),
        PersonaObjectionResponse(
            objection="We don't have time to evaluate",
            response="15-minute demo shows the fleet management dashboard. If it doesn't solve your remote management pain in 15 minutes, I'll stop wasting your time.",
            persona_context="Respect their time - they're understaffed. Make the demo commitment minimal.",
        ),
    ],
    context_cues=PersonaWarmContext(
        what_to_listen_for=[
            "Team size relative to room count",
            "Mentions of construction or refresh projects",
            "Complaints about being on-site constantly",
            "Integration requirements with existing control systems",
        ],
        buying_signals=[
            "We have a construction project starting...",
            "I can't keep managing this many rooms with this team size",
            "We had a major failure during [important event]",
            "What's the support like?",
        ],
        red_flags=[
            "Just took this role - may not have budget authority yet",
            "Locked into multi-year competitor contract",
            "IT controls the budget, not AV",
        ],
    ),
)


# ============================================================================
# L&D Director (Corporate)
# Primary Pain: Can't scale content without scaling costs
# Reference Story: OpenAI - "workhorse of our streams"
# ============================================================================

LD_DIRECTOR_WARM_SCRIPT = PersonaWarmScript(
    id="ld_director_warm",
    persona_type=PersonaType.LD_DIRECTOR,
    persona_title="L&D Director",
    primary_pain="Can't scale content creation without scaling costs - production bottleneck limits training reach",
    value_proposition="Self-service content capture that lets SMEs record broadcast-quality training without a production team",
    reference_story="OpenAI calls Pearl 'the workhorse of our streams' - broadcast quality without production overhead",
    trigger_variations=[
        # Content Download
        PersonaTriggerVariation(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Thanks for downloading our [content] - I noticed you're in L&D at [Company].",
            connect="Most L&D leaders who download that are trying to scale content creation without scaling their production budget. Is that resonating?",
            qualify="How are you creating training content today? In-house team, outsourced, or a mix?",
            propose="OpenAI uses Pearl as the workhorse of their streams - broadcast quality without a production team. Would a quick look at their setup be useful?",
            discovery_questions=[
                "How much SME time do you spend on training delivery?",
                "What's your cost per learner, and how are you trying to reduce it?",
                "How long does it take to create a new training module?",
                "What happens when a key expert leaves or retires?",
            ],
            what_to_listen_for=[
                "Production backlog mentions",
                "SME availability constraints",
                "Cost per learner concerns",
                "Knowledge loss from retiring experts",
            ],
        ),
        # Webinar Attended
        PersonaTriggerVariation(
            trigger_type=TriggerType.WEBINAR_ATTENDED,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Thanks for joining our [webinar title] - did the self-service capture approach resonate with your team's challenges?",
            connect="L&D leaders who attend that webinar are usually hitting a production ceiling - they need more content but can't afford more production resources. Sound familiar?",
            qualify="What's your current production bottleneck? Is it SME time, production capacity, or budget?",
            propose="I can show you how companies like OpenAI get broadcast quality without production overhead. Would that be valuable?",
            discovery_questions=[
                "What specifically caught your interest about the webinar?",
                "How does your current production workflow compare?",
                "Are you delivering consistent training across all locations?",
            ],
            what_to_listen_for=[
                "Questions about production workflow",
                "Interest in reducing production dependency",
                "Multi-location training challenges",
            ],
        ),
        # Demo Request (Highest Intent)
        PersonaTriggerVariation(
            trigger_type=TriggerType.DEMO_REQUEST,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Got your demo request - let's get that scheduled.",
            connect="Before we book time, what's driving the interest? Is this about scaling your training content production?",
            qualify="Is this for a specific training initiative, or building a case for self-service capture capability? What's your timeline?",
            propose="Perfect - I'll show you how OpenAI and similar companies use Pearl for self-service SME capture. What works better, early or later this week?",
            discovery_questions=[
                "What training programs are you looking to scale?",
                "What's your current production capacity?",
                "Who else needs to see this to move forward?",
            ],
            what_to_listen_for=[
                "Specific training initiatives with deadlines",
                "Budget already allocated for training tech",
                "Stakeholder involvement hints",
            ],
        ),
        # Pricing Page
        PersonaTriggerVariation(
            trigger_type=TriggerType.PRICING_PAGE,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. I noticed you were checking out our pricing.",
            connect="Are you comparing us to ongoing production costs, or evaluating against other capture solutions?",
            qualify="What's the scope - single studio or multiple locations? How many content creators would need access?",
            propose="Most L&D teams see ROI in the first year compared to outsourced production. I can walk you through the comparison. Would that help?",
            discovery_questions=[
                "What are you spending annually on video production?",
                "How many training videos do you produce per year?",
                "What's your timeline for making a decision?",
            ],
            what_to_listen_for=[
                "Annual production spend (ROI comparison)",
                "Volume of content needed",
                "Budget timing",
            ],
        ),
    ],
    objections=[
        PersonaObjectionResponse(
            objection="We outsource video production",
            response="Calculate your annual contract vs. one-time hardware. Most L&D teams see ROI in the first year. Plus, you control the timeline - no waiting for agency availability.",
            persona_context="L&D Directors are measured on cost per learner - show them the math.",
        ),
        PersonaObjectionResponse(
            objection="Our LMS handles this",
            response="Your LMS delivers content - Pearl creates it. They're complementary. We integrate with all major LMS platforms.",
            persona_context="L&D Directors often conflate content delivery with content creation.",
        ),
        PersonaObjectionResponse(
            objection="Quality doesn't matter for internal training",
            response="Research shows production quality impacts learning retention by up to 40%. Plus, it reflects your employer brand to new hires.",
            persona_context="L&D Directors care about training effectiveness metrics.",
        ),
        PersonaObjectionResponse(
            objection="SMEs don't have time to record",
            response="That's exactly the point - record once, deploy forever. One day of SME time creates content that trains thousands of employees for years.",
            persona_context="Flip the objection - recording saves SME time long-term.",
        ),
    ],
    context_cues=PersonaWarmContext(
        what_to_listen_for=[
            "Production backlog size",
            "SME availability constraints",
            "Cost per learner metrics",
            "Knowledge transfer urgency (retirements)",
        ],
        buying_signals=[
            "We're trying to scale our training capacity",
            "Our production backlog is X months",
            "Key experts are retiring and we're losing knowledge",
            "We need to reduce training travel costs",
        ],
        red_flags=[
            "IT controls training tech budget",
            "Just launched new LMS - not ready to add tools",
            "Outsourcing contract just renewed",
        ],
    ),
)


# ============================================================================
# Technical Director (House of Worship / Live Events)
# Primary Pain: Can't fail on Sunday / Equipment failures during live events
# Reference Story: 5-minute volunteer training, no PC to crash
# ============================================================================

TECHNICAL_DIRECTOR_WARM_SCRIPT = PersonaWarmScript(
    id="technical_director_warm",
    persona_type=PersonaType.TECHNICAL_DIRECTOR,
    persona_title="Technical Director",
    primary_pain="Can't fail on Sunday - equipment failures during live events cause panic, and volunteer turnover means constant retraining",
    value_proposition="Hardware reliability that doesn't crash like PCs, with touchscreen simplicity that volunteers learn in 5 minutes",
    reference_story="Churches use Pearl because volunteers can run it - 5-minute training, no PC to crash on Sunday",
    trigger_variations=[
        # Content Download
        PersonaTriggerVariation(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Thanks for downloading our [content] - are you running production for a church or live event venue?",
            connect="Most technical directors who download that are worried about the same thing - equipment failing during a live event. Is reliability a concern for you?",
            qualify="What's your current production setup? Staff-operated or volunteer-run?",
            propose="Churches use Pearl because volunteers can run it after 5 minutes of training, and hardware doesn't crash like PCs. Would a quick look be useful?",
            discovery_questions=[
                "What's your biggest Sunday morning (or event day) worry?",
                "Have you had equipment failures during a service or event?",
                "How long does it take to train a new volunteer?",
                "What would make your workflow simpler?",
            ],
            what_to_listen_for=[
                "Mentions of past failures during services",
                "Volunteer turnover challenges",
                "PC/software reliability complaints",
                "Complexity frustrations",
            ],
        ),
        # Webinar Attended
        PersonaTriggerVariation(
            trigger_type=TriggerType.WEBINAR_ATTENDED,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Thanks for attending our [webinar title] - did the hardware reliability discussion hit home?",
            connect="Technical directors at the webinar usually have a war story about equipment failing during an important event. What's yours?",
            qualify="Are you running with staff or volunteers? What's your current equipment setup?",
            propose="I can show you how the touchscreen operation works - most volunteers are comfortable after one walkthrough. Would that be helpful?",
            discovery_questions=[
                "What specifically caught your interest about the webinar?",
                "How does your current reliability compare?",
                "What's your backup plan when equipment fails?",
            ],
            what_to_listen_for=[
                "Reliability concerns",
                "Volunteer training challenges",
                "Interest in touchscreen simplicity",
            ],
        ),
        # Demo Request (Highest Intent)
        PersonaTriggerVariation(
            trigger_type=TriggerType.DEMO_REQUEST,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Got your demo request - let's get that scheduled before your next event.",
            connect="What's driving the interest? Is this about reliability, simplicity, or both?",
            qualify="Is this for a specific production upgrade, or exploring options? What events do you need it for?",
            propose="I'll show you the touchscreen interface that volunteers learn in 5 minutes, and we can talk about how hardware differs from PC-based solutions. What day works best?",
            discovery_questions=[
                "What events do you need to support?",
                "What's your timeline for upgrading?",
                "Who else needs to be involved?",
            ],
            what_to_listen_for=[
                "Specific events with deadlines",
                "Budget already allocated",
                "Decision-maker involvement",
            ],
        ),
        # Pricing Page
        PersonaTriggerVariation(
            trigger_type=TriggerType.PRICING_PAGE,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. I noticed you were looking at our pricing page.",
            connect="Are you comparing us to PC-based solutions, or other hardware options?",
            qualify="What's the scope - single venue or multiple locations? What features are most important?",
            propose="Pearl Mini at $3,999 is a one-time cost with no subscriptions. Compare that to ongoing software licenses and PC replacements. Want me to walk you through the comparison?",
            discovery_questions=[
                "What's your current budget situation?",
                "What are you comparing us against?",
                "What's your timeline for making a decision?",
            ],
            what_to_listen_for=[
                "Budget constraints",
                "Competitor mentions",
                "Decision timeline",
            ],
        ),
    ],
    objections=[
        PersonaObjectionResponse(
            objection="Blackmagic is cheaper",
            response="ATEM needs a PC for recording. That PC can crash - we've all seen it. Pearl is standalone hardware that just works, even when volunteers operate it.",
            persona_context="Technical Directors have war stories about PC crashes. Tap into that.",
        ),
        PersonaObjectionResponse(
            objection="We use vMix/OBS",
            response="vMix is great until Windows updates mid-service. Hardware doesn't have that problem. Many churches use Pearl as their reliability backup.",
            persona_context="Software reliability is the Achilles heel - they know it.",
        ),
        PersonaObjectionResponse(
            objection="Our volunteers can handle complex gear",
            response="How often do volunteers turn over? Every time someone new joins, you're retraining. Simple touchscreen means 5 minutes, not 5 hours.",
            persona_context="Volunteer turnover is constant - minimize retraining burden.",
        ),
        PersonaObjectionResponse(
            objection="Current setup works fine",
            response="When it works. What's the cost when it doesn't - during Easter, Christmas, or your biggest event? Pearl is insurance.",
            persona_context="Frame as insurance against high-stakes failures.",
        ),
    ],
    context_cues=PersonaWarmContext(
        what_to_listen_for=[
            "Past failure stories during events",
            "Volunteer turnover rate",
            "PC/software reliability complaints",
            "Upcoming major events",
        ],
        buying_signals=[
            "We had a failure during [important event]",
            "I can't keep training new volunteers",
            "We're building/renovating our space",
            "We need something anyone can operate",
        ],
        red_flags=[
            "Committee decision-making (slow process)",
            "Very small budget",
            "Happy with complex setup (not our customer)",
        ],
    ),
)


# ============================================================================
# Simulation Director (Healthcare)
# Primary Pain: HIPAA compliance + accreditation requirements
# Reference Story: Medical schools, local recording, PHI never leaves network
# ============================================================================

SIMULATION_DIRECTOR_WARM_SCRIPT = PersonaWarmScript(
    id="simulation_director_warm",
    persona_type=PersonaType.SIMULATION_DIRECTOR,
    persona_title="Simulation Center Director",
    primary_pain="HIPAA compliance anxiety with cloud recording, plus SSH accreditation requirements for documented debriefing",
    value_proposition="Local recording where PHI never leaves your network, with multi-source capture for effective debriefing",
    reference_story="Medical schools use Pearl for sim lab recording - PHI never leaves your network, fully HIPAA-compliant",
    trigger_variations=[
        # Content Download
        PersonaTriggerVariation(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Thanks for downloading our [content] - are you running a simulation center?",
            connect="Most simulation directors who download that are dealing with HIPAA concerns about video storage. Is compliance a priority for you?",
            qualify="How are you capturing simulation sessions today? Are you concerned about where the video is stored?",
            propose="Medical schools use Pearl because video never leaves your network - no cloud, no HIPAA exposure. Would a quick look at how they set it up be useful?",
            discovery_questions=[
                "How are you capturing simulation sessions today?",
                "Are you concerned about HIPAA compliance with video storage?",
                "When's your next SSH or LCME accreditation visit?",
                "How many simulation rooms do you need to equip?",
            ],
            what_to_listen_for=[
                "HIPAA concerns",
                "Upcoming accreditation visits",
                "Multi-angle capture needs",
                "SimCapture/LearningSpace integration needs",
            ],
        ),
        # Webinar Attended
        PersonaTriggerVariation(
            trigger_type=TriggerType.WEBINAR_ATTENDED,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Thanks for attending our [webinar title] - did the HIPAA-compliant recording approach address your concerns?",
            connect="Simulation directors at the webinar are usually worried about two things: HIPAA compliance and accreditation documentation. Which is more pressing for you?",
            qualify="What's your current capture setup? Local or cloud-based?",
            propose="I can show you how Pearl integrates with SimCapture while keeping all video on your network. Would that be helpful before your next accreditation visit?",
            discovery_questions=[
                "What specifically caught your interest about the webinar?",
                "Do you use SimCapture or LearningSpace?",
                "What's your biggest challenge with debriefing?",
            ],
            what_to_listen_for=[
                "SimCapture integration questions",
                "Accreditation timeline",
                "Debriefing effectiveness concerns",
            ],
        ),
        # Demo Request (Highest Intent)
        PersonaTriggerVariation(
            trigger_type=TriggerType.DEMO_REQUEST,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Got your demo request - let's get that scheduled.",
            connect="What's driving the interest? HIPAA compliance, accreditation prep, or expanding your sim center?",
            qualify="Is this for new rooms or upgrading existing? How many simulation spaces are we talking about?",
            propose="I'll show you the local recording workflow and SimCapture integration. What works better this week?",
            discovery_questions=[
                "How many rooms do you need to equip?",
                "What's your timeline for deployment?",
                "Do you use SimCapture or another debrief platform?",
            ],
            what_to_listen_for=[
                "Expansion plans",
                "Accreditation deadlines",
                "Budget allocation status",
            ],
        ),
        # Pricing Page
        PersonaTriggerVariation(
            trigger_type=TriggerType.PRICING_PAGE,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. I noticed you were looking at our pricing.",
            connect="Are you comparing us to simulation-specific systems, or evaluating for the first time?",
            qualify="What's the scope - how many simulation rooms? Are you looking at multi-source capture?",
            propose="Pearl-2 at $7,999 vs. OR-specific systems at $50K+. For simulation, it's 90% less cost with the same capability. Want me to walk you through the comparison?",
            discovery_questions=[
                "What's your budget for simulation technology?",
                "What are you comparing us against?",
                "What's your timeline for procurement?",
            ],
            what_to_listen_for=[
                "Budget range",
                "B-Line Medical or other competitor mentions",
                "Procurement timeline",
            ],
        ),
    ],
    objections=[
        PersonaObjectionResponse(
            objection="We use SimCapture already",
            response="Perfect - Pearl feeds into SimCapture as the hardware capture layer. Same workflow, better reliability. We integrate natively.",
            persona_context="SimCapture is common - Pearl complements, doesn't replace.",
        ),
        PersonaObjectionResponse(
            objection="B-Line Medical is simulation-specific",
            response="Pearl is more versatile and integrates with SimCapture at a fraction of the cost. Same multi-angle capability, more flexibility.",
            persona_context="B-Line is specialized but expensive - cost is our advantage.",
        ),
        PersonaObjectionResponse(
            objection="HIPAA concerns with video",
            response="Pearl records locally - video never touches cloud unless you choose. You control the data completely. That's why medical schools trust us.",
            persona_context="Local recording is the key differentiator for HIPAA.",
        ),
        PersonaObjectionResponse(
            objection="Budget is limited",
            response="Compare to OR-specific systems at $50K+. Pearl-2 at $7,999 is 90% less for the same capability. Worth a comparison?",
            persona_context="Healthcare budgets are tight - cost comparison works.",
        ),
    ],
    context_cues=PersonaWarmContext(
        what_to_listen_for=[
            "HIPAA compliance concerns",
            "Upcoming accreditation visits",
            "SimCapture or LearningSpace usage",
            "Multi-angle capture needs for debriefing",
        ],
        buying_signals=[
            "Our SSH visit is coming up in X months",
            "We're expanding/building a new simulation center",
            "We had recording failures during important sessions",
            "We're concerned about HIPAA/compliance",
        ],
        red_flags=[
            "Locked into B-Line contract",
            "IT controls all healthcare tech decisions",
            "Very early in planning (no budget yet)",
        ],
    ),
)


# ============================================================================
# Court Administrator (Government)
# Primary Pain: Court reporter shortage
# Reference Story: 33 states permit electronic recording, 1.78M hearings unrecorded
# ============================================================================

COURT_ADMINISTRATOR_WARM_SCRIPT = PersonaWarmScript(
    id="court_administrator_warm",
    persona_type=PersonaType.COURT_ADMINISTRATOR,
    persona_title="Court Administrator",
    primary_pain="Court reporter shortage leaving 1.78 million hearings without verbatim record annually",
    value_proposition="Electronic recording that supplements court reporters, ensuring all proceedings have a reliable record",
    reference_story="33 states now permit electronic recording - addressing the 1.78 million hearings that go unrecorded due to court reporter shortage",
    trigger_variations=[
        # Content Download
        PersonaTriggerVariation(
            trigger_type=TriggerType.CONTENT_DOWNLOAD,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Thanks for downloading our [content] - are you dealing with the court reporter shortage?",
            connect="Most court administrators who download that are trying to figure out how to record hearings without enough court reporters. Is that your situation?",
            qualify="What percentage of your hearings have verbatim recording today? How many courtrooms are you managing?",
            propose="33 states now permit electronic recording to address this. I can show you how other courts are supplementing their court reporters. Would that be useful?",
            discovery_questions=[
                "How are you handling the court reporter shortage?",
                "What percentage of hearings have verbatim recording today?",
                "What's your transcript turnaround time?",
                "Are you meeting state recording requirements?",
            ],
            what_to_listen_for=[
                "Court reporter shortage severity",
                "Recording coverage gaps",
                "Transcript backlog",
                "State mandate compliance",
            ],
        ),
        # Webinar Attended
        PersonaTriggerVariation(
            trigger_type=TriggerType.WEBINAR_ATTENDED,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Thanks for attending our [webinar title] - is the court reporter shortage affecting your operations?",
            connect="Court administrators at the webinar are dealing with the same crisis - not enough reporters to cover all proceedings. How bad is it in your jurisdiction?",
            qualify="What's your current recording coverage? Are there hearings that don't get recorded at all?",
            propose="I can show you how other courts have implemented electronic recording to fill the gaps. Would that help as you plan?",
            discovery_questions=[
                "What specifically caught your interest about the webinar?",
                "How does your state handle electronic recording?",
                "What's your biggest operational challenge?",
            ],
            what_to_listen_for=[
                "State-specific regulations",
                "Recording coverage gaps",
                "Interest in pilot programs",
            ],
        ),
        # Demo Request (Highest Intent)
        PersonaTriggerVariation(
            trigger_type=TriggerType.DEMO_REQUEST,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. Got your demo request - let's get that scheduled.",
            connect="What's driving the interest? Court reporter shortage, Open Meeting Law compliance, or upgrading your current recording system?",
            qualify="Is this for a specific courthouse project, or evaluating options for a broader rollout? How many courtrooms?",
            propose="I'll show you our court recording workflow and we can discuss what other jurisdictions have done. What day works best?",
            discovery_questions=[
                "How many courtrooms need recording?",
                "What's your timeline for implementation?",
                "What procurement vehicle do you use?",
            ],
            what_to_listen_for=[
                "Scope of deployment",
                "Budget and procurement path",
                "Timeline urgency",
            ],
        ),
        # Pricing Page
        PersonaTriggerVariation(
            trigger_type=TriggerType.PRICING_PAGE,
            acknowledge="Hi [Name], this is Tim from Epiphan Video. I noticed you were looking at our pricing.",
            connect="Are you comparing us to JAVS or other court-specific systems, or evaluating electronic recording for the first time?",
            qualify="What's the scope - single courtroom or multiple? Are you looking at county-wide deployment?",
            propose="We're on TIPS and Sourcewell for cooperative purchasing, which simplifies procurement. Want me to walk you through the options for your scope?",
            discovery_questions=[
                "What's your procurement process?",
                "How many courtrooms are you equipping?",
                "What's your timeline?",
            ],
            what_to_listen_for=[
                "Procurement vehicle preferences",
                "Budget constraints",
                "JAVS competitive situation",
            ],
        ),
    ],
    objections=[
        PersonaObjectionResponse(
            objection="Judges prefer court reporters",
            response="Electronic recording supplements, not replaces. It's for the 1.78 million hearings without any record today. Judges still get reporters for complex cases.",
            persona_context="Frame as supplementary, not replacement - reduces resistance.",
        ),
        PersonaObjectionResponse(
            objection="Our state doesn't allow it",
            response="33 of 35 states now permit electronic recording. Let me check your specific state - things may have changed. What state are you in?",
            persona_context="Regulations are changing rapidly - many administrators have outdated info.",
        ),
        PersonaObjectionResponse(
            objection="Procurement is complex",
            response="We're on TIPS and Sourcewell for cooperative purchasing, plus GSA Schedule for federal. Makes it much simpler than full RFP.",
            persona_context="Government procurement is a pain - cooperative purchasing is the answer.",
        ),
        PersonaObjectionResponse(
            objection="We have JAVS",
            response="JAVS is excellent for courts. Pearl works for other government applications too - Open Meeting Law, public hearings, council meetings. Worth a comparison for those use cases?",
            persona_context="Don't fight JAVS head-on - expand to other government use cases.",
        ),
    ],
    context_cues=PersonaWarmContext(
        what_to_listen_for=[
            "Court reporter shortage severity",
            "Recording coverage percentage",
            "State mandate compliance status",
            "Procurement vehicle preferences",
        ],
        buying_signals=[
            "We can't find court reporters",
            "Our backlog is X months for transcripts",
            "We're renovating/building a new courthouse",
            "We received an ADA complaint",
            "Open Meeting Law audit coming up",
        ],
        red_flags=[
            "State doesn't permit electronic recording (check first)",
            "Locked into JAVS contract",
            "No budget allocated for court tech",
        ],
    ),
)


# ============================================================================
# Combined Collection
# ============================================================================

PERSONA_WARM_SCRIPTS: list[PersonaWarmScript] = [
    AV_DIRECTOR_WARM_SCRIPT,
    LD_DIRECTOR_WARM_SCRIPT,
    TECHNICAL_DIRECTOR_WARM_SCRIPT,
    SIMULATION_DIRECTOR_WARM_SCRIPT,
    COURT_ADMINISTRATOR_WARM_SCRIPT,
]


# ============================================================================
# Helper Functions
# ============================================================================


def get_persona_warm_script(persona_type: PersonaType) -> PersonaWarmScript | None:
    """Get warm script for a specific persona type.

    Args:
        persona_type: The persona to look up

    Returns:
        PersonaWarmScript if found, None if persona doesn't have warm scripts
    """
    for script in PERSONA_WARM_SCRIPTS:
        if script.persona_type == persona_type:
            return script
    return None


def get_warm_script_for_persona_trigger(
    persona_type: PersonaType,
    trigger_type: TriggerType,
) -> PersonaTriggerVariation | None:
    """Get the specific trigger variation for a persona + trigger combination.

    This is the primary lookup for warm calls - given who they are (persona)
    and what they did (trigger), get the exact script to use.

    Args:
        persona_type: Who they are (e.g., AV_DIRECTOR)
        trigger_type: What they did (e.g., CONTENT_DOWNLOAD)

    Returns:
        PersonaTriggerVariation if found, None otherwise
    """
    script = get_persona_warm_script(persona_type)
    if script is None:
        return None

    for variation in script.trigger_variations:
        if variation.trigger_type == trigger_type:
            return variation
    return None
