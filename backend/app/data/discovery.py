"""SPIN Discovery framework questions and BANT+ qualification from BDR Playbook."""

from app.data.schemas import (
    DiscoveryQuestion,
    QualificationCriterion,
    SPINStage,
    QualificationRating,
)

DISCOVERY_QUESTIONS: list[DiscoveryQuestion] = [
    # ============================================================================
    # SITUATION Questions (Universal)
    # ============================================================================
    DiscoveryQuestion(
        id="sit_001",
        stage=SPINStage.SITUATION,
        vertical="universal",
        question="Walk me through how video recording works in your organization today.",
        what_you_learn="Current state, technology stack, workflow complexity",
    ),
    DiscoveryQuestion(
        id="sit_002",
        stage=SPINStage.SITUATION,
        vertical="universal",
        question="What equipment are you using right now?",
        what_you_learn="Competitive landscape, technology age, potential replacement cycle",
    ),
    DiscoveryQuestion(
        id="sit_003",
        stage=SPINStage.SITUATION,
        vertical="universal",
        question="Who's responsible for managing this day-to-day?",
        what_you_learn="Decision-maker vs. user, team structure, support burden",
    ),
    DiscoveryQuestion(
        id="sit_004",
        stage=SPINStage.SITUATION,
        vertical="universal",
        question="How many locations or rooms are you recording in?",
        what_you_learn="Scale of opportunity, fleet management need",
    ),
    DiscoveryQuestion(
        id="sit_005",
        stage=SPINStage.SITUATION,
        vertical="universal",
        question="What platforms do you stream to or integrate with?",
        what_you_learn="LMS ecosystem, integration requirements",
    ),
    # Higher Ed Specific
    DiscoveryQuestion(
        id="sit_hed_001",
        stage=SPINStage.SITUATION,
        vertical="higher_ed",
        question="How many classrooms are equipped for recording today?",
        what_you_learn="Scale, coverage gaps, expansion opportunity",
    ),
    DiscoveryQuestion(
        id="sit_hed_002",
        stage=SPINStage.SITUATION,
        vertical="higher_ed",
        question="Which LMS platform do you use - Panopto, Kaltura, YuJa?",
        what_you_learn="Integration requirements, ecosystem fit",
    ),
    DiscoveryQuestion(
        id="sit_hed_003",
        stage=SPINStage.SITUATION,
        vertical="higher_ed",
        question="How many people on your team support classroom technology?",
        what_you_learn="Staffing constraints, remote management need",
    ),
    # Corporate Specific
    DiscoveryQuestion(
        id="sit_corp_001",
        stage=SPINStage.SITUATION,
        vertical="corporate",
        question="Walk me through your content creation process today.",
        what_you_learn="Workflow, bottlenecks, external dependencies",
    ),
    DiscoveryQuestion(
        id="sit_corp_002",
        stage=SPINStage.SITUATION,
        vertical="corporate",
        question="How do you handle executive town halls and communications?",
        what_you_learn="Quality expectations, stakes, current solution",
    ),
    # Healthcare Specific
    DiscoveryQuestion(
        id="sit_health_001",
        stage=SPINStage.SITUATION,
        vertical="healthcare",
        question="How are you capturing simulation sessions today?",
        what_you_learn="Current solution, pain points, compliance approach",
    ),
    DiscoveryQuestion(
        id="sit_health_002",
        stage=SPINStage.SITUATION,
        vertical="healthcare",
        question="Do you use SimCapture or LearningSpace?",
        what_you_learn="Integration requirements, existing workflow",
    ),
    # ============================================================================
    # PROBLEM Questions (Universal + Vertical)
    # ============================================================================
    DiscoveryQuestion(
        id="prob_001",
        stage=SPINStage.PROBLEM,
        vertical="universal",
        question="What's your biggest headache with that?",
        what_you_learn="Primary pain point - listen, then probe deeper",
    ),
    DiscoveryQuestion(
        id="prob_002",
        stage=SPINStage.PROBLEM,
        vertical="universal",
        question="What happens when the system fails?",
        what_you_learn="Consequences, stakes, urgency",
    ),
    DiscoveryQuestion(
        id="prob_003",
        stage=SPINStage.PROBLEM,
        vertical="universal",
        question="How much time does your team spend on troubleshooting?",
        what_you_learn="Support burden, hidden costs",
    ),
    DiscoveryQuestion(
        id="prob_004",
        stage=SPINStage.PROBLEM,
        vertical="universal",
        question="What do you hear from users about the current system?",
        what_you_learn="End-user satisfaction, complaints, adoption issues",
    ),
    DiscoveryQuestion(
        id="prob_005",
        stage=SPINStage.PROBLEM,
        vertical="universal",
        question="Have you had any incidents that caused problems recently?",
        what_you_learn="Recent pain, urgency, specific examples",
    ),
    DiscoveryQuestion(
        id="prob_006",
        stage=SPINStage.PROBLEM,
        vertical="universal",
        question="What would you change if you could start fresh?",
        what_you_learn="Ideal state, priorities, frustrations",
    ),
    # Higher Ed Problems
    DiscoveryQuestion(
        id="prob_hed_001",
        stage=SPINStage.PROBLEM,
        vertical="higher_ed",
        question="How do you know when a recording failed?",
        what_you_learn="Monitoring gaps, reactive vs. proactive",
    ),
    DiscoveryQuestion(
        id="prob_hed_002",
        stage=SPINStage.PROBLEM,
        vertical="higher_ed",
        question="What's the burden of on-site troubleshooting?",
        what_you_learn="Remote management need, staffing strain",
    ),
    # Corporate Problems
    DiscoveryQuestion(
        id="prob_corp_001",
        stage=SPINStage.PROBLEM,
        vertical="corporate",
        question="What feedback do you get from leadership about quality?",
        what_you_learn="Executive expectations, quality gaps",
    ),
    DiscoveryQuestion(
        id="prob_corp_002",
        stage=SPINStage.PROBLEM,
        vertical="corporate",
        question="What's your content production backlog?",
        what_you_learn="Capacity constraints, scaling challenges",
    ),
    # Healthcare Problems
    DiscoveryQuestion(
        id="prob_health_001",
        stage=SPINStage.PROBLEM,
        vertical="healthcare",
        question="What happens when recording fails during a simulation?",
        what_you_learn="Consequences for learning, frustration level",
    ),
    DiscoveryQuestion(
        id="prob_health_002",
        stage=SPINStage.PROBLEM,
        vertical="healthcare",
        question="How confident are you in HIPAA compliance with your current approach?",
        what_you_learn="Compliance anxiety, cloud concerns",
    ),
    # ============================================================================
    # IMPLICATION Questions
    # ============================================================================
    DiscoveryQuestion(
        id="impl_001",
        stage=SPINStage.IMPLICATION,
        vertical="universal",
        question="What does that cost you when it happens?",
        what_you_learn="Financial impact, business consequences",
    ),
    DiscoveryQuestion(
        id="impl_002",
        stage=SPINStage.IMPLICATION,
        vertical="universal",
        question="How does that affect your team?",
        what_you_learn="Human impact, morale, burnout",
    ),
    DiscoveryQuestion(
        id="impl_003",
        stage=SPINStage.IMPLICATION,
        vertical="universal",
        question="What does leadership say about that?",
        what_you_learn="Visibility, pressure, executive awareness",
    ),
    DiscoveryQuestion(
        id="impl_004",
        stage=SPINStage.IMPLICATION,
        vertical="universal",
        question="How does that compare to what competitors/peers are doing?",
        what_you_learn="Competitive pressure, benchmarking",
    ),
    DiscoveryQuestion(
        id="impl_005",
        stage=SPINStage.IMPLICATION,
        vertical="universal",
        question="What happens if this continues for another year?",
        what_you_learn="Urgency, trajectory, risk tolerance",
    ),
    # Higher Ed Implications
    DiscoveryQuestion(
        id="impl_hed_001",
        stage=SPINStage.IMPLICATION,
        vertical="higher_ed",
        question="How does unreliability affect faculty adoption?",
        what_you_learn="User resistance, adoption challenges",
    ),
    DiscoveryQuestion(
        id="impl_hed_002",
        stage=SPINStage.IMPLICATION,
        vertical="higher_ed",
        question="What's the impact on student accessibility?",
        what_you_learn="ADA compliance, student experience",
    ),
    # Corporate Implications
    DiscoveryQuestion(
        id="impl_corp_001",
        stage=SPINStage.IMPLICATION,
        vertical="corporate",
        question="What happens if the CEO's quarterly address fails?",
        what_you_learn="Stakes, career risk, urgency",
    ),
    DiscoveryQuestion(
        id="impl_corp_002",
        stage=SPINStage.IMPLICATION,
        vertical="corporate",
        question="How does content backlog affect training rollout speed?",
        what_you_learn="Business impact, time to competency",
    ),
    # Healthcare Implications
    DiscoveryQuestion(
        id="impl_health_001",
        stage=SPINStage.IMPLICATION,
        vertical="healthcare",
        question="How does debriefing without video affect learning outcomes?",
        what_you_learn="Educational impact, quality concerns",
    ),
    DiscoveryQuestion(
        id="impl_health_002",
        stage=SPINStage.IMPLICATION,
        vertical="healthcare",
        question="What's the risk to SSH accreditation without proper documentation?",
        what_you_learn="Compliance urgency, accreditation timeline",
    ),
    # ============================================================================
    # NEED-PAYOFF Questions
    # ============================================================================
    DiscoveryQuestion(
        id="need_001",
        stage=SPINStage.NEED_PAYOFF,
        vertical="universal",
        question="If you could manage all rooms from one dashboard, how would that change things?",
        what_you_learn="Value of fleet management, time savings",
    ),
    DiscoveryQuestion(
        id="need_002",
        stage=SPINStage.NEED_PAYOFF,
        vertical="universal",
        question="What would it mean to never worry about equipment failing during a critical event?",
        what_you_learn="Value of reliability, peace of mind",
    ),
    DiscoveryQuestion(
        id="need_003",
        stage=SPINStage.NEED_PAYOFF,
        vertical="universal",
        question="If you could scale content production without adding headcount, what would that enable?",
        what_you_learn="Business value of efficiency, ROI framing",
    ),
    DiscoveryQuestion(
        id="need_004",
        stage=SPINStage.NEED_PAYOFF,
        vertical="universal",
        question="What would you do with the time you'd save?",
        what_you_learn="Strategic priorities, opportunity cost",
    ),
    DiscoveryQuestion(
        id="need_005",
        stage=SPINStage.NEED_PAYOFF,
        vertical="universal",
        question="How would that change your relationship with faculty/leadership/volunteers?",
        what_you_learn="Stakeholder value, political benefits",
    ),
    # Higher Ed Need-Payoff
    DiscoveryQuestion(
        id="need_hed_001",
        stage=SPINStage.NEED_PAYOFF,
        vertical="higher_ed",
        question="If you could troubleshoot remotely, what would that free up?",
        what_you_learn="Time savings, staffing efficiency",
    ),
    # Corporate Need-Payoff
    DiscoveryQuestion(
        id="need_corp_001",
        stage=SPINStage.NEED_PAYOFF,
        vertical="corporate",
        question="What would broadcast quality for leadership comms mean for employee engagement?",
        what_you_learn="Executive visibility value, culture impact",
    ),
    # Healthcare Need-Payoff
    DiscoveryQuestion(
        id="need_health_001",
        stage=SPINStage.NEED_PAYOFF,
        vertical="healthcare",
        question="What would 100% recording reliability mean for debriefing effectiveness?",
        what_you_learn="Educational value, learning outcomes",
    ),
]


QUALIFICATION_CRITERIA: list[QualificationCriterion] = [
    # Budget
    QualificationCriterion(
        id="bant_budget_hot",
        category="budget",
        signal="Specific budget allocation identified",
        rating=QualificationRating.HOT,
        key_question="What budget do you have allocated for this?",
    ),
    QualificationCriterion(
        id="bant_budget_warm",
        category="budget",
        signal="Budget cycle identified, amount TBD",
        rating=QualificationRating.WARM,
        key_question="When does your fiscal year start?",
    ),
    QualificationCriterion(
        id="bant_budget_cool",
        category="budget",
        signal="'Need to find budget' or 'not budgeted'",
        rating=QualificationRating.COOL,
    ),
    QualificationCriterion(
        id="bant_budget_cold",
        category="budget",
        signal="No budget, no path to budget",
        rating=QualificationRating.COLD,
    ),
    # Authority
    QualificationCriterion(
        id="bant_auth_hot",
        category="authority",
        signal="Decision-maker present on call",
        rating=QualificationRating.HOT,
        key_question="Who else needs to be involved in this decision?",
    ),
    QualificationCriterion(
        id="bant_auth_warm",
        category="authority",
        signal="Clear path to decision-maker + intro offered",
        rating=QualificationRating.WARM,
    ),
    QualificationCriterion(
        id="bant_auth_cool",
        category="authority",
        signal="Multiple approvals needed, path unclear",
        rating=QualificationRating.COOL,
    ),
    QualificationCriterion(
        id="bant_auth_cold",
        category="authority",
        signal="No clarity on decision-maker",
        rating=QualificationRating.COLD,
    ),
    # Need
    QualificationCriterion(
        id="bant_need_hot",
        category="need",
        signal="Active pain point or recent incident",
        rating=QualificationRating.HOT,
        key_question="What triggered this evaluation?",
    ),
    QualificationCriterion(
        id="bant_need_warm",
        category="need",
        signal="Problem recognized, not urgent",
        rating=QualificationRating.WARM,
    ),
    QualificationCriterion(
        id="bant_need_cool",
        category="need",
        signal="Awareness only, no active pain",
        rating=QualificationRating.COOL,
    ),
    QualificationCriterion(
        id="bant_need_cold",
        category="need",
        signal="No acknowledged need",
        rating=QualificationRating.COLD,
    ),
    # Timeline
    QualificationCriterion(
        id="bant_time_hot",
        category="timeline",
        signal="Specific deadline or event driving decision",
        rating=QualificationRating.HOT,
        key_question="What's driving the timeline?",
    ),
    QualificationCriterion(
        id="bant_time_warm",
        category="timeline",
        signal="This quarter or this year",
        rating=QualificationRating.WARM,
    ),
    QualificationCriterion(
        id="bant_time_cool",
        category="timeline",
        signal="'Eventually' or 'sometime'",
        rating=QualificationRating.COOL,
    ),
    QualificationCriterion(
        id="bant_time_cold",
        category="timeline",
        signal="No timeline, no urgency",
        rating=QualificationRating.COLD,
    ),
    # Competition
    QualificationCriterion(
        id="bant_comp_hot",
        category="competition",
        signal="No other vendors being evaluated",
        rating=QualificationRating.HOT,
        key_question="Who else are you looking at?",
    ),
    QualificationCriterion(
        id="bant_comp_warm",
        category="competition",
        signal="2-3 vendors on shortlist",
        rating=QualificationRating.WARM,
    ),
    QualificationCriterion(
        id="bant_comp_cool",
        category="competition",
        signal="Early stage, many options",
        rating=QualificationRating.COOL,
    ),
    QualificationCriterion(
        id="bant_comp_cold",
        category="competition",
        signal="Incumbent preferred, renewal likely",
        rating=QualificationRating.COLD,
    ),
]


# Qualification scoring guidance
QUALIFICATION_SCORING = [
    {"score": "4-5 Hots", "disposition": "Priority 1 - Demo within 1 week"},
    {"score": "2-3 Hots (rest Warm)", "disposition": "Priority 2 - Demo within 2 weeks"},
    {"score": "Mixed Warm/Cool", "disposition": "Priority 3 - Nurture with content"},
    {"score": "Mostly Cold", "disposition": "Priority 4 - Educational drip, revisit 90 days"},
]


# Disqualification signals
DISQUALIFY_SIGNALS = [
    {"signal": "Just researching for a paper/report", "meaning": "No purchase intent"},
    {"signal": "Can't identify any stakeholders", "meaning": "No authority path"},
    {"signal": "Our current system is perfect", "meaning": "No need acknowledged"},
    {"signal": "Refuses to discuss budget/timeline", "meaning": "Not engaged"},
    {"signal": "Send me everything you have", "meaning": "Low intent, time waster"},
    {"signal": "Company in financial distress", "meaning": "No budget possible"},
]


# Discovery close framework template
DISCOVERY_CLOSE_TEMPLATE = """
Let me make sure I understand...

[SITUATION]: You're using {current_system} for {use_case} across {scope}

[PROBLEM]: Main challenges are {challenges}

[IMPLICATION]: Costing you {costs}

[NEED]: What you need is {their_words}

Did I capture that correctly?
"""


def get_questions_by_stage(stage: SPINStage) -> list[DiscoveryQuestion]:
    """Get all questions for a SPIN stage."""
    return [q for q in DISCOVERY_QUESTIONS if q.stage == stage]


def get_questions_by_vertical(vertical: str) -> list[DiscoveryQuestion]:
    """Get questions for a specific vertical (includes universal)."""
    return [
        q for q in DISCOVERY_QUESTIONS
        if q.vertical == vertical or q.vertical == "universal"
    ]
