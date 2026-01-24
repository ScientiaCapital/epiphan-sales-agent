"""Market intelligence data from research-hub analysis (January 2026)."""

from app.data.schemas import MarketIntelligence

MARKET_INTELLIGENCE: list[MarketIntelligence] = [
    # ============================================================================
    # MARKET SIZE DATA
    # ============================================================================
    MarketIntelligence(
        id="lecture_capture_market",
        category="market_size",
        title="Lecture Capture Market Size",
        summary="Explosive growth in lecture capture market with 28.57% CAGR through 2030. Software dominates at 65% but hardware remains critical for enterprise deployments.",
        data_points={
            "2025_value_billions": 13.65,
            "2030_value_billions": 47.97,
            "cagr": 28.57,
            "software_share": 65.82,
            "hardware_share": 34.18,
            "key_drivers": [
                "Distance and hybrid learning demand",
                "LMS and collaboration tool integration",
                "AI-driven analytics adoption",
                "Government-funded classroom digitization",
            ],
        },
        sources=["Mordor Intelligence", "Grand View Research"],
        last_updated="2026-01-23",
    ),
    MarketIntelligence(
        id="pro_av_market",
        category="market_size",
        title="Pro AV Overall Market",
        summary="Pro AV market growth slowing to 3.9% CAGR due to macroeconomic pressures, but still reaching $402B by 2030.",
        data_points={
            "2024_value_billions": 321,
            "2025_value_billions": 332,
            "2030_value_billions": 402,
            "cagr": 3.9,
            "previous_cagr": 5.3,
            "growth_drivers": ["Hybrid workplace", "Experience economy", "AI integration"],
            "regional_leader": "Asia-Pacific",
        },
        sources=["AVIXA IOTA"],
        last_updated="2026-01-23",
    ),
    MarketIntelligence(
        id="enterprise_streaming_market",
        category="market_size",
        title="Enterprise Streaming Market",
        summary="Enterprise streaming growing 10.7-19.5% CAGR with training & development as largest segment.",
        data_points={
            "2024_value_billions": 38.30,
            "2025_value_billions": 48.2,
            "2029_value_billions": 98.36,
            "cagr_range": "10.7-19.5%",
            "top_segment": "Training & Development",
            "fastest_growing": "Corporate Communication",
        },
        sources=["Industry Analysis"],
        last_updated="2026-01-23",
    ),
    # ============================================================================
    # TECHNOLOGY TRENDS
    # ============================================================================
    MarketIntelligence(
        id="ndi_ecosystem",
        category="technology_trends",
        title="NDI 6 Ecosystem Expansion",
        summary="NDI 6 introduces WAN connectivity enabling new remote production use cases. NDI|HX3 standardization accelerating.",
        data_points={
            "ndi_6_features": ["HDR support", "10-bit color", "WAN connectivity", "Embedded Bridge"],
            "ndi_hx3_latency": "<100ms glass-to-glass",
            "bandwidth_requirement": "125+ Mbps for 1080p30",
            "key_vendors": ["BirdDog", "Kiloview", "PTZOptics", "Lumens", "Magewell", "Panasonic"],
            "opportunity": "Leverage NDI 6 WAN for education/enterprise hybrid scenarios",
        },
        sources=["NAB 2025", "IBC 2025"],
        last_updated="2026-01-23",
    ),
    MarketIntelligence(
        id="protocol_convergence",
        category="technology_trends",
        title="Protocol Convergence (2025-2026)",
        summary="SRT for remote ingest, NDI for local production, RTMP for legacy compatibility. Hybrid deployments becoming standard.",
        data_points={
            "protocols": {
                "NDI": {"use_case": "LAN production, studio", "bandwidth": "125+ Mbps", "latency": "Ultra-low"},
                "SRT": {"use_case": "Remote contribution over WAN", "bandwidth": "65% less than RTMP", "latency": "Low with error correction"},
                "RTMP": {"use_case": "Platform ingest (legacy)", "bandwidth": "Moderate", "latency": "Higher"},
            },
            "2025_best_practice": "SRT for remote ingest, NDI for local, RTMP for legacy",
        },
        sources=["Wowza 2026 Predictions"],
        last_updated="2026-01-23",
    ),
    MarketIntelligence(
        id="ai_video_tools",
        category="technology_trends",
        title="AI Video Tools Encroachment",
        summary="AI-powered tools lowering 'good enough' bar. Native transcription, auto-captioning, intelligent search becoming table stakes.",
        data_points={
            "key_players": {
                "Descript": {"feature": "Text-based editing, AI avatars", "price": "$5/user/month education"},
                "Riverside.fm": {"feature": "Remote recording, AI editing", "price": "$15/month+"},
                "Loom": {"feature": "Async video, Confluence integration", "price": "$40K+/year enterprise"},
            },
            "threat_level": "MEDIUM-HIGH",
            "implication": "Epiphan must add native transcription, auto-captioning to stay competitive",
        },
        sources=["Product Analysis"],
        last_updated="2026-01-23",
    ),
    MarketIntelligence(
        id="hybrid_cloud_trend",
        category="technology_trends",
        title="Hybrid Cloud/Appliance Deployments",
        summary="Organizations moving away from pure cloud toward on-premises + cloud burst capability. 40-60% cost savings on hybrid vs. pure cloud.",
        data_points={
            "trend": "Hybrid, on-premises, edge deployments becoming standard",
            "drivers": ["Data security", "Cost predictability", "Regulatory compliance"],
            "cost_savings": "40-60% vs. pure cloud",
            "wowza_quote": "Design solutions with portable, modular components that can leverage specialized hardware for high density, burst to cloud when needed",
        },
        sources=["Wowza 2026 Predictions"],
        last_updated="2026-01-23",
    ),
    # ============================================================================
    # COMPETITIVE INTELLIGENCE
    # ============================================================================
    MarketIntelligence(
        id="lumens_threat",
        category="competitive_intelligence",
        title="Lumens LC100N - Direct Pearl Nexus Competitor",
        summary="CRITICAL: Lumens offers 5-year warranty vs. Epiphan's 1-year at similar price point. Strong in APAC with growing NA presence.",
        data_points={
            "product": "LC100N CaptureVision",
            "price": "~$3,600",
            "vs_pearl_nexus": "~$3,500",
            "key_differentiator": "5-year warranty vs. 1-year",
            "threat_level": "HIGH",
            "recent_activity": "January 2026 partnership with Versatech International (Philippines)",
            "response": "Extend warranty to 3-5 years; emphasize touchscreen and NA support",
        },
        sources=["Lumens Product Specs", "Industry News"],
        last_updated="2026-01-23",
    ),
    MarketIntelligence(
        id="extron_smp401",
        category="competitive_intelligence",
        title="Extron SMP 401 - Direct Pearl-2 Competitor",
        summary="Extron SMP 401 shipping August 2024 with 4K/60 multi-channel recording. Strong enterprise sales channel.",
        data_points={
            "product": "SMP 401",
            "status": "NOW SHIPPING (August 2024)",
            "specs": {
                "resolution": "4K/60 multi-channel",
                "inputs": "3 HDMI + 2 RTP/RTSP + optional 12G-SDI",
                "at_1080p60": "5 recordings + 6 streams simultaneously",
                "encoding": "H.264/H.265",
            },
            "vms_integration": ["Kaltura", "Panopto", "YuJa", "Opencast"],
            "threat_level": "HIGH",
            "weakness": "Dealer-only pricing (opaque)",
        },
        sources=["Extron Product Specs"],
        last_updated="2026-01-23",
    ),
    MarketIntelligence(
        id="yuja_hardware",
        category="competitive_intelligence",
        title="YuJa Hardware Hub - Ecosystem Lock-In Threat",
        summary="YuJa offering own hardware (RCS-550/MCS-550) creating direct competition with locked ecosystem.",
        data_points={
            "products": ["RCS-550", "MCS-550"],
            "specs": "1U, 2-3 video sources, comparable to Pearl Mini/Nexus",
            "unique_angle": "Bootstrapped company, strong accessibility focus (Gen-AI PowerPack)",
            "recent_wins": ["Texas A&M", "Southern Arkansas", "Montana University System (16 institutions)"],
            "threat_level": "MEDIUM-HIGH",
            "response": "Emphasize Pearl's multi-CMS compatibility vs. YuJa single-platform lock-in",
        },
        sources=["YuJa Product Announcements"],
        last_updated="2026-01-23",
    ),
    MarketIntelligence(
        id="matrox_eol",
        category="competitive_intelligence",
        title="Matrox Product EOL - Displacement Opportunity",
        summary="Multiple Matrox products reaching end-of-life. Major displacement opportunity for Pearl.",
        data_points={
            "eol_products": {
                "Monarch HD": "EOL June 2024",
                "Monarch HDX": "EOL April 2025",
                "Maevex 6020 (Panopto)": "EOL July 2025",
            },
            "replacement": "Vion series (broadcast/IP focus)",
            "opportunity": "Target existing Matrox customers for replacement",
            "talking_point": "Pearl is modern replacement with cloud management PowerStream can't match",
        },
        sources=["Matrox EOL Announcements"],
        last_updated="2026-01-23",
    ),
    MarketIntelligence(
        id="echo360_churn",
        category="competitive_intelligence",
        title="Echo360 Customer Churn - Displacement Opportunity",
        summary="Echo360 walled garden driving customers away. Confirmed exits at SIU (June 2026) and UNCW (January 2026).",
        data_points={
            "status": "PE-backed, walled garden ecosystem",
            "confirmed_churn": {
                "SIU": "Contract expires June 2026",
                "UNCW": "Migrated to Panopto January 2026",
            },
            "funding": "$157M total, $43M line of credit May 2024",
            "acquisitions": ["GoReact (May 2025)", "Inkling (May 2024)"],
            "opportunity": "Package Pearl + Panopto/Kaltura as 'open platform' alternative",
            "pearl_integration": "NONE (closed ecosystem)",
        },
        sources=["Industry News", "Customer Announcements"],
        last_updated="2026-01-23",
    ),
    # ============================================================================
    # PRICING INTELLIGENCE
    # ============================================================================
    MarketIntelligence(
        id="hardware_pricing",
        category="pricing_intelligence",
        title="Hardware Pricing Landscape (January 2026)",
        summary="Pearl positioned mid-market with strong value proposition. Entry-level threat from Magewell and AJA.",
        data_points={
            "epiphan": {
                "Pearl Nano": "$1,999",
                "Pearl Nexus": "$3,299",
                "Pearl Mini": "$3,999",
                "Pearl-2": "$7,999",
            },
            "competitors": {
                "Lumens LC100N": "~$3,600",
                "Extron SMP 401": "Dealer-only (not public)",
                "AREC LS-860N": "AUD $7,695",
                "Cattura CaptureCast Pro": "$7,995",
                "Cattura CaptureCast NDI": "~$3,756",
                "AJA HELO Plus": "$1,699",
                "Magewell Pro Convert": "$499-$799",
            },
            "key_insight": "Warranty gap: Lumens 5-year vs. Epiphan 1-year is major competitive disadvantage",
        },
        sources=["Manufacturer Pricing"],
        last_updated="2026-01-23",
    ),
    # ============================================================================
    # STRATEGIC OPPORTUNITIES
    # ============================================================================
    MarketIntelligence(
        id="warranty_gap",
        category="strategic_opportunity",
        title="CRITICAL: Warranty Extension Needed",
        summary="1-year warranty vs. Lumens' 5-year is visible differentiator in RFP process. Immediate action needed.",
        data_points={
            "current_state": "Epiphan 1-year warranty",
            "competitor_benchmark": "Lumens 5-year standard",
            "market_impact": "HIGH - visible in RFP evaluation",
            "recommendation": "Extend to 3-5 years; bundle with SLA support; offer hardware insurance",
        },
        sources=["Competitive Analysis"],
        last_updated="2026-01-23",
    ),
    MarketIntelligence(
        id="ai_features_gap",
        category="strategic_opportunity",
        title="Native AI Features Required",
        summary="Competitors adding AI transcription, avatars, intelligent search. AI is table stakes for 2026.",
        data_points={
            "competitor_ai": {
                "Kaltura Genies": "Sentiment analysis, auto-captions, summaries, translations",
                "Panopto Access AI": "High-accuracy ASR, Microsoft 365 Copilot integration",
                "YuJa PowerPack": "Enhanced audio descriptions, multi-language dubbing",
            },
            "opportunity": "Partner with AI platforms or integrate with CMS partners' AI",
            "timeline": "6-12 months",
            "market_impact": "HIGH - AI is table stakes",
        },
        sources=["Product Analysis"],
        last_updated="2026-01-23",
    ),
    MarketIntelligence(
        id="ada_deadline",
        category="strategic_opportunity",
        title="ADA Title II Deadline (April 2026)",
        summary="ADA Title II accessibility deadline driving university video captioning investments.",
        data_points={
            "deadline": "April 2026",
            "requirement": "Video accessibility and captioning",
            "market_impact": "HIGH - regulatory driver",
            "opportunity": "Partner with AI platforms for enhanced audio descriptions; market as 'accessibility-by-design' hardware",
        },
        sources=["ADA Regulations"],
        last_updated="2026-01-23",
    ),
]


# Quick lookup by category
def get_intel_by_category(category: str) -> list[MarketIntelligence]:
    """Get all market intelligence for a category."""
    return [m for m in MARKET_INTELLIGENCE if m.category == category]


def get_intel_by_id(intel_id: str) -> MarketIntelligence | None:
    """Get specific market intelligence by ID."""
    for intel in MARKET_INTELLIGENCE:
        if intel.id == intel_id:
            return intel
    return None


# Summary exports for quick reference
MARKET_SIZE_SUMMARY = {
    "lecture_capture_2030": "$47.97B",
    "lecture_capture_cagr": "28.57%",
    "pro_av_2030": "$402B",
    "pro_av_cagr": "3.9%",
}

COMPETITOR_THREAT_LEVELS = {
    "HIGH": ["Lumens LC100N", "Extron SMP 401", "YuJa Hardware Hub"],
    "MEDIUM": ["AREC", "Matrox Vion", "Cattura/Vizrt"],
    "LOW": ["AJA HELO", "Teradek (different market)"],
    "DISPLACEMENT": ["SlingStudio (discontinued)", "Matrox Monarch (EOL)", "Echo360 (churn)"],
}

STRATEGIC_PRIORITIES = [
    {"priority": 1, "action": "Extend warranty to 3-5 years", "impact": "HIGH", "timeline": "Immediate"},
    {"priority": 2, "action": "Add AI transcription/captioning", "impact": "HIGH", "timeline": "6-12 months"},
    {"priority": 3, "action": "Target Echo360 churning customers", "impact": "MEDIUM", "timeline": "Q1-Q2 2026"},
    {"priority": 4, "action": "Position as hybrid-ready appliance", "impact": "MEDIUM", "timeline": "Ongoing"},
]
