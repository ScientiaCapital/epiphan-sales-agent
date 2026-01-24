-- Seed data for Epiphan Sales Agent
-- Reference customers, personas, and competitors from BDR Playbook

-- ============================================================================
-- SEED PERSONAS
-- ============================================================================

INSERT INTO seed_personas (id, title, title_variations, reports_to, team_size, budget_authority, verticals, day_to_day, kpis, pain_points, hot_buttons, discovery_questions, objections, buying_signals) VALUES
(
    'av_director',
    'AV Director',
    ARRAY['Director of AV Services', 'Classroom Technology Manager', 'Director of Learning Spaces', 'AV Manager'],
    'CIO, VP of IT, VP of Facilities',
    '3-15 people',
    '$200K - $2M annually',
    ARRAY['higher_ed', 'corporate', 'government', 'live_events']::vertical_type[],
    ARRAY['Managing 50-500+ rooms/spaces with small team', 'Responding to equipment failure tickets', 'Planning refresh cycles and construction projects', 'Evaluating new technology purchases', 'Training staff and end users'],
    ARRAY['System uptime / reliability', 'Support ticket volume and resolution time', 'Project deployment timeline', 'Budget management', 'End-user satisfaction scores'],
    '[{"point": "Equipment failures during critical events", "emotional_impact": "Anxiety, embarrassment", "solution": "Hardware reliability - no PC crashes"}, {"point": "Cant troubleshoot remotely", "emotional_impact": "Frustration, wasted travel", "solution": "Fleet management dashboard"}, {"point": "Understaffed for room count", "emotional_impact": "Overwhelm, burnout", "solution": "Remote management reduces on-site needs"}]'::jsonb,
    ARRAY['Manage 200+ rooms from one dashboard', 'Remote firmware updates and troubleshooting', 'Self-healing recording - auto-restart on failure', 'NC State manages 300+ with minimal staff', 'No recurring fees - ever', '3-year warranty with advance replacement'],
    ARRAY['How many rooms/spaces do you currently manage?', 'How many people on your team handle AV support?', 'What is your biggest reliability pain point right now?', 'Can you troubleshoot remotely, or do you have to be on-site?', 'When is your next major refresh or construction project?', 'What happens when equipment fails during a critical event?'],
    '[{"objection": "We are standardized on [competitor]", "response": "Pearl integrates with Crestron/Extron control systems. It adds capability, does not replace your ecosystem."}, {"objection": "Too expensive upfront", "response": "Compare 5-year TCO: no recurring fees vs. software subscriptions. Plus reduced support ticket volume."}]'::jsonb,
    '{"high": ["We have a construction project starting...", "I cant keep managing this many rooms with this team size", "We had a major failure during [important event]"], "medium": ["What is the support like?", "How does it integrate with our control system?", "Can I see the management dashboard?"]}'::jsonb
),
(
    'ld_director',
    'L&D Director',
    ARRAY['VP of Talent Development', 'Chief Learning Officer', 'Director of Learning & Development', 'Training Director'],
    'CHRO, VP of HR, COO',
    '5-50 people',
    '$500K - $5M+ annually',
    ARRAY['corporate', 'industrial']::vertical_type[],
    ARRAY['Designing training programs and curricula', 'Managing content creation workflows', 'Measuring training effectiveness and ROI', 'Responding to business unit training requests', 'Managing LMS and training technology stack'],
    ARRAY['Training completion rates', 'Time to competency for new hires', 'Cost per learner', 'Training ROI / business impact', 'Content production velocity'],
    '[{"point": "Cant scale content creation", "emotional_impact": "Frustration, bottleneck", "solution": "Self-service capture = more content"}, {"point": "High production costs", "emotional_impact": "Budget pressure", "solution": "No ongoing production team needed"}]'::jsonb,
    ARRAY['218% higher revenue per employee with video training (Brandon Hall)', 'Record SME once, train 1,000 employees', 'Self-service capture - no production team required', 'OpenAI uses Pearl as the workhorse of their streams', '40% reduction in training time with video', 'Consistent quality across all locations'],
    ARRAY['How are you creating training content today?', 'How much SME time do you spend on training delivery?', 'What is your cost per learner, and how are you trying to reduce it?', 'Are you delivering consistent training across all locations?', 'What happens when a key expert leaves or retires?', 'How long does it take to create a new training module?'],
    '[{"objection": "We outsource video production", "response": "Calculate annual contract vs. one-time hardware. Most see ROI in the first year."}, {"objection": "Our LMS handles this", "response": "Your LMS delivers content - Pearl creates it. They are complementary."}]'::jsonb,
    '{"high": ["We are trying to scale our training capacity", "Our production backlog is [X] months", "Key experts are retiring and we are losing knowledge", "We need to reduce training travel costs"], "medium": ["What is the learning curve for creating content?", "How does this integrate with [LMS]?", "Can you show me what the output looks like?"]}'::jsonb
),
(
    'simulation_director',
    'Simulation Center Director',
    ARRAY['Director of Simulation', 'Simulation Center Manager', 'Director of Clinical Simulation'],
    'Dean of Medicine, CMO, VP of Academic Affairs',
    '5-20 staff',
    '$100K - $1M annually',
    ARRAY['healthcare']::vertical_type[],
    ARRAY['Running simulation sessions for students/residents', 'Facilitating debriefing with video playback', 'Maintaining accreditation standards (SSH, LCME)', 'Managing simulation equipment and manikins', 'Tracking learner competency and assessments'],
    ARRAY['Accreditation compliance (SSH, LCME)', 'Session throughput and utilization', 'Debriefing effectiveness', 'Learner competency metrics', 'Technology reliability during sessions'],
    '[{"point": "Debriefing without video is less effective", "emotional_impact": "Frustration, suboptimal learning", "solution": "Multi-source video capture"}, {"point": "HIPAA compliance with cloud recording", "emotional_impact": "Legal/compliance anxiety", "solution": "Local recording - PHI never leaves network"}]'::jsonb,
    ARRAY['Local recording - HIPAA compliant, no PHI in cloud', 'SSH accreditation support', 'Native SimCapture/LearningSpace integration', 'Multi-source synchronized capture', 'Easy retrieval for debriefing', 'One device for entire sim room'],
    ARRAY['How are you capturing simulation sessions today?', 'Do you use SimCapture or LearningSpace?', 'When is your next SSH or LCME accreditation visit?', 'Are you concerned about HIPAA compliance with video storage?', 'How many simulation rooms do you need to equip?', 'What is your biggest challenge with debriefing?'],
    '[{"objection": "We use SimCapture already", "response": "Perfect - Pearl feeds into SimCapture as the hardware capture layer. Same workflow, better reliability."}, {"objection": "Budget is limited", "response": "Compare to OR-specific systems at $50K+. Pearl-2 at $7,999 is 90% less."}]'::jsonb,
    '{"high": ["Our SSH visit is coming up in [X] months", "We are expanding/building a new simulation center", "We had recording failures during [important session]", "We are concerned about [HIPAA/compliance]"], "medium": ["How does this integrate with SimCapture?", "Can you show me the debriefing playback?", "What is the installation process?"]}'::jsonb
);

-- ============================================================================
-- SEED COMPETITORS
-- ============================================================================

INSERT INTO seed_competitors (id, name, company, price_range, positioning, market_context, status, target_verticals, when_to_compete, when_to_walk_away, key_differentiators, claims, proof_points, talk_track, call_mentions, rank) VALUES
(
    'blackmagic_atem',
    'Blackmagic ATEM',
    'Blackmagic Design',
    '$295 - $2,795',
    'Budget-friendly live switching',
    'Most common competitor by call volume (507 mentions). Entry-level to prosumer live switching.',
    'active',
    ARRAY['house_of_worship', 'live_events', 'corporate']::vertical_type[],
    ARRAY['Recording is the primary need (not just switching)', 'Multiple rooms require fleet management', 'LMS integration is critical (Panopto/Kaltura/YuJa)', 'Mission-critical reliability (consequences matter)', 'Volunteer or non-technical operators', '24/7 unattended operation required'],
    ARRAY['Pure budget play under $1,000', 'Customer already invested heavily in ATEM ecosystem', 'Heavy live graphics/virtual sets required', 'Customer has dedicated production staff comfortable with ATEM'],
    '[{"feature": "Recording Architecture", "competitor_capability": "Requires external PC for recording", "pearl_capability": "All-in-one hardware recording", "why_it_matters": "PC can crash, Pearl hardware is purpose-built"}, {"feature": "Fleet Management", "competitor_capability": "None - per-device configuration", "pearl_capability": "Epiphan Cloud dashboard for 200+ rooms", "why_it_matters": "Enterprise scale impossible with ATEM"}]'::jsonb,
    '[{"claim": "ATEM is cheaper upfront", "response": "Calculate TCO: ATEM + PC + software + IT time = $3,000-5,000. Pearl Nano at $1,999 is all-in-one."}, {"claim": "ATEM has more I/O options", "response": "For switching, yes. But Pearl records reliably. Do you need a switcher or a recorder?"}]'::jsonb,
    ARRAY['NC State manages 300+ Pearl rooms with minimal staff vs. per-device ATEM management', 'ATEM audio drift after 60 minutes makes long sessions worthless (documented user reports)', 'ATEM software freezes requiring hard reboot documented during live broadcasts', 'Network connection limit of 6-8 simultaneous causes ignoring all connections'],
    '{"opening": "ATEM is a great switcher - probably the best value for live switching. But it is not a recorder. When recording is your primary need, you are bolting on a PC that can crash. Pearl is purpose-built for reliable recording.", "closing": "Keep ATEM for switching if you love it. But for recording - especially at scale - Pearl is the enterprise choice."}'::jsonb,
    507,
    1
),
(
    'vmix',
    'vMix',
    'vMix',
    '$700 - $3,000+ (software + PC)',
    'Flexible Windows-based production software',
    'Software solution requiring dedicated PC. Popular with tech-savvy users who want customization.',
    'active',
    ARRAY['live_events', 'house_of_worship']::vertical_type[],
    ARRAY['Reliability is paramount (cant risk Windows crashes)', 'Non-technical operators (volunteers, staff)', 'Multiple locations requiring standardization', 'LMS integration critical', '24/7 unattended operation'],
    ARRAY['Customer has dedicated IT staff comfortable with Windows', 'Advanced customization is required', 'Customer already invested in vMix and loves it', 'Budget is under $1,000'],
    '[{"feature": "Platform", "competitor_capability": "Windows PC software", "pearl_capability": "Purpose-built hardware appliance", "why_it_matters": "Windows updates, driver conflicts, blue screens are risks"}, {"feature": "Reliability", "competitor_capability": "Subject to Windows issues, driver conflicts, memory leaks", "pearl_capability": "Hardware does not blue-screen or require updates", "why_it_matters": "Cant fail on Sunday morning or during CEO address"}]'::jsonb,
    '[{"claim": "vMix is more flexible", "response": "Absolutely - vMix can do almost anything if you have the expertise. But flexibility requires complexity. Pearl trades flexibility for reliability."}, {"claim": "vMix is cheaper", "response": "Software is $700. Add a reliable PC ($1,200+), capture cards ($300+), IT time - you are at $2,500+ with Windows risk."}]'::jsonb,
    ARRAY['Windows 10/11 documented crashes during production (updates, drivers)', 'Memory leaks after 12-hour recordings require restart', 'Driver conflicts with capture cards cause freezes', 'Background apps (antivirus scans) interrupt recording', 'Windows ran into a problem during CEO address = career risk'],
    '{"opening": "vMix is incredibly flexible - if you have the expertise to manage Windows, drivers, and troubleshooting, it is powerful. But that flexibility comes with risk. Pearl is purpose-built hardware that will not blue-screen during your most important event.", "closing": "If you love vMix and have IT support, keep using it. For reliability without complexity, Pearl is the safer choice."}'::jsonb,
    NULL,
    3
),
(
    'slingstudio',
    'SlingStudio',
    'DISH Network (discontinued)',
    '$999 (when available)',
    'Wireless multi-camera production (DISCONTINUED)',
    'BUSINESS DISCONTINUED FEBRUARY 2022. Users are orphaned. Major displacement opportunity.',
    'discontinued',
    ARRAY['live_events', 'house_of_worship']::vertical_type[],
    ARRAY['ALWAYS compete - users are orphaned with no support', 'Users experiencing WiFi reliability issues', 'Users need wired reliability alternative', 'Users need fleet management (never had it)'],
    ARRAY['Never - this is pure displacement opportunity'],
    '[{"feature": "Business Status", "competitor_capability": "DISCONTINUED - NO SUPPORT", "pearl_capability": "Active product with roadmap", "why_it_matters": "Users have no future with SlingStudio"}, {"feature": "Connectivity", "competitor_capability": "WiFi-dependent (unreliable in congested venues)", "pearl_capability": "Wired reliability", "why_it_matters": "WiFi drops during events are common"}]'::jsonb,
    '[{"claim": "Our SlingStudio still works", "response": "For now. But there is no support, no updates, no parts. When it breaks, you are stuck."}, {"claim": "We like the wireless capability", "response": "Pearl gives you wired reliability with optional NDI for wireless when you need it. Best of both worlds."}]'::jsonb,
    ARRAY['DISH discontinued SlingStudio in February 2022', 'No support, updates, or replacement parts available', 'WiFi unreliability in congested venues (conferences, churches)', '2-3 second delay makes IMAG impossible', 'Requires iPad for operation (extra device failure point)'],
    '{"opening": "SlingStudio users are orphaned - DISH discontinued the product in 2022. There is no support, no updates, and no parts. Pearl gives you the same wireless multi-cam capability with wired reliability and active support.", "closing": "Your SlingStudio has no future. Pearl is the upgrade path with ongoing support and development."}'::jsonb,
    17,
    6
);

-- ============================================================================
-- SEED REFERENCE STORIES
-- ============================================================================

INSERT INTO seed_stories (id, customer, stats, quote, quote_person, quote_title, vertical, product, challenge, solution, results, talking_points, case_study_url) VALUES
(
    'nc_state',
    'NC State University',
    '300+ Pearl units, 7M+ annual views, team of 3',
    'We went from constant firefighting to remote fleet management.',
    'AV Director',
    'Director of Classroom Technology',
    'higher_ed',
    'Pearl Mini / Pearl-2',
    'Managing 300+ lecture capture rooms with limited staff. Constant on-site troubleshooting. Faculty complaints about unreliable recordings.',
    'Deployed Pearl across campus with Epiphan Cloud fleet management. Remote firmware updates, troubleshooting, and monitoring from one dashboard.',
    ARRAY['300+ rooms managed by team of 3', '7M+ video views annually', '90% reduction in on-site troubleshooting', 'Faculty satisfaction improved significantly', 'Panopto integration automated uploads'],
    ARRAY['Scale reference for higher ed (300+ rooms)', 'Staffing efficiency (team of 3)', 'Fleet management proof point', 'Panopto integration validation', 'Peer institution credibility'],
    'https://www.epiphan.com/case-studies/nc-state'
),
(
    'unlv',
    'UNLV (University of Nevada, Las Vegas)',
    '215 Pearl units campus-wide',
    'Pearl gave us the scale we needed without adding headcount.',
    'Director of Academic Technologies',
    'Director of Academic Technologies',
    'higher_ed',
    'Pearl Nexus / Pearl-2',
    'Campus-wide lecture capture deployment needed. Multiple buildings, varying room configurations. Integration with existing LMS required.',
    'Standardized on Pearl Nexus for fixed installations. Centralized management via Epiphan Cloud. Native LMS integration.',
    ARRAY['215 units deployed campus-wide', 'Standardized hardware across all buildings', 'Centralized remote management', 'No additional staffing required', 'Consistent recording quality'],
    ARRAY['Large-scale deployment (215 units)', 'Standardization story', 'No headcount increase', 'Campus-wide consistency'],
    'https://www.epiphan.com/case-studies/unlv'
),
(
    'openai',
    'OpenAI',
    'The workhorse of our streams',
    'Pearl is the workhorse of our streams.',
    'Production Team',
    'Internal Communications',
    'corporate',
    'Pearl-2',
    'High-stakes internal and external communications. Needed broadcast-quality reliability without dedicated production crew.',
    'Deployed Pearl-2 for executive communications, product launches, and internal streaming. Hardware reliability critical.',
    ARRAY['Broadcast-quality internal comms', 'No production team required', 'Zero failures during critical streams', 'Workhorse status for reliability'],
    ARRAY['Tech company credibility (OpenAI)', 'Workhorse quote - reliability', 'Broadcast quality without crew', 'High-stakes use case validation', 'Modern tech company endorsement'],
    NULL
);

-- Verify seed data
SELECT 'Personas seeded: ' || COUNT(*)::text FROM seed_personas;
SELECT 'Competitors seeded: ' || COUNT(*)::text FROM seed_competitors;
SELECT 'Stories seeded: ' || COUNT(*)::text FROM seed_stories;
