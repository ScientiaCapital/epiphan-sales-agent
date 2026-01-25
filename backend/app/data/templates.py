"""Email and LinkedIn templates from Epiphan BDR Playbook."""

from app.data.schemas import EmailTemplate, LinkedInTemplate, Vertical

__all__ = [
    # Constants
    "EMAIL_TEMPLATES",
    "LINKEDIN_TEMPLATES",
    "LINKEDIN_POSTING_SCHEDULE",
    # Functions
    "get_templates_by_trigger",
    "get_templates_by_vertical",
]

EMAIL_TEMPLATES: list[EmailTemplate] = [
    # ============================================================================
    # TRIGGER-BASED TEMPLATES
    # ============================================================================
    EmailTemplate(
        id="construction_1",
        name="New Building Announcement",
        trigger="construction",
        subject="AV for your new {{building_type}} at {{company}}",
        body="""Hi {{first_name}},

Saw the news about your {{building_type}} project at {{company}} - exciting times.

{{reference_customer}} standardized on Epiphan Pearl for their new spaces. They're managing {{unit_count}}+ rooms with a team of {{team_size}} using our fleet management dashboard.

Worth a quick call to see if that approach fits your project?

Best,
Tim

P.S. Happy to share what {{reference_customer}} learned during their deployment.""",
        sequence_day=1,
        template_type="cold",
    ),
    EmailTemplate(
        id="equipment_failure",
        name="Post-Incident Outreach",
        trigger="equipment_failure",
        subject="Preventing the next recording failure at {{company}}",
        body="""Hi {{first_name}},

I work with AV teams who've dealt with equipment failures during critical events. The common theme: PC-based systems that crash at the worst possible time.

Pearl is purpose-built hardware that doesn't have Windows update surprises or driver conflicts. OpenAI calls it "the workhorse of our streams."

Would 15 minutes be worthwhile to see how it works?

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    EmailTemplate(
        id="ada_compliance",
        name="ADA Title II Deadline",
        trigger="compliance",
        vertical=Vertical.HIGHER_ED,
        subject="April 2026 ADA deadline - video captioning at {{company}}",
        body="""Hi {{first_name}},

With the April 2026 ADA Title II deadline approaching, many institutions are evaluating their video accessibility strategy.

Pearl integrates natively with Panopto, Kaltura, and YuJa - making captioned content automatic. NC State uses this approach across 300+ classrooms.

Would it help to see how they're handling accessibility at scale?

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    EmailTemplate(
        id="leadership_change",
        name="New AV Director",
        trigger="leadership_change",
        subject="Welcome to {{company}} - quick intro",
        body="""Hi {{first_name}},

Congrats on the new role at {{company}}. The first 90 days can be overwhelming - I wanted to be a resource, not a sales pitch.

Quick question: What's on your immediate priority list for classroom/meeting technology?

I work with AV Directors managing 50-500+ spaces. Happy to share what's working for peers in similar situations.

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    EmailTemplate(
        id="panopto_expansion",
        name="Panopto Hardware Angle",
        trigger="platform_expansion",
        subject="Hardware for your Panopto expansion",
        body="""Hi {{first_name}},

Heard you're expanding Panopto across campus. The platform is great - but the capture hardware often becomes the bottleneck.

Pearl integrates natively with Panopto and gives you:
- Remote management from one dashboard
- Auto-upload without manual intervention
- Hardware that doesn't crash mid-lecture

{{reference_customer}} scaled from {{before_count}} to {{after_count}} rooms using Pearl with Panopto.

Worth a quick call to compare approaches?

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    EmailTemplate(
        id="budget_cycle_fy",
        name="FY Planning Early Engagement",
        trigger="budget_cycle",
        subject="FY{{year}} AV planning at {{company}}",
        body="""Hi {{first_name}},

As you're putting together FY{{year}} plans, wanted to put something on your radar.

{{reference_customer}} budgeted Pearl deployments this way: hardware once, no recurring fees ever. That TCO story helped them get approval for {{unit_count}} units.

If AV refresh is in your plans, worth a conversation to see if the approach fits?

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    EmailTemplate(
        id="year_end_budget",
        name="Year-End Budget Allocation",
        trigger="budget_cycle",
        subject="End of year budget at {{company}}?",
        body="""Hi {{first_name}},

Quick question: Do you have end-of-year budget that needs allocation before {{deadline}}?

Pearl is a one-time hardware purchase with no recurring fees. Several clients use year-end funds for technology that:
- Doesn't require ongoing budget approval
- Ships quickly (in stock)
- Deploys without extensive IT integration

If that timing works, happy to expedite a quote.

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    # ============================================================================
    # VERTICAL-SPECIFIC TEMPLATES
    # ============================================================================
    EmailTemplate(
        id="higher_ed_1",
        name="Higher Ed - Fleet Management",
        trigger="vertical",
        vertical=Vertical.HIGHER_ED,
        subject="Managing {{room_count}}+ classrooms at {{company}}",
        body="""Hi {{first_name}},

NC State manages 300+ lecture capture rooms with a team of 3 using Epiphan Pearl. They went from constant firefighting to remote fleet management.

The key: one dashboard for firmware updates, troubleshooting, and status monitoring across every room.

If scale is your challenge, worth seeing how they did it?

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    EmailTemplate(
        id="corporate_1",
        name="Corporate - L&D Scaling",
        trigger="vertical",
        vertical=Vertical.CORPORATE,
        subject="Scaling training content at {{company}}",
        body="""Hi {{first_name}},

218% higher revenue per employee with video training (Brandon Hall). But most L&D teams can't scale content creation fast enough.

Pearl lets you record SME once, train 1,000 employees. No production team required. OpenAI uses it as "the workhorse of their streams."

If content backlog is your bottleneck, worth a quick conversation?

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    EmailTemplate(
        id="healthcare_1",
        name="Healthcare - Simulation",
        trigger="vertical",
        vertical=Vertical.HEALTHCARE,
        subject="Simulation recording at {{company}} - HIPAA compliant",
        body="""Hi {{first_name}},

Medical schools use Pearl because PHI never leaves the network - fully HIPAA compliant local recording.

Multi-angle capture for debriefing, native SimCapture integration, and SSH accreditation documentation.

If your next accreditation visit is approaching, worth seeing how peers handle it?

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    EmailTemplate(
        id="house_of_worship_1",
        name="House of Worship - Volunteer Friendly",
        trigger="vertical",
        vertical=Vertical.HOUSE_OF_WORSHIP,
        subject="Volunteer-friendly streaming at {{church}}",
        body="""Hi {{first_name}},

Churches use Pearl Mini because volunteers can run it - 5-minute training, no PC to crash on Sunday.

Touchscreen operation, hardware reliability, and no monthly streaming fees.

If volunteer turnover or Sunday reliability is a concern, worth a quick demo?

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    EmailTemplate(
        id="government_1",
        name="Government - Court Recording",
        trigger="vertical",
        vertical=Vertical.GOVERNMENT,
        subject="Court recording - 1.78M hearings go unrecorded",
        body="""Hi {{first_name}},

1.78 million hearings go without verbatim record annually due to court reporter shortages. 33 states now permit electronic recording.

Pearl is on TIPS and Sourcewell for easy procurement. CJIS-compliant with ADA captioning capability.

If the reporter shortage is affecting your operations, worth a conversation?

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    EmailTemplate(
        id="industrial_1",
        name="Industrial - Knowledge Transfer",
        trigger="vertical",
        vertical=Vertical.INDUSTRIAL,
        subject="Capturing expert knowledge before it retires",
        body="""Hi {{first_name}},

2.7 million boomers leaving the workforce take 30 years of know-how with them.

Manufacturers use Pearl to capture expert knowledge once, train new hires forever. Plus video documentation for OSHA compliance.

If knowledge transfer is on your radar, worth exploring?

Tim""",
        sequence_day=1,
        template_type="cold",
    ),
    # ============================================================================
    # SEQUENCE TEMPLATES
    # ============================================================================
    EmailTemplate(
        id="follow_up_1",
        name="No Response Follow-Up",
        trigger="sequence",
        subject="Re: {{previous_subject}}",
        body="""Hi {{first_name}},

Following up on my note about {{topic}}. Worth a quick conversation, or is this not a priority right now?

Either way, let me know - I don't want to keep pinging if timing isn't right.

Tim""",
        sequence_day=5,
        template_type="follow_up",
    ),
    EmailTemplate(
        id="breakup_1",
        name="Professional Breakup",
        trigger="sequence",
        subject="Should I close your file?",
        body="""Hi {{first_name}},

I've reached out a few times about {{topic}} without hearing back.

I'll assume timing isn't right and won't keep emailing. But my door is open if things change.

If there's someone else I should be talking to, happy for an introduction.

Best,
Tim""",
        sequence_day=18,
        template_type="breakup",
    ),
]


LINKEDIN_TEMPLATES: list[LinkedInTemplate] = [
    LinkedInTemplate(
        id="connection_request_av",
        name="Connection Request - AV Director",
        trigger="new_connection",
        vertical=Vertical.HIGHER_ED,
        message="""Hi {{first_name}}, I work with AV Directors managing 50-500+ rooms. Always looking to connect with peers in the space - would be great to share what's working. No pitch, just networking.""",
        character_count=198,
    ),
    LinkedInTemplate(
        id="connection_request_ld",
        name="Connection Request - L&D",
        trigger="new_connection",
        vertical=Vertical.CORPORATE,
        message="""Hi {{first_name}}, I work with L&D teams scaling training content. Always interested in what's working for peers - would love to connect and swap ideas.""",
        character_count=161,
    ),
    LinkedInTemplate(
        id="connection_request_technical",
        name="Connection Request - Technical Director",
        trigger="new_connection",
        vertical=Vertical.HOUSE_OF_WORSHIP,
        message="""Hi {{first_name}}, I saw your work at {{church}} - impressive production quality. Would love to connect with fellow technical directors.""",
        character_count=139,
    ),
    LinkedInTemplate(
        id="engagement_comment",
        name="Post Engagement - Value Add",
        trigger="engagement",
        message="""Great point about {{topic}}. I've seen similar results at {{reference}} - they found that {{insight}}. Would love to hear more about your approach.""",
        character_count=148,
    ),
    LinkedInTemplate(
        id="warm_outreach_content",
        name="Warm Outreach - Content Download",
        trigger="content_download",
        message="""Hi {{first_name}}, saw you downloaded our {{content_name}}. Did you find what you were looking for? Happy to answer any questions that came up.""",
        character_count=153,
    ),
    LinkedInTemplate(
        id="warm_outreach_event",
        name="Warm Outreach - Trade Show",
        trigger="trade_show",
        message="""Hi {{first_name}}, great connecting at {{event}}. The conversation about {{topic}} stuck with me - would love to continue the discussion.""",
        character_count=143,
    ),
    LinkedInTemplate(
        id="referral_intro",
        name="Referral Introduction",
        trigger="referral",
        message="""Hi {{first_name}}, {{referrer}} suggested I reach out - they mentioned you're dealing with {{challenge}}. Would a quick conversation be helpful?""",
        character_count=152,
    ),
    LinkedInTemplate(
        id="thought_leadership_share",
        name="Thought Leadership - Tuesday Post",
        trigger="posting_cadence",
        message="""{{insight_headline}}

{{body_paragraph}}

What's your experience with this?

#AVTech #LectureCapture #EdTech""",
        character_count=0,  # Variable
    ),
    LinkedInTemplate(
        id="case_study_share",
        name="Case Study - Thursday Post",
        trigger="posting_cadence",
        message="""📊 How {{customer}} manages {{scale}} with a team of {{team_size}}

{{key_insight}}

Full story: {{link}}

#HigherEd #AVManagement #CaseStudy""",
        character_count=0,  # Variable
    ),
]


# LinkedIn posting cadence (Tuesday/Thursday optimal for B2B)
LINKEDIN_POSTING_SCHEDULE = {
    "optimal_days": ["Tuesday", "Thursday"],
    "optimal_times": ["8:00 AM", "12:00 PM"],
    "content_mix": {
        "Tuesday": "Thought leadership / Industry insights",
        "Thursday": "Case studies / Customer stories",
    },
    "engagement_tips": [
        "Reply to comments within 1 hour",
        "Like and comment on prospect posts before outreach",
        "Share customer wins (with permission)",
        "Ask questions to drive engagement",
    ],
}


def get_templates_by_trigger(trigger: str) -> list[EmailTemplate]:
    """Get all email templates for a specific trigger."""
    return [t for t in EMAIL_TEMPLATES if t.trigger == trigger]


def get_templates_by_vertical(vertical: Vertical) -> list[EmailTemplate]:
    """Get all email templates for a vertical."""
    return [t for t in EMAIL_TEMPLATES if t.vertical == vertical]
