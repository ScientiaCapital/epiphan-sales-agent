"""Competitor battlecard data from Epiphan BDR Playbook.

15+ competitive profiles with positioning, differentiators, and talk tracks.
"""

from app.data.schemas import (
    CompetitorBattlecard,
    KeyDifferentiator,
    ClaimResponse,
    TalkTrack,
    Vertical,
    CompetitorStatus,
)

COMPETITORS: list[CompetitorBattlecard] = [
    CompetitorBattlecard(
        id="blackmagic_atem",
        name="Blackmagic ATEM",
        company="Blackmagic Design",
        price_range="$295 - $2,795",
        positioning="Budget-friendly live switching",
        market_context="Most common competitor by call volume (507 mentions). Entry-level to prosumer live switching.",
        status=CompetitorStatus.ACTIVE,
        target_verticals=[Vertical.HOUSE_OF_WORSHIP, Vertical.LIVE_EVENTS, Vertical.CORPORATE],
        when_to_compete=[
            "Recording is the primary need (not just switching)",
            "Multiple rooms require fleet management",
            "LMS integration is critical (Panopto/Kaltura/YuJa)",
            "Mission-critical reliability (consequences matter)",
            "Volunteer or non-technical operators",
            "24/7 unattended operation required",
        ],
        when_to_walk_away=[
            "Pure budget play under $1,000",
            "Customer already invested heavily in ATEM ecosystem",
            "Heavy live graphics/virtual sets required",
            "Customer has dedicated production staff comfortable with ATEM",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Recording Architecture",
                competitor_capability="Requires external PC for recording",
                pearl_capability="All-in-one hardware recording",
                why_it_matters="PC can crash, Pearl hardware is purpose-built",
            ),
            KeyDifferentiator(
                feature="Fleet Management",
                competitor_capability="None - per-device configuration",
                pearl_capability="Epiphan Cloud dashboard for 200+ rooms",
                why_it_matters="Enterprise scale impossible with ATEM",
            ),
            KeyDifferentiator(
                feature="LMS Integration",
                competitor_capability="None",
                pearl_capability="Native Panopto, Kaltura, YuJa, Opencast",
                why_it_matters="Education market excluded for ATEM",
            ),
            KeyDifferentiator(
                feature="Reliability",
                competitor_capability="Documented network drops, software freezes",
                pearl_capability="Purpose-built hardware, 24/7 capable",
                why_it_matters="Cost of failed recording > price difference",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="ATEM is cheaper upfront",
                response="Calculate TCO: ATEM + PC + software + IT time = $3,000-5,000. Pearl Nano at $1,999 is all-in-one.",
            ),
            ClaimResponse(
                claim="ATEM has more I/O options",
                response="For switching, yes. But Pearl records reliably. Do you need a switcher or a recorder?",
            ),
            ClaimResponse(
                claim="We've used ATEM for years",
                response="For what use case? If recording is primary, Pearl is purpose-built for that. Keep ATEM for switching.",
            ),
        ],
        proof_points=[
            "NC State manages 300+ Pearl rooms with minimal staff vs. per-device ATEM management",
            "ATEM audio drift after 60 minutes makes long sessions 'worthless' (documented user reports)",
            "ATEM software freezes requiring hard reboot documented during live broadcasts",
            "Network connection limit of 6-8 simultaneous causes ignoring all connections",
        ],
        talk_track=TalkTrack(
            opening="ATEM is a great switcher - probably the best value for live switching. But it's not a recorder. When recording is your primary need, you're bolting on a PC that can crash. Pearl is purpose-built for reliable recording.",
            closing="Keep ATEM for switching if you love it. But for recording - especially at scale - Pearl is the enterprise choice.",
        ),
        call_mentions=507,
        rank=1,
    ),
    CompetitorBattlecard(
        id="tricaster",
        name="TriCaster",
        company="Vizrt (formerly NewTek)",
        price_range="$9,995 - $34,995",
        positioning="Professional broadcast production",
        market_context="Premium live production with virtual sets and graphics. Overkill for recording-first use cases.",
        status=CompetitorStatus.ACTIVE,
        target_verticals=[Vertical.LIVE_EVENTS, Vertical.CORPORATE],
        when_to_compete=[
            "Recording is primary (not production)",
            "IT-managed deployment (not dedicated production staff)",
            "Budget-conscious evaluation",
            "LMS integration required",
            "Multiple locations/fleet deployment",
        ],
        when_to_walk_away=[
            "Heavy live graphics/virtual sets required",
            "Dedicated broadcast production staff",
            "Customer wants TriCaster-specific features",
            "Film/broadcast production is primary use case",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Primary Function",
                competitor_capability="Live production with graphics/virtual sets",
                pearl_capability="Recording-first with production capabilities",
                why_it_matters="TriCaster is overkill when recording is primary",
            ),
            KeyDifferentiator(
                feature="Price Point",
                competitor_capability="$10K-$35K",
                pearl_capability="$2K-$8K",
                why_it_matters="Pearl is 50-80% less for recording use cases",
            ),
            KeyDifferentiator(
                feature="Complexity",
                competitor_capability="Requires training and expertise",
                pearl_capability="Touchscreen operation, volunteer-friendly",
                why_it_matters="IT/AV teams can deploy Pearl, not just production staff",
            ),
            KeyDifferentiator(
                feature="Fleet Management",
                competitor_capability="Per-device, limited remote management",
                pearl_capability="Epiphan Cloud for enterprise scale",
                why_it_matters="UNLV chose Pearl for 215+ rooms, not TriCaster",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="TriCaster is the industry standard",
                response="For broadcast production, absolutely. For lecture capture and corporate recording, Pearl is the standard. UNLV has 215 Pearls.",
            ),
            ClaimResponse(
                claim="We need the virtual set capabilities",
                response="Fair point - TriCaster excels there. But do you need virtual sets, or do you need reliable recording? Different tools.",
            ),
            ClaimResponse(
                claim="TriCaster can do everything",
                response="It can - but at what cost and complexity? Pearl does recording brilliantly for a fraction of the price.",
            ),
        ],
        proof_points=[
            "UNLV standardized on 215 Pearl units, not TriCaster",
            "TriCaster acquired by Vizrt in 2019 - product direction uncertain",
            "Windows Embedded reliability concerns (same Windows update issues)",
            "NC State manages 300+ Pearl rooms - wouldn't be economical with TriCaster",
        ],
        talk_track=TalkTrack(
            opening="TriCaster is excellent for broadcast production - if you need virtual sets and advanced graphics, it's a great choice. But for recording-first workflows, it's overkill. Pearl does recording brilliantly at half the cost.",
            closing="If production is your need, consider TriCaster. If recording is your need, Pearl is purpose-built and proven at scale.",
        ),
        call_mentions=None,
        rank=2,
    ),
    CompetitorBattlecard(
        id="vmix",
        name="vMix",
        company="vMix",
        price_range="$700 - $3,000+ (software + PC)",
        positioning="Flexible Windows-based production software",
        market_context="Software solution requiring dedicated PC. Popular with tech-savvy users who want customization.",
        status=CompetitorStatus.ACTIVE,
        target_verticals=[Vertical.LIVE_EVENTS, Vertical.HOUSE_OF_WORSHIP],
        when_to_compete=[
            "Reliability is paramount (can't risk Windows crashes)",
            "Non-technical operators (volunteers, staff)",
            "Multiple locations requiring standardization",
            "LMS integration critical",
            "24/7 unattended operation",
        ],
        when_to_walk_away=[
            "Customer has dedicated IT staff comfortable with Windows",
            "Advanced customization is required",
            "Customer already invested in vMix and loves it",
            "Budget is under $1,000",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Platform",
                competitor_capability="Windows PC software",
                pearl_capability="Purpose-built hardware appliance",
                why_it_matters="Windows updates, driver conflicts, blue screens are risks",
            ),
            KeyDifferentiator(
                feature="Reliability",
                competitor_capability="Subject to Windows issues, driver conflicts, memory leaks",
                pearl_capability="Hardware doesn't blue-screen or require updates",
                why_it_matters="Can't fail on Sunday morning or during CEO's address",
            ),
            KeyDifferentiator(
                feature="Operator Skill",
                competitor_capability="Requires Windows/IT knowledge",
                pearl_capability="Touchscreen operation, 5-minute training",
                why_it_matters="Volunteers can operate Pearl without IT support",
            ),
            KeyDifferentiator(
                feature="Long-Duration Recording",
                competitor_capability="Memory leaks after 12+ hours documented",
                pearl_capability="Built for 24/7 operation",
                why_it_matters="Enterprise and healthcare need always-on recording",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="vMix is more flexible",
                response="Absolutely - vMix can do almost anything if you have the expertise. But flexibility requires complexity. Pearl trades flexibility for reliability.",
            ),
            ClaimResponse(
                claim="vMix is cheaper",
                response="Software is $700. Add a reliable PC ($1,200+), capture cards ($300+), IT time - you're at $2,500+ with Windows risk.",
            ),
            ClaimResponse(
                claim="We've been using vMix for years",
                response="How many times has Windows updated during an event? How long to troubleshoot PC issues? Pearl eliminates that risk.",
            ),
        ],
        proof_points=[
            "Windows 10/11 documented crashes during production (updates, drivers)",
            "Memory leaks after 12-hour recordings require restart",
            "Driver conflicts with capture cards cause freezes",
            "Background apps (antivirus scans) interrupt recording",
            "'Windows ran into a problem' during CEO address = career risk",
        ],
        talk_track=TalkTrack(
            opening="vMix is incredibly flexible - if you have the expertise to manage Windows, drivers, and troubleshooting, it's powerful. But that flexibility comes with risk. Pearl is purpose-built hardware that won't blue-screen during your most important event.",
            closing="If you love vMix and have IT support, keep using it. For reliability without complexity, Pearl is the safer choice.",
        ),
        call_mentions=None,
        rank=3,
    ),
    CompetitorBattlecard(
        id="teradek",
        name="Teradek",
        company="Videndum (Creative Solutions)",
        price_range="$1,500 - $16,000",
        positioning="Wireless transmission and mobile streaming",
        market_context="Emmy-winning wireless technology for film/sports. Streaming-focused, not recording-focused.",
        status=CompetitorStatus.ACTIVE,
        target_verticals=[Vertical.LIVE_EVENTS],
        when_to_compete=[
            "Recording is primary need (Teradek is streaming-only)",
            "Fixed installation (not mobile wireless)",
            "LMS integration required",
            "No tolerance for subscription fees",
            "Multiple inputs needed",
        ],
        when_to_walk_away=[
            "Mobile wireless transmission is primary need",
            "Film/sports production context",
            "Customer has existing Teradek investment",
            "Single-source streaming only",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Primary Function",
                competitor_capability="Wireless transmission and streaming",
                pearl_capability="Recording-first with streaming",
                why_it_matters="Teradek streams but doesn't record well (SD card only)",
            ),
            KeyDifferentiator(
                feature="Recording",
                competitor_capability="SD card only, single source",
                pearl_capability="Multi-source to internal SSD",
                why_it_matters="Enterprise recording needs more than SD cards",
            ),
            KeyDifferentiator(
                feature="Subscription",
                competitor_capability="Core.io: $49-299/month ($600-3,600/year)",
                pearl_capability="No recurring fees ever",
                why_it_matters="TCO over 3 years: Teradek = $7,564+, Pearl = $3,999 once",
            ),
            KeyDifferentiator(
                feature="LMS Integration",
                competitor_capability="None",
                pearl_capability="Native Panopto, Kaltura, YuJa",
                why_it_matters="Education market excluded for Teradek",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="Teradek is used in Hollywood",
                response="Absolutely - for wireless transmission. But you need recording, not wireless. Different tools.",
            ),
            ClaimResponse(
                claim="Core.io is great for cloud management",
                response="At $600-3,600/year. Epiphan Cloud is included with Pearl. No subscription.",
            ),
            ClaimResponse(
                claim="Teradek has better streaming quality",
                response="For mobile streaming, yes. For fixed installations with recording, Pearl is purpose-built.",
            ),
        ],
        proof_points=[
            "Overheating problems documented (Bolt Pro 300, early models)",
            "Battery life poor: VidiU Go 80-90 min vs. claimed 2.5 hours",
            "Customer service rated 'slowest tech support'",
            "SD card recording only - no large storage option",
            "Single-source focus - not multi-source production",
        ],
        talk_track=TalkTrack(
            opening="Teradek is excellent for wireless camera-to-monitor transmission - they've won Emmys for that. For fixed installations with recording and LMS integration, Pearl is purpose-built.",
            closing="If you need wireless transmission, Teradek is great. If you need reliable recording, Pearl is the choice.",
        ),
        call_mentions=128,
        rank=4,
    ),
    CompetitorBattlecard(
        id="yolobox",
        name="YoloBox",
        company="YoloLiv",
        price_range="$699 - $1,999",
        positioning="Portable Android-based streaming tablet",
        market_context="Prosumer/creator market. Good for individuals, not enterprise.",
        status=CompetitorStatus.ACTIVE,
        target_verticals=[Vertical.HOUSE_OF_WORSHIP],
        when_to_compete=[
            "Multiple locations requiring fleet management",
            "LMS integration critical (education)",
            "Mission-critical reliability",
            "Enterprise-scale deployment",
            "IT team needs to manage devices",
        ],
        when_to_walk_away=[
            "Single location, budget under $1,000",
            "Individual creator use case",
            "Customer already owns YoloBox and loves it",
            "Portability is the primary requirement",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Platform",
                competitor_capability="Android tablet",
                pearl_capability="Purpose-built hardware appliance",
                why_it_matters="Android instability, memory corruption, restarts documented",
            ),
            KeyDifferentiator(
                feature="Fleet Management",
                competitor_capability="None - consumer device",
                pearl_capability="Epiphan Cloud for enterprise",
                why_it_matters="Can't manage 50+ YoloBoxes at scale",
            ),
            KeyDifferentiator(
                feature="Thermal Management",
                competitor_capability="Overheating causing freezes and data loss",
                pearl_capability="Enterprise thermal design for 24/7",
                why_it_matters="Can't overheat during important events",
            ),
            KeyDifferentiator(
                feature="LMS Integration",
                competitor_capability="None",
                pearl_capability="Native Panopto, Kaltura, YuJa",
                why_it_matters="Education market excluded for YoloBox",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="YoloBox is cheaper",
                response="For a single device, yes. For enterprise deployment, you need reliability and management YoloBox can't provide.",
            ),
            ClaimResponse(
                claim="YoloBox is portable",
                response="Great for mobile use. For fixed installations, you need enterprise reliability.",
            ),
            ClaimResponse(
                claim="Our church loves YoloBox",
                response="For small churches, it works. But what happens when it crashes on Sunday? Pearl is insurance.",
            ),
        ],
        proof_points=[
            "Android-based crashes requiring restarts (documented)",
            "Overheating causing freezes and data loss",
            "Cannot turn on while charging",
            "Picky USB-C charger requirements",
            "NDI costs $99 extra (not included)",
            "'Restart is often first troubleshooting step' (user support forums)",
        ],
        talk_track=TalkTrack(
            opening="YoloBox is perfect for solo creators and small operations - it's portable and affordable. When streaming becomes mission-critical infrastructure, you need Pearl's enterprise reliability.",
            closing="For individual use, YoloBox is great. For enterprise or education, Pearl is the professional choice.",
        ),
        call_mentions=48,
        rank=5,
    ),
    CompetitorBattlecard(
        id="slingstudio",
        name="SlingStudio",
        company="DISH Network (discontinued)",
        price_range="$999 (when available)",
        positioning="Wireless multi-camera production (DISCONTINUED)",
        market_context="BUSINESS DISCONTINUED FEBRUARY 2022. Users are orphaned. Major displacement opportunity.",
        status=CompetitorStatus.DISCONTINUED,
        target_verticals=[Vertical.LIVE_EVENTS, Vertical.HOUSE_OF_WORSHIP],
        when_to_compete=[
            "ALWAYS compete - users are orphaned with no support",
            "Users experiencing WiFi reliability issues",
            "Users need wired reliability alternative",
            "Users need fleet management (never had it)",
        ],
        when_to_walk_away=[
            "Never - this is pure displacement opportunity",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Business Status",
                competitor_capability="DISCONTINUED - NO SUPPORT",
                pearl_capability="Active product with roadmap",
                why_it_matters="Users have no future with SlingStudio",
            ),
            KeyDifferentiator(
                feature="Connectivity",
                competitor_capability="WiFi-dependent (unreliable in congested venues)",
                pearl_capability="Wired reliability",
                why_it_matters="WiFi drops during events are common",
            ),
            KeyDifferentiator(
                feature="Latency",
                competitor_capability="2-3 second delay (unsuitable for IMAG)",
                pearl_capability="Near-zero latency",
                why_it_matters="Can't do real-time production with SlingStudio",
            ),
            KeyDifferentiator(
                feature="Fleet Management",
                competitor_capability="Never had any",
                pearl_capability="Epiphan Cloud dashboard",
                why_it_matters="Enterprise scale was never possible",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="Our SlingStudio still works",
                response="For now. But there's no support, no updates, no parts. When it breaks, you're stuck.",
            ),
            ClaimResponse(
                claim="We like the wireless capability",
                response="Pearl gives you wired reliability with optional NDI for wireless when you need it. Best of both worlds.",
            ),
        ],
        proof_points=[
            "DISH discontinued SlingStudio in February 2022",
            "No support, updates, or replacement parts available",
            "WiFi unreliability in congested venues (conferences, churches)",
            "2-3 second delay makes IMAG impossible",
            "Requires iPad for operation (extra device failure point)",
            "4 wireless sources only, 2-hour battery max",
        ],
        talk_track=TalkTrack(
            opening="SlingStudio users are orphaned - DISH discontinued the product in 2022. There's no support, no updates, and no parts. Pearl gives you the same wireless multi-cam capability with wired reliability and active support.",
            closing="Your SlingStudio has no future. Pearl is the upgrade path with ongoing support and development.",
        ),
        call_mentions=17,
        rank=6,
    ),
    CompetitorBattlecard(
        id="extron_smp",
        name="Extron SMP",
        company="Extron Electronics",
        price_range="Dealer pricing (not public)",
        positioning="Enterprise AV ecosystem recording",
        market_context="Strong enterprise sales channel. SMP 401 (August 2024) is direct Pearl-2 competitor.",
        status=CompetitorStatus.ACTIVE,
        target_verticals=[Vertical.CORPORATE, Vertical.HIGHER_ED],
        when_to_compete=[
            "Customer open to best recording solution (not locked to Extron)",
            "Fleet management quality matters",
            "Touchscreen interface valued",
            "Transparent pricing preferred",
        ],
        when_to_walk_away=[
            "Deep existing Extron ecosystem investment",
            "Extron integrator relationship locked in",
            "Customer requires Extron-specific features",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Pricing",
                competitor_capability="Dealer-only, opaque",
                pearl_capability="Transparent public pricing",
                why_it_matters="Hard to compare TCO with hidden pricing",
            ),
            KeyDifferentiator(
                feature="Interface",
                competitor_capability="Web UI only",
                pearl_capability="7-inch touchscreen (Pearl Mini)",
                why_it_matters="Operators can use Pearl without training",
            ),
            KeyDifferentiator(
                feature="Independence",
                competitor_capability="Best with Extron ecosystem",
                pearl_capability="Works with any control system",
                why_it_matters="Pearl adds capability without ecosystem lock-in",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="We're an Extron shop",
                response="Pearl integrates with Extron control systems. It adds capability, doesn't replace your ecosystem.",
            ),
            ClaimResponse(
                claim="SMP 401 has more channels",
                response="For some configs, yes. But Pearl's touchscreen and fleet management are mature advantages.",
            ),
        ],
        proof_points=[
            "Pearl works with Crestron AND Extron - not locked to one",
            "Epiphan Cloud more mature than Extron's management",
            "Pearl Mini touchscreen vs. web UI only",
            "Transparent pricing vs. dealer opacity",
        ],
        talk_track=TalkTrack(
            opening="Extron makes excellent AV infrastructure - if you're an Extron shop, the SMP fits your ecosystem. Pearl works alongside any control system and adds touchscreen operation that Extron lacks.",
            closing="Pearl complements Extron - you don't have to choose. For recording specifically, Pearl has advantages worth evaluating.",
        ),
        call_mentions=None,
        rank=7,
    ),
    CompetitorBattlecard(
        id="crestron",
        name="Crestron",
        company="Crestron Electronics",
        price_range="System-dependent",
        positioning="Room control with capture capability",
        market_context="Control system leader. Capture is secondary function. Pearl COMPLEMENTS Crestron.",
        status=CompetitorStatus.COMPLEMENTARY,
        target_verticals=[Vertical.CORPORATE, Vertical.HIGHER_ED],
        when_to_compete=[
            "Never compete directly - position as complementary",
            "Customer needs better recording than Crestron capture provides",
            "Multi-source production required",
        ],
        when_to_walk_away=[
            "Customer only needs basic single-source capture",
            "Crestron integrator has full solution",
            "Customer locked into Crestron Capture",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Primary Function",
                competitor_capability="Room control (capture is secondary)",
                pearl_capability="Recording-first",
                why_it_matters="Crestron does control well, Pearl does recording well",
            ),
            KeyDifferentiator(
                feature="Multi-Source",
                competitor_capability="Limited multi-source capability",
                pearl_capability="Full multi-source production",
                why_it_matters="Pearl adds capability Crestron lacks",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="We're a Crestron shop",
                response="Perfect - Pearl integrates with Crestron control. It adds recording capability your control system doesn't have.",
            ),
            ClaimResponse(
                claim="Crestron Capture handles recording",
                response="For basic capture, yes. Pearl adds multi-source production and better LMS integration.",
            ),
        ],
        proof_points=[
            "Pearl integrates natively with Crestron control systems",
            "Complementary, not competitive positioning",
            "Adds capability without replacing infrastructure",
        ],
        talk_track=TalkTrack(
            opening="Crestron is excellent for room control - we integrate with Crestron, not compete against it. Pearl adds recording capability that complements your control system.",
            closing="Keep Crestron for control. Add Pearl for recording. They work together.",
        ),
        call_mentions=None,
        rank=8,
    ),
    CompetitorBattlecard(
        id="matrox",
        name="Matrox Monarch/Vion",
        company="Matrox Video",
        price_range="$3,000 - $10,600",
        positioning="Encoding and AV-over-IP (multiple products EOL)",
        market_context="DISPLACEMENT OPPORTUNITY: Monarch HD (EOL June 2024), Monarch HDX (EOL April 2025), Maevex 6020 (EOL July 2025).",
        status=CompetitorStatus.ACTIVE,
        target_verticals=[Vertical.HIGHER_ED, Vertical.CORPORATE],
        when_to_compete=[
            "ALWAYS with EOL products - users need replacement",
            "PowerStream Plus Windows limitation matters",
            "On-device controls needed",
            "Firmware update process is concern",
        ],
        when_to_walk_away=[
            "Vion series meets their needs",
            "Broadcast/IP workflow primary focus",
            "Customer comfortable with Matrox support",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Product Status",
                competitor_capability="Multiple EOL: Monarch HD/HDX, Maevex 6020",
                pearl_capability="Active product with roadmap",
                why_it_matters="Matrox users need replacement path",
            ),
            KeyDifferentiator(
                feature="Fleet Management",
                competitor_capability="PowerStream Plus - Windows desktop only",
                pearl_capability="Epiphan Cloud - web-based",
                why_it_matters="Cloud management vs. Windows application",
            ),
            KeyDifferentiator(
                feature="On-Device Control",
                competitor_capability="No on-device controls",
                pearl_capability="7-inch touchscreen (Pearl Mini)",
                why_it_matters="Setup 'a pain' without device controls",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="We're happy with our Monarch",
                response="Which model? Monarch HD and HDX are discontinued. Pearl is the modern replacement with cloud management.",
            ),
            ClaimResponse(
                claim="PowerStream Plus works for us",
                response="It's a Windows desktop app - Epiphan Cloud is web-based, accessible anywhere.",
            ),
        ],
        proof_points=[
            "Monarch HD: EOL June 2024",
            "Monarch HDX: EOL April 2025",
            "Maevex 6020 (Panopto): EOL July 2025",
            "PowerStream Plus is Windows-only desktop app",
            "Setup described as 'a pain' by users",
            "Cannot verify encoder settings before going live",
        ],
        talk_track=TalkTrack(
            opening="Your Monarch HDX is discontinued - Matrox ended support in April 2025. Pearl is the modern replacement path with cloud management that PowerStream Plus can't match.",
            closing="Matrox users need a replacement path. Pearl is purpose-built with ongoing development.",
        ),
        call_mentions=None,
        rank=9,
    ),
    CompetitorBattlecard(
        id="haivision",
        name="Haivision Makito",
        company="Haivision",
        price_range="$10,000 - $50,000+",
        positioning="Premium broadcast/contribution encoding",
        market_context="SRT inventors, broadcast-certified. 2-3x Pearl price for similar capability.",
        status=CompetitorStatus.ACTIVE,
        target_verticals=[Vertical.LIVE_EVENTS],
        when_to_compete=[
            "Budget matters (Pearl is 50-80% less)",
            "Education/corporate use case (not broadcast)",
            "LMS integration required",
            "Customer questioning premium pricing",
        ],
        when_to_walk_away=[
            "Broadcast TV contribution is primary",
            "Customer requires Haivision-specific certifications",
            "Existing Haivision investment",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Pricing",
                competitor_capability="$10K-$50K+",
                pearl_capability="$2K-$8K",
                why_it_matters="2-3x premium for similar recording capability",
            ),
            KeyDifferentiator(
                feature="SRT Support",
                competitor_capability="SRT inventors (no longer differentiator)",
                pearl_capability="Full SRT support",
                why_it_matters="SRT is now industry standard - everyone has it",
            ),
            KeyDifferentiator(
                feature="Target Market",
                competitor_capability="Broadcast contribution",
                pearl_capability="Education/corporate recording",
                why_it_matters="Different use cases, different price points",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="Haivision invented SRT",
                response="They did - and now SRT is an open standard. Pearl fully supports it at a fraction of the price.",
            ),
            ClaimResponse(
                claim="Haivision is broadcast-grade",
                response="For broadcast contribution, yes. For education and corporate recording, Pearl is purpose-built at better value.",
            ),
        ],
        proof_points=[
            "SRT is now industry standard - no longer Haivision differentiator",
            "Pearl-2 at $7,999 vs. Makito X4 at $15,000+",
            "Same SRT protocol, different price point",
            "Enterprise buyers questioning 2-3x premium",
        ],
        talk_track=TalkTrack(
            opening="Haivision invented SRT - they're the gold standard for broadcast contribution. But SRT is now an open standard. Pearl fully supports it at a fraction of the price for education and corporate use.",
            closing="For broadcast TV, Haivision makes sense. For everything else, Pearl delivers the same quality at better value.",
        ),
        call_mentions=None,
        rank=10,
    ),
    CompetitorBattlecard(
        id="magewell",
        name="Magewell",
        company="Magewell",
        price_range="$299 - $1,299",
        positioning="Capture cards and NDI encoders (components)",
        market_context="Components, not complete system. Aggressive pricing erodes mid-range value.",
        status=CompetitorStatus.ACTIVE,
        target_verticals=[Vertical.CORPORATE, Vertical.LIVE_EVENTS],
        when_to_compete=[
            "Customer needs complete solution (not components)",
            "LMS integration required",
            "Fleet management needed",
            "Non-technical operators",
        ],
        when_to_walk_away=[
            "Customer wants to build custom PC solution",
            "Single-source simple capture only",
            "Budget under $500",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Solution Type",
                competitor_capability="Components requiring PC + software",
                pearl_capability="Complete all-in-one system",
                why_it_matters="Total system cost often exceeds Pearl",
            ),
            KeyDifferentiator(
                feature="LMS Integration",
                competitor_capability="None (requires external software)",
                pearl_capability="Native Panopto, Kaltura, YuJa",
                why_it_matters="Education market excluded",
            ),
            KeyDifferentiator(
                feature="Fleet Management",
                competitor_capability="None",
                pearl_capability="Epiphan Cloud",
                why_it_matters="Can't manage Magewell cards at scale",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="Magewell is cheaper",
                response="The card is $499. Add PC + software + integration + IT time = $2,000+. Pearl is all-in-one.",
            ),
            ClaimResponse(
                claim="We want to build our own system",
                response="That works for one room. For 50+ rooms, you need standardization and management Pearl provides.",
            ),
        ],
        proof_points=[
            "Magewell + PC + software = $1,000-4,700+ total system",
            "OEM in Cattura/Vizrt (they use Magewell internally)",
            "Q-SYS plugins (January 2025) expanding ecosystem",
            "Components don't include management or LMS integration",
        ],
        talk_track=TalkTrack(
            opening="Magewell makes excellent capture cards - great for custom PC builds. But when you add PC, software, and IT time, the total cost often exceeds Pearl, which is all-in-one with management included.",
            closing="For DIY builders, Magewell is great. For enterprise deployment, Pearl is the complete solution.",
        ),
        call_mentions=None,
        rank=11,
    ),
    CompetitorBattlecard(
        id="lumens",
        name="Lumens LC Series",
        company="Lumens Integration (Pegatron)",
        price_range="$3,000 - $3,600",
        positioning="Direct Pearl Nexus competitor with 5-year warranty",
        market_context="Near-identical price to Pearl Nexus. CRITICAL: 5-year warranty vs. Epiphan 1-year.",
        status=CompetitorStatus.ACTIVE,
        target_verticals=[Vertical.HIGHER_ED, Vertical.CORPORATE],
        when_to_compete=[
            "North American support matters (Ottawa vs. Taiwan)",
            "Touchscreen interface valued",
            "Full NDI (vs. NDI|HX2)",
            "Existing Epiphan relationship",
        ],
        when_to_walk_away=[
            "Warranty is primary decision factor (5-year vs. 1-year)",
            "APAC deployment with local support needs",
            "PTZ camera ecosystem integration required",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Warranty",
                competitor_capability="5-year standard",
                pearl_capability="1-year standard (WEAKNESS)",
                why_it_matters="Major competitive disadvantage - address proactively",
            ),
            KeyDifferentiator(
                feature="Interface",
                competitor_capability="Web UI only",
                pearl_capability="7-inch touchscreen (Pearl Mini)",
                why_it_matters="On-device operation without training",
            ),
            KeyDifferentiator(
                feature="NDI",
                competitor_capability="NDI|HX2",
                pearl_capability="Full NDI",
                why_it_matters="Pearl-2 has better NDI performance",
            ),
            KeyDifferentiator(
                feature="Support Location",
                competitor_capability="Taiwan-based",
                pearl_capability="Ottawa-based (North America)",
                why_it_matters="Time zone and language advantage for NA customers",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="Lumens has 5-year warranty",
                response="That's a strong point. Pearl's reliability means fewer claims - but we can discuss extended warranty options.",
            ),
            ClaimResponse(
                claim="Lumens is same price",
                response="Similar hardware price. Pearl's touchscreen (Mini) and North American support are the differentiators.",
            ),
        ],
        proof_points=[
            "LC100N at ~$3,600 vs. Pearl Nexus ~$3,500",
            "Pearl Mini touchscreen vs. web UI only",
            "Full NDI vs. NDI|HX2",
            "Ottawa support vs. Taiwan time zone",
        ],
        talk_track=TalkTrack(
            opening="Lumens has a good warranty - that's their strength. Pearl's touchscreen operation and North American support from Ottawa are ours. Similar price, different advantages.",
            closing="For APAC with local support, Lumens might make sense. For North America, Pearl's Ottawa support and touchscreen are significant.",
        ),
        call_mentions=None,
        rank=12,
    ),
    CompetitorBattlecard(
        id="arec",
        name="AREC Media Station",
        company="AREC Inc.",
        price_range="AUD $7,199 - $7,695",
        positioning="Asia-Pacific education with speaker tracking",
        market_context="Strong in APAC. Unique speaker tracking feature (DS-9CU). Taiwan-based support.",
        status=CompetitorStatus.ACTIVE,
        target_verticals=[Vertical.HIGHER_ED],
        when_to_compete=[
            "North American deployment (Ottawa support advantage)",
            "NDI/SRT protocols (vs. proprietary AV-over-IP)",
            "Touchscreen operation valued",
        ],
        when_to_walk_away=[
            "APAC deployment with local support needs",
            "Speaker tracking is critical feature",
            "Existing AREC relationship",
        ],
        key_differentiators=[
            KeyDifferentiator(
                feature="Geographic Support",
                competitor_capability="Taiwan-based (APAC strength)",
                pearl_capability="Ottawa-based (NA strength)",
                why_it_matters="For NA deployments, Pearl support is local",
            ),
            KeyDifferentiator(
                feature="Protocols",
                competitor_capability="AV-over-IP focused (different protocol family)",
                pearl_capability="NDI, SRT (won in North America)",
                why_it_matters="NDI/SRT aligns with NA infrastructure",
            ),
            KeyDifferentiator(
                feature="Interface",
                competitor_capability="Web UI only",
                pearl_capability="Touchscreen available",
                why_it_matters="On-device operation advantage",
            ),
            KeyDifferentiator(
                feature="Unique Feature",
                competitor_capability="Speaker tracking (DS-9CU)",
                pearl_capability="No built-in speaker tracking",
                why_it_matters="AREC differentiator for lecture capture",
            ),
        ],
        claims=[
            ClaimResponse(
                claim="AREC has speaker tracking",
                response="DS-9CU is impressive for automated lecture capture. For manual production or non-lecture use cases, Pearl's flexibility is the advantage.",
            ),
            ClaimResponse(
                claim="AREC is strong in education",
                response="In Asia-Pacific, yes. For North American education, Pearl's Ottawa support and NDI/SRT protocols align better.",
            ),
        ],
        proof_points=[
            "Pearl supports NDI/SRT (protocols that won in NA)",
            "Ottawa support vs. Taiwan time zone",
            "Touchscreen vs. web UI only",
            "LS-860N at AUD $7,695 vs. Pearl Mini at ~$4,000 USD",
        ],
        talk_track=TalkTrack(
            opening="AREC makes solid lecture capture with good automation, especially strong in Asia-Pacific. For North American deployments, Pearl's Ottawa support and NDI/SRT protocols align better with local infrastructure.",
            closing="If you're deploying in Asia with AREC relationships, that might make sense. For North America, Pearl's local support is significant.",
        ),
        call_mentions=None,
        rank=13,
    ),
]


def get_competitor_by_id(competitor_id: str) -> CompetitorBattlecard | None:
    """Lookup competitor by ID."""
    for competitor in COMPETITORS:
        if competitor.id == competitor_id:
            return competitor
    return None


def get_active_competitors() -> list[CompetitorBattlecard]:
    """Get all active competitors."""
    return [c for c in COMPETITORS if c.status == CompetitorStatus.ACTIVE]


def get_displacement_opportunities() -> list[CompetitorBattlecard]:
    """Get discontinued competitors (displacement opportunities)."""
    return [c for c in COMPETITORS if c.status == CompetitorStatus.DISCONTINUED]


def get_competitors_by_vertical(vertical: Vertical) -> list[CompetitorBattlecard]:
    """Get competitors targeting a specific vertical."""
    return [c for c in COMPETITORS if vertical in c.target_verticals]
