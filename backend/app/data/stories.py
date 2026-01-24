"""Reference customer stories and case studies from Epiphan BDR Playbook."""

from app.data.schemas import ReferenceStory, Vertical

REFERENCE_STORIES: list[ReferenceStory] = [
    ReferenceStory(
        id="nc_state",
        customer="NC State University",
        stats="300+ Pearl units, 7M+ annual views, team of 3",
        quote="We went from constant firefighting to remote fleet management.",
        quote_person="AV Director",
        quote_title="Director of Classroom Technology",
        vertical=Vertical.HIGHER_ED,
        product="Pearl Mini / Pearl-2",
        challenge="Managing 300+ lecture capture rooms with limited staff. Constant on-site troubleshooting. Faculty complaints about unreliable recordings.",
        solution="Deployed Pearl across campus with Epiphan Cloud fleet management. Remote firmware updates, troubleshooting, and monitoring from one dashboard.",
        results=[
            "300+ rooms managed by team of 3",
            "7M+ video views annually",
            "90% reduction in on-site troubleshooting",
            "Faculty satisfaction improved significantly",
            "Panopto integration automated uploads",
        ],
        talking_points=[
            "Scale reference for higher ed (300+ rooms)",
            "Staffing efficiency (team of 3)",
            "Fleet management proof point",
            "Panopto integration validation",
            "Peer institution credibility",
        ],
        case_study_url="https://www.epiphan.com/case-studies/nc-state",
    ),
    ReferenceStory(
        id="unlv",
        customer="UNLV (University of Nevada, Las Vegas)",
        stats="215 Pearl units campus-wide",
        quote="Pearl gave us the scale we needed without adding headcount.",
        quote_person="Director of Academic Technologies",
        quote_title="Director of Academic Technologies",
        vertical=Vertical.HIGHER_ED,
        product="Pearl Nexus / Pearl-2",
        challenge="Campus-wide lecture capture deployment needed. Multiple buildings, varying room configurations. Integration with existing LMS required.",
        solution="Standardized on Pearl Nexus for fixed installations. Centralized management via Epiphan Cloud. Native LMS integration.",
        results=[
            "215 units deployed campus-wide",
            "Standardized hardware across all buildings",
            "Centralized remote management",
            "No additional staffing required",
            "Consistent recording quality",
        ],
        talking_points=[
            "Large-scale deployment (215 units)",
            "Standardization story",
            "No headcount increase",
            "Campus-wide consistency",
        ],
        case_study_url="https://www.epiphan.com/case-studies/unlv",
    ),
    ReferenceStory(
        id="mtsu",
        customer="MTSU (Middle Tennessee State University)",
        stats="428 Pearl units - largest deployment",
        quote="The largest Pearl deployment in higher education.",
        quote_person="AV Services Director",
        quote_title="Director of AV Services",
        vertical=Vertical.HIGHER_ED,
        product="Pearl Nexus / Pearl Mini",
        challenge="Massive scale lecture capture across entire university. Needed reliable, manageable solution for 400+ rooms.",
        solution="Deployed 428 Pearl units - the largest known Pearl deployment. Fleet management essential at this scale.",
        results=[
            "428 units deployed (largest Pearl deployment)",
            "University-wide standardization",
            "Fleet management at unprecedented scale",
            "Reliable lecture capture across all departments",
        ],
        talking_points=[
            "Largest deployment proof point",
            "Scale validation (428 units)",
            "Enterprise credibility",
            "Fleet management at scale",
        ],
        case_study_url=None,
    ),
    ReferenceStory(
        id="openai",
        customer="OpenAI",
        stats="'The workhorse of our streams'",
        quote="Pearl is the workhorse of our streams.",
        quote_person="Production Team",
        quote_title="Internal Communications",
        vertical=Vertical.CORPORATE,
        product="Pearl-2",
        challenge="High-stakes internal and external communications. Needed broadcast-quality reliability without dedicated production crew.",
        solution="Deployed Pearl-2 for executive communications, product launches, and internal streaming. Hardware reliability critical.",
        results=[
            "Broadcast-quality internal comms",
            "No production team required",
            "Zero failures during critical streams",
            "'Workhorse' status for reliability",
        ],
        talking_points=[
            "Tech company credibility (OpenAI)",
            "'Workhorse' quote - reliability",
            "Broadcast quality without crew",
            "High-stakes use case validation",
            "Modern tech company endorsement",
        ],
        case_study_url=None,
    ),
    ReferenceStory(
        id="harvard_dce",
        customer="Harvard DCE (Division of Continuing Education)",
        stats="Campus-wide deployment for online programs",
        quote="Consistent quality across all our online course recordings.",
        quote_person="Director of Media Services",
        quote_title="Director of Media Services",
        vertical=Vertical.HIGHER_ED,
        product="Pearl-2",
        challenge="Online program quality requirements. Multiple recording locations. Brand consistency critical for Harvard name.",
        solution="Standardized on Pearl for all online course recordings. Consistent output quality regardless of room or operator.",
        results=[
            "Consistent quality across all programs",
            "Brand standards maintained",
            "Scalable online course production",
            "Harvard-quality output",
        ],
        talking_points=[
            "Ivy League credibility",
            "Brand/quality consistency",
            "Online program production",
            "Harvard name recognition",
        ],
        case_study_url="https://www.epiphan.com/case-studies/harvard-dce",
    ),
    ReferenceStory(
        id="freeman",
        customer="Freeman AV",
        stats="Production company deployment",
        quote="Hardware reliability when failure isn't an option.",
        quote_person="Technical Director",
        quote_title="Senior Technical Director",
        vertical=Vertical.LIVE_EVENTS,
        product="Pearl-2",
        challenge="High-stakes corporate events where failure costs tens of thousands. PC-based solutions too risky for mission-critical production.",
        solution="Deployed Pearl-2 as reliable recording backup and primary capture. Hardware that doesn't blue-screen.",
        results=[
            "Zero recording failures at events",
            "Hardware backup for critical captures",
            "Production company endorsement",
            "Deployed across multiple event teams",
        ],
        talking_points=[
            "Production company credibility",
            "Mission-critical validation",
            "'Failure isn't an option' story",
            "Live events reliability",
        ],
        case_study_url=None,
    ),
    ReferenceStory(
        id="google",
        customer="Google",
        stats="Internal communications and training",
        quote="Reliable internal streaming infrastructure.",
        quote_person="Internal Communications",
        quote_title="Media Operations",
        vertical=Vertical.CORPORATE,
        product="Pearl-2",
        challenge="Global internal communications. Multiple office locations. Needed reliable, scalable streaming infrastructure.",
        solution="Deployed Pearl for internal town halls, training, and executive communications. Standardized approach.",
        results=[
            "Global internal streaming",
            "Multiple office deployment",
            "Executive communications quality",
            "Training content production",
        ],
        talking_points=[
            "Tech giant validation",
            "Global scale reference",
            "Internal comms use case",
            "Enterprise credibility",
        ],
        case_study_url=None,
    ),
    ReferenceStory(
        id="meta",
        customer="Meta",
        stats="Content production and streaming",
        quote="Broadcast quality for internal and external content.",
        quote_person="Media Production",
        quote_title="Media Production Manager",
        vertical=Vertical.CORPORATE,
        product="Pearl-2",
        challenge="High-volume content production. Needed reliable, professional-grade streaming and recording.",
        solution="Deployed Pearl for content production workflows. Professional output without production complexity.",
        results=[
            "High-volume content production",
            "Professional-grade output",
            "Reliable streaming infrastructure",
            "Simplified production workflow",
        ],
        talking_points=[
            "Tech giant validation",
            "Content production scale",
            "Professional quality",
            "Enterprise credibility",
        ],
        case_study_url=None,
    ),
]


# Reference customers by vertical for quick lookup
REFERENCE_BY_VERTICAL = {
    Vertical.HIGHER_ED: ["nc_state", "unlv", "mtsu", "harvard_dce"],
    Vertical.CORPORATE: ["openai", "google", "meta"],
    Vertical.LIVE_EVENTS: ["freeman"],
}

# Top references by use case
REFERENCE_BY_USE_CASE = {
    "fleet_management": ["nc_state", "unlv", "mtsu"],
    "executive_comms": ["openai", "google", "meta"],
    "live_events": ["freeman"],
    "online_courses": ["harvard_dce"],
    "reliability": ["openai", "freeman"],
    "scale": ["nc_state", "unlv", "mtsu"],
}


def get_story_by_id(story_id: str) -> ReferenceStory | None:
    """Get reference story by ID."""
    for story in REFERENCE_STORIES:
        if story.id == story_id:
            return story
    return None


def get_stories_by_vertical(vertical: Vertical) -> list[ReferenceStory]:
    """Get all reference stories for a vertical."""
    return [s for s in REFERENCE_STORIES if s.vertical == vertical]


def get_best_reference_for_context(
    vertical: Vertical | None = None,
    use_case: str | None = None,
) -> ReferenceStory | None:
    """Get the best reference story for a given context."""
    if use_case and use_case in REFERENCE_BY_USE_CASE:
        story_id = REFERENCE_BY_USE_CASE[use_case][0]
        return get_story_by_id(story_id)

    if vertical and vertical in REFERENCE_BY_VERTICAL:
        story_id = REFERENCE_BY_VERTICAL[vertical][0]
        return get_story_by_id(story_id)

    # Default to NC State (most comprehensive)
    return get_story_by_id("nc_state")
