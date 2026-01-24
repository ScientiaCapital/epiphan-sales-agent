"""Persona seed data from Epiphan BDR Playbook.

8 comprehensive buyer personas with discovery questions, objections, and buying signals.
"""

from app.data.schemas import (
    PersonaProfile,
    PainPoint,
    ObjectionResponse,
    BuyingSignals,
    Vertical,
)

PERSONAS: list[PersonaProfile] = [
    PersonaProfile(
        id="av_director",
        title="AV Director",
        title_variations=[
            "Director of AV Services",
            "Classroom Technology Manager",
            "Director of Learning Spaces",
            "AV Manager",
        ],
        reports_to="CIO, VP of IT, VP of Facilities",
        team_size="3-15 people",
        budget_authority="$200K - $2M annually",
        verticals=[Vertical.HIGHER_ED, Vertical.CORPORATE, Vertical.GOVERNMENT, Vertical.LIVE_EVENTS],
        day_to_day=[
            "Managing 50-500+ rooms/spaces with small team",
            "Responding to equipment failure tickets",
            "Planning refresh cycles and construction projects",
            "Evaluating new technology purchases",
            "Training staff and end users",
        ],
        kpis=[
            "System uptime / reliability",
            "Support ticket volume and resolution time",
            "Project deployment timeline",
            "Budget management",
            "End-user satisfaction scores",
        ],
        pain_points=[
            PainPoint(
                point="Equipment failures during critical events",
                emotional_impact="Anxiety, embarrassment",
                solution="Hardware reliability - no PC crashes",
            ),
            PainPoint(
                point="Can't troubleshoot remotely",
                emotional_impact="Frustration, wasted travel",
                solution="Fleet management dashboard",
            ),
            PainPoint(
                point="Understaffed for room count",
                emotional_impact="Overwhelm, burnout",
                solution="Remote management reduces on-site needs",
            ),
            PainPoint(
                point="Legacy equipment aging out",
                emotional_impact="Planning stress",
                solution="Modern, supportable platform",
            ),
            PainPoint(
                point="End users complaining",
                emotional_impact="Pressure from above",
                solution="Reliability = fewer complaints",
            ),
        ],
        hot_buttons=[
            "Manage 200+ rooms from one dashboard",
            "Remote firmware updates and troubleshooting",
            "Self-healing recording - auto-restart on failure",
            "NC State manages 300+ with minimal staff",
            "No recurring fees - ever",
            "3-year warranty with advance replacement",
        ],
        discovery_questions=[
            "How many rooms/spaces do you currently manage?",
            "How many people on your team handle AV support?",
            "What's your biggest reliability pain point right now?",
            "Can you troubleshoot remotely, or do you have to be on-site?",
            "When's your next major refresh or construction project?",
            "What happens when equipment fails during a critical event?",
        ],
        objections=[
            ObjectionResponse(
                objection="We're standardized on [competitor]",
                response="Pearl integrates with Crestron/Extron control systems. It adds capability, doesn't replace your ecosystem.",
            ),
            ObjectionResponse(
                objection="Too expensive upfront",
                response="Compare 5-year TCO: no recurring fees vs. software subscriptions. Plus reduced support ticket volume.",
            ),
            ObjectionResponse(
                objection="Current system works fine",
                response="How much time do you spend on break-fix? Pearl's reliability frees up time for strategic projects.",
            ),
            ObjectionResponse(
                objection="We don't have time to evaluate",
                response="15-minute demo shows the fleet management dashboard. See if it solves your remote management pain.",
            ),
        ],
        buying_signals=BuyingSignals(
            high=[
                "We have a construction project starting...",
                "I can't keep managing this many rooms with this team size",
                "We had a major failure during [important event]",
            ],
            medium=[
                "What's the support like?",
                "How does it integrate with our control system?",
                "Can I see the management dashboard?",
            ],
        ),
    ),
    PersonaProfile(
        id="ld_director",
        title="L&D Director",
        title_variations=[
            "VP of Talent Development",
            "Chief Learning Officer",
            "Director of Learning & Development",
            "Training Director",
        ],
        reports_to="CHRO, VP of HR, COO",
        team_size="5-50 people",
        budget_authority="$500K - $5M+ annually",
        verticals=[Vertical.CORPORATE, Vertical.INDUSTRIAL],
        day_to_day=[
            "Designing training programs and curricula",
            "Managing content creation workflows",
            "Measuring training effectiveness and ROI",
            "Responding to business unit training requests",
            "Managing LMS and training technology stack",
        ],
        kpis=[
            "Training completion rates",
            "Time to competency for new hires",
            "Cost per learner",
            "Training ROI / business impact",
            "Content production velocity",
        ],
        pain_points=[
            PainPoint(
                point="Can't scale content creation",
                emotional_impact="Frustration, bottleneck",
                solution="Self-service capture = more content",
            ),
            PainPoint(
                point="High production costs",
                emotional_impact="Budget pressure",
                solution="No ongoing production team needed",
            ),
            PainPoint(
                point="Inconsistent quality across locations",
                emotional_impact="Brand/quality concerns",
                solution="Standardized hardware = consistent output",
            ),
            PainPoint(
                point="SME time is expensive/limited",
                emotional_impact="Dependency, scheduling",
                solution="Record once, deploy forever",
            ),
            PainPoint(
                point="Travel costs for training",
                emotional_impact="Budget drain",
                solution="Video enables remote delivery",
            ),
        ],
        hot_buttons=[
            "218% higher revenue per employee with video training (Brandon Hall)",
            "Record SME once, train 1,000 employees",
            "Self-service capture - no production team required",
            "OpenAI uses Pearl as the workhorse of their streams",
            "40% reduction in training time with video",
            "Consistent quality across all locations",
        ],
        discovery_questions=[
            "How are you creating training content today?",
            "How much SME time do you spend on training delivery?",
            "What's your cost per learner, and how are you trying to reduce it?",
            "Are you delivering consistent training across all locations?",
            "What happens when a key expert leaves or retires?",
            "How long does it take to create a new training module?",
        ],
        objections=[
            ObjectionResponse(
                objection="We outsource video production",
                response="Calculate annual contract vs. one-time hardware. Most see ROI in the first year.",
            ),
            ObjectionResponse(
                objection="Our LMS handles this",
                response="Your LMS delivers content - Pearl creates it. They're complementary.",
            ),
            ObjectionResponse(
                objection="Quality doesn't matter for internal training",
                response="Research shows production quality impacts learning retention. Plus it reflects your brand.",
            ),
            ObjectionResponse(
                objection="SMEs don't have time to record",
                response="That's the point - record once, deploy forever. One day creates content for years.",
            ),
        ],
        buying_signals=BuyingSignals(
            high=[
                "We're trying to scale our training capacity",
                "Our production backlog is [X] months",
                "Key experts are retiring and we're losing knowledge",
                "We need to reduce training travel costs",
            ],
            medium=[
                "What's the learning curve for creating content?",
                "How does this integrate with [LMS]?",
                "Can you show me what the output looks like?",
            ],
        ),
    ),
    PersonaProfile(
        id="technical_director",
        title="Technical Director",
        title_variations=[
            "Technical Director",
            "Production Director",
            "Media Director",
            "Broadcast Engineer",
        ],
        reports_to="AV Manager, Executive Pastor, Production Manager",
        team_size="Mix of staff + volunteers",
        budget_authority="$20K - $200K (recommends, may not approve)",
        verticals=[Vertical.HOUSE_OF_WORSHIP, Vertical.LIVE_EVENTS, Vertical.CORPORATE],
        day_to_day=[
            "Running live productions (services, events, broadcasts)",
            "Managing volunteer teams (HoW especially)",
            "Maintaining equipment and troubleshooting",
            "Training operators on technical workflows",
            "Balancing quality with operational simplicity",
        ],
        kpis=[
            "Production quality and consistency",
            "Zero failures during live events",
            "Volunteer retention and training success",
            "Equipment uptime and maintenance",
            "Budget adherence",
        ],
        pain_points=[
            PainPoint(
                point="Equipment failure during live event",
                emotional_impact="Panic, embarrassment",
                solution="Hardware reliability - no crashes",
            ),
            PainPoint(
                point="Volunteer turnover",
                emotional_impact="Constant retraining",
                solution="Touchscreen = 5-minute training",
            ),
            PainPoint(
                point="Complex setups",
                emotional_impact="Stress before events",
                solution="All-in-one simplicity",
            ),
            PainPoint(
                point="Can't fail on Sunday",
                emotional_impact="Weekly anxiety",
                solution="Proven reliability",
            ),
            PainPoint(
                point="Inconsistent output quality",
                emotional_impact="Frustration",
                solution="Standardized hardware",
            ),
        ],
        hot_buttons=[
            "Hardware doesn't crash like PCs",
            "5-minute volunteer training",
            "Touchscreen operation",
            "Auto-start at scheduled times",
            "Can't fail on Sunday morning",
            "Multi-source recording with one box",
            "NDI workflow support",
        ],
        discovery_questions=[
            "What's your current production setup?",
            "Who operates during events - staff or volunteers?",
            "What's your biggest Sunday morning (or event day) worry?",
            "Have you had equipment failures during a service or event?",
            "How long does it take to train a new volunteer?",
            "What would make your workflow simpler?",
        ],
        objections=[
            ObjectionResponse(
                objection="Blackmagic is cheaper",
                response="ATEM needs a PC for recording. That PC can crash. Pearl is standalone and reliable.",
            ),
            ObjectionResponse(
                objection="We use vMix",
                response="vMix is great until Windows updates mid-service. Hardware doesn't have that problem.",
            ),
            ObjectionResponse(
                objection="Our volunteers can handle complex gear",
                response="How often do volunteers turn over? Simple = less retraining.",
            ),
            ObjectionResponse(
                objection="Current setup works",
                response="When it works. What's the cost when it doesn't?",
            ),
        ],
        buying_signals=BuyingSignals(
            high=[
                "We had a [failure] during [important event]",
                "I can't keep training new volunteers",
                "We're building/renovating our [space]",
                "We need something anyone can operate",
            ],
            medium=[
                "How does NDI work with this?",
                "Can I see the touchscreen interface?",
                "What's the failover capability?",
            ],
        ),
    ),
    PersonaProfile(
        id="simulation_director",
        title="Simulation Center Director",
        title_variations=[
            "Director of Simulation",
            "Simulation Center Manager",
            "Director of Clinical Simulation",
        ],
        reports_to="Dean of Medicine, CMO, VP of Academic Affairs",
        team_size="5-20 staff",
        budget_authority="$100K - $1M annually",
        verticals=[Vertical.HEALTHCARE],
        day_to_day=[
            "Running simulation sessions for students/residents",
            "Facilitating debriefing with video playback",
            "Maintaining accreditation standards (SSH, LCME)",
            "Managing simulation equipment and manikins",
            "Tracking learner competency and assessments",
        ],
        kpis=[
            "Accreditation compliance (SSH, LCME)",
            "Session throughput and utilization",
            "Debriefing effectiveness",
            "Learner competency metrics",
            "Technology reliability during sessions",
        ],
        pain_points=[
            PainPoint(
                point="Debriefing without video is less effective",
                emotional_impact="Frustration, suboptimal learning",
                solution="Multi-source video capture",
            ),
            PainPoint(
                point="HIPAA compliance with cloud recording",
                emotional_impact="Legal/compliance anxiety",
                solution="Local recording - PHI never leaves network",
            ),
            PainPoint(
                point="Multi-angle capture synchronization",
                emotional_impact="Technical complexity",
                solution="Single device, multiple inputs",
            ),
            PainPoint(
                point="SSH/LCME accreditation prep",
                emotional_impact="Stress, documentation burden",
                solution="Reliable capture = evidence",
            ),
            PainPoint(
                point="SimCapture integration issues",
                emotional_impact="Technical frustration",
                solution="Native integration",
            ),
        ],
        hot_buttons=[
            "Local recording - HIPAA compliant, no PHI in cloud",
            "SSH accreditation support",
            "Native SimCapture/LearningSpace integration",
            "Multi-source synchronized capture",
            "Easy retrieval for debriefing",
            "One device for entire sim room",
        ],
        discovery_questions=[
            "How are you capturing simulation sessions today?",
            "Do you use SimCapture or LearningSpace?",
            "When's your next SSH or LCME accreditation visit?",
            "Are you concerned about HIPAA compliance with video storage?",
            "How many simulation rooms do you need to equip?",
            "What's your biggest challenge with debriefing?",
        ],
        objections=[
            ObjectionResponse(
                objection="We use SimCapture already",
                response="Perfect - Pearl feeds into SimCapture as the hardware capture layer. Same workflow, better reliability.",
            ),
            ObjectionResponse(
                objection="B-Line Medical is simulation-specific",
                response="Pearl is more versatile and integrates with SimCapture. Same capability, more flexibility.",
            ),
            ObjectionResponse(
                objection="HIPAA concerns with video",
                response="Pearl records locally - video never touches cloud unless you choose. You control the data.",
            ),
            ObjectionResponse(
                objection="Budget is limited",
                response="Compare to OR-specific systems at $50K+. Pearl-2 at $7,999 is 90% less.",
            ),
        ],
        buying_signals=BuyingSignals(
            high=[
                "Our SSH visit is coming up in [X] months",
                "We're expanding/building a new simulation center",
                "We had recording failures during [important session]",
                "We're concerned about [HIPAA/compliance]",
            ],
            medium=[
                "How does this integrate with SimCapture?",
                "Can you show me the debriefing playback?",
                "What's the installation process?",
            ],
        ),
    ),
    PersonaProfile(
        id="court_administrator",
        title="Court Administrator",
        title_variations=[
            "Court Administrator",
            "Court Executive Officer",
            "Clerk of Court",
            "Trial Court Administrator",
            "Director of Court Operations",
        ],
        reports_to="Presiding Judge, Chief Justice, County Board",
        team_size="10-200 staff (varies by court size/jurisdiction)",
        budget_authority="$100K - $5M annually",
        verticals=[Vertical.GOVERNMENT, Vertical.LEGAL],
        day_to_day=[
            "Managing court operations and case flow",
            "Ensuring compliance with state mandates (recording requirements)",
            "Handling budget and resource allocation",
            "Overseeing technology and modernization",
            "Responding to public records requests (FOIA/Sunshine Law)",
        ],
        kpis=[
            "Case clearance rate / backlog reduction",
            "Compliance with state recording mandates",
            "Budget management",
            "Public access and transparency (Open Meeting Law)",
            "Technology modernization progress",
            "ADA accessibility compliance",
        ],
        pain_points=[
            PainPoint(
                point="Court reporter shortage (critical nationwide)",
                emotional_impact="Operational crisis",
                solution="Electronic recording as supplement",
            ),
            PainPoint(
                point="Case backlog due to transcript delays",
                emotional_impact="Stress, public pressure",
                solution="Faster recording = faster transcripts",
            ),
            PainPoint(
                point="Open Meeting Law / Sunshine Law compliance",
                emotional_impact="Legal risk",
                solution="Reliable public meeting recording",
            ),
            PainPoint(
                point="ADA accessibility requirements (April 2026 deadline)",
                emotional_impact="Compliance anxiety",
                solution="Captioning capability",
            ),
            PainPoint(
                point="Transcript costs ($3-5/page)",
                emotional_impact="Budget pressure",
                solution="Video reduces transcription needs",
            ),
        ],
        hot_buttons=[
            "Address court reporter shortage",
            "33 states permit electronic recording in courts",
            "1.78M hearings go without verbatim record annually",
            "Reduce transcript turnaround time",
            "ADA-compliant captioning capability",
            "CJIS-compliant security",
            "Available through TIPS and Sourcewell cooperative purchasing",
        ],
        discovery_questions=[
            "How are you handling the court reporter shortage?",
            "What percentage of hearings have verbatim recording today?",
            "What's your transcript turnaround time?",
            "Are you meeting state recording requirements?",
            "Have you received ADA complaints about hearing accessibility?",
            "What's your current courtroom technology setup?",
            "Do you use Tyler Odyssey or Journal Technologies for case management?",
        ],
        objections=[
            ObjectionResponse(
                objection="Judges prefer court reporters",
                response="Electronic recording supplements, not replaces. It's for the 1.78M hearings without any record today.",
            ),
            ObjectionResponse(
                objection="Our state doesn't allow it",
                response="33 of 35 states now permit electronic recording. Let me check your specific state requirements.",
            ),
            ObjectionResponse(
                objection="Procurement is complex",
                response="We're on TIPS and Sourcewell for cooperative purchasing, plus GSA Schedule for federal.",
            ),
            ObjectionResponse(
                objection="JAVS is the court standard",
                response="JAVS is excellent but court-specific. Pearl is equally capable at lower cost, plus works for other government applications.",
            ),
        ],
        buying_signals=BuyingSignals(
            high=[
                "We can't find court reporters",
                "Our backlog is [X] months for transcripts",
                "We're renovating/building a new courthouse",
                "We received an ADA complaint",
                "Open Meeting Law audit coming up",
            ],
            medium=[
                "What's the transcript workflow?",
                "How does it integrate with Tyler Odyssey?",
                "What procurement vehicles are available?",
            ],
        ),
    ),
    PersonaProfile(
        id="corp_comms_director",
        title="Corp Comms Director",
        title_variations=[
            "VP of Corporate Communications",
            "Head of Internal Communications",
            "Director of Executive Communications",
            "VP of Internal Comms",
        ],
        reports_to="CEO or CMO",
        team_size="3-15 people (comms team, often with contractors)",
        budget_authority="$100K - $500K annually for comms/AV technology",
        verticals=[Vertical.CORPORATE],
        day_to_day=[
            "Planning and executing executive town halls and quarterly addresses",
            "Managing internal broadcast studios or event production",
            "Coordinating with IT/AV for meeting room setup",
            "Ensuring brand consistency in all communications",
            "Managing crisis communication scenarios",
            "Training executives on messaging and delivery",
        ],
        kpis=[
            "Employee engagement scores post-broadcast",
            "Message consistency across communications",
            "Technical reliability (zero failures during CEO events)",
            "Production quality and brand alignment",
            "Executive satisfaction with communication vehicles",
        ],
        pain_points=[
            PainPoint(
                point="Zero tolerance for failures during CEO events",
                emotional_impact="Anxiety, career risk",
                solution="Hardware doesn't crash like PCs",
            ),
            PainPoint(
                point="Executive visibility = high stakes",
                emotional_impact="Pressure from C-suite",
                solution="Professional-grade reliability",
            ),
            PainPoint(
                point="Inconsistent quality across offices",
                emotional_impact="Brand risk",
                solution="Standardized hardware = consistency",
            ),
            PainPoint(
                point="Limited internal production team",
                emotional_impact="Resource constraint",
                solution="Self-service capture capability",
            ),
            PainPoint(
                point="Zoom/Teams quality limitations (720p)",
                emotional_impact="Professionalism concerns",
                solution="Broadcast quality for leadership",
            ),
        ],
        hot_buttons=[
            "Broadcast quality for CEO's quarterly address",
            "Can't have technical failure during board communication",
            "Freeman (major event producer) uses Pearl",
            "OpenAI calls Pearl 'the workhorse of our streams'",
            "Zero cloud dependency = zero security risk",
            "Reduced reliance on external production teams",
            "Consistent quality across all office locations",
        ],
        discovery_questions=[
            "How are you currently handling executive town halls and quarterly addresses?",
            "What's your current setup for the CEO's internal communications?",
            "Have you had any technical failures during important executive broadcasts?",
            "Who manages the production - internal team or outsourced?",
            "How many office locations are part of your internal broadcast strategy?",
            "What's the biggest risk if technical failure occurs during executive communication?",
            "Are you streaming internally to remote workers or recording for playback?",
        ],
        objections=[
            ObjectionResponse(
                objection="We use Zoom/Teams",
                response="Zoom caps at 720p and any mobile participant degrades the entire broadcast. For the CEO, you need broadcast quality.",
            ),
            ObjectionResponse(
                objection="External production company handles this",
                response="Pearl lets you bring that in-house. One device, no production overhead. The CEO doesn't need a film crew.",
            ),
            ObjectionResponse(
                objection="Our current system works",
                response="Until it doesn't - during the CEO's quarterly address. What's the cost of that failure? Pearl is insurance.",
            ),
            ObjectionResponse(
                objection="This is overkill for internal comms",
                response="Your internal communications shape employee engagement and retention. It deserves broadcast quality.",
            ),
        ],
        buying_signals=BuyingSignals(
            high=[
                "We had a technical failure during [executive event]",
                "We're scaling our town hall program for hybrid workforce",
                "We're building a new broadcast studio",
                "External production costs are too high",
            ],
            medium=[
                "How do you handle Zoom quality issues?",
                "Can we stream to multiple office locations simultaneously?",
                "What's the setup for hybrid meetings?",
            ],
        ),
    ),
    PersonaProfile(
        id="ehs_manager",
        title="EHS Manager",
        title_variations=[
            "EHS Director (Environment, Health & Safety)",
            "Safety Manager",
            "Director of Safety",
            "Plant Safety Manager",
            "VP of EHS",
        ],
        reports_to="VP of Operations, COO, VP of Manufacturing",
        team_size="2-10 people (varies by plant size)",
        budget_authority="$50K - $500K annually (separate EHS budget from L&D)",
        verticals=[Vertical.INDUSTRIAL],
        day_to_day=[
            "Managing OSHA compliance",
            "Conducting incident investigations and root cause analysis",
            "Delivering safety training and near-miss reviews",
            "Preparing for OSHA audits and inspections",
            "Maintaining safety documentation and records",
            "Managing safety committees and plant floor teams",
        ],
        kpis=[
            "OSHA compliance metrics",
            "TRIR (Total Recordable Incident Rate)",
            "Near-miss reporting and investigation closure",
            "Safety training completion documentation",
            "Audit readiness score",
        ],
        pain_points=[
            PainPoint(
                point="Proving training was actually delivered",
                emotional_impact="Compliance anxiety",
                solution="Video documentation as proof",
            ),
            PainPoint(
                point="Incident investigations without video evidence",
                emotional_impact="Legal liability",
                solution="Multi-angle video capture of incidents",
            ),
            PainPoint(
                point="OSHA audit readiness documentation gaps",
                emotional_impact="Stress, regulatory risk",
                solution="Video evidence of safety training",
            ),
            PainPoint(
                point="Inconsistent safety communication across shifts",
                emotional_impact="Culture/compliance gap",
                solution="Standardized safety training videos",
            ),
            PainPoint(
                point="Plant floor documentation is manual/slow",
                emotional_impact="Time-consuming",
                solution="Mobile capture for incident scenes",
            ),
        ],
        hot_buttons=[
            "Video proof of safety training delivery for OSHA",
            "OSHA-compliant incident documentation",
            "Mobile capture for plant floor investigations",
            "Reduces liability in incident review",
            "Audit-ready documentation package",
            "Training consistency across all shifts",
            "Incident playback for root cause analysis",
            "One OSHA violation can cost $100K-$500K+",
        ],
        discovery_questions=[
            "How do you currently document safety training compliance?",
            "Have you had OSHA violations related to documentation gaps?",
            "When an incident occurs, how do you document and investigate it?",
            "How often do you face OSHA audits or inspections?",
            "What's your current incident reporting process?",
            "How do you ensure safety message consistency across all shifts?",
            "What's your TRIR and how are you improving it?",
        ],
        objections=[
            ObjectionResponse(
                objection="We use incident reporting software",
                response="That captures the report. Pearl captures the evidence. They're complementary.",
            ),
            ObjectionResponse(
                objection="Video is too complex for plant floor",
                response="Pearl is designed for simplicity. Plant supervisors can use it - no tech training needed.",
            ),
            ObjectionResponse(
                objection="Our incidents are rare",
                response="That's why you need documentation ready - OSHA doesn't care that they're rare. When they happen, you need the evidence.",
            ),
            ObjectionResponse(
                objection="Too expensive for safety budget",
                response="What's the cost of one OSHA violation? Or one incident investigation that goes wrong? Pearl pays for itself.",
            ),
        ],
        buying_signals=BuyingSignals(
            high=[
                "We had an OSHA violation or citation",
                "We're preparing for an OSHA audit",
                "We had a serious incident that needs documentation",
                "Leadership is asking us to improve documentation",
            ],
            medium=[
                "How do you document training for compliance?",
                "Can you show incident investigation examples?",
                "What's the setup for plant floor recording?",
            ],
        ),
    ),
    PersonaProfile(
        id="law_firm_it",
        title="Law Firm IT Director",
        title_variations=[
            "Director of Information Technology (Law Firm)",
            "Legal Tech Manager",
            "Director of Legal Operations",
            "IT Operations Manager (Legal)",
        ],
        reports_to="Managing Partner, COO, Director of Administration",
        team_size="3-20 IT staff (varies by firm size)",
        budget_authority="$50K - $500K (manages technology budget)",
        verticals=[Vertical.LEGAL],
        day_to_day=[
            "Managing deposition room technology and setup",
            "Ensuring video quality for attorney review and trial prep",
            "Handling confidential deposition recording and archiving",
            "Managing multiple office locations' recording capabilities",
            "Maintaining chain of custody for recorded evidence",
            "Integrating with case management and deposition software",
        ],
        kpis=[
            "Deposition recording reliability (zero failures)",
            "Video quality for trial preparation",
            "System uptime for critical deposition events",
            "Confidentiality/security compliance",
            "Attorney satisfaction with recording capabilities",
        ],
        pain_points=[
            PainPoint(
                point="Multi-angle deposition capture complexity",
                emotional_impact="Technical stress",
                solution="Synchronized multi-source recording",
            ),
            PainPoint(
                point="Confidential case footage in cloud = discovery risk",
                emotional_impact="Compliance/liability risk",
                solution="Local recording - zero cloud exposure",
            ),
            PainPoint(
                point="Chain of custody integrity for evidence",
                emotional_impact="Legal liability",
                solution="Single device, tamper-evident recording",
            ),
            PainPoint(
                point="Video sync issues for credibility review",
                emotional_impact="Professional risk",
                solution="Perfect synchronization between angles",
            ),
            PainPoint(
                point="Multi-location coordination across offices",
                emotional_impact="Operational headache",
                solution="Remote fleet management",
            ),
        ],
        hot_buttons=[
            "Local recording - confidential case materials never touch cloud",
            "No cloud = no discovery risk for sensitive IP/product cases",
            "Perfect synchronization for multi-angle deposition review",
            "Chain of custody ready - single device, single recording",
            "No subscription fees - fixed hardware cost",
            "Reliable backup for trial prep video review",
            "Mobile deposition capture for remote locations",
        ],
        discovery_questions=[
            "How are you capturing depositions today?",
            "Do you have multiple deposition rooms across offices?",
            "Are you recording locally or using cloud storage?",
            "How do you handle multi-angle capture for credibility assessment?",
            "What deposition software do you use (Livenote, Veritext, etc.)?",
            "Have you had issues with video quality or synchronization?",
            "What's your workflow from recording to attorney review?",
        ],
        objections=[
            ObjectionResponse(
                objection="We use our deposition service provider's setup",
                response="That's fine for deposition transcript. Pearl adds the multi-angle video backup for trial prep and credibility challenges.",
            ),
            ObjectionResponse(
                objection="Cloud recording is standard",
                response="For confidential case materials? No - local recording keeps your case materials on your servers, zero cloud dependency.",
            ),
            ObjectionResponse(
                objection="Current setup works fine",
                response="Until you need multi-angle video for credibility assessment or trial prep. Pearl gives you that option.",
            ),
            ObjectionResponse(
                objection="Too expensive for backup video",
                response="Multi-angle video credibility assessment is becoming standard in high-stakes litigation. It's not backup - it's required.",
            ),
        ],
        buying_signals=BuyingSignals(
            high=[
                "We're building/upgrading deposition rooms",
                "We need multi-angle video capability for trials",
                "We had issues with video quality affecting trial prep",
                "We're concerned about cloud storage for confidential cases",
            ],
            medium=[
                "How do you sync multiple camera angles?",
                "Can you show deposition room setup?",
                "What's the workflow post-recording?",
            ],
        ),
    ),
]


def get_persona_by_id(persona_id: str) -> PersonaProfile | None:
    """Lookup persona by ID."""
    for persona in PERSONAS:
        if persona.id == persona_id:
            return persona
    return None


def get_personas_by_vertical(vertical: Vertical) -> list[PersonaProfile]:
    """Get all personas relevant to a vertical."""
    return [p for p in PERSONAS if vertical in p.verticals]
