"""Pydantic schemas for seed data structures.

Based on TypeScript interfaces from epiphan-bdr-playbook/study-app/data.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class Vertical(str, Enum):
    """Epiphan target verticals."""

    HIGHER_ED = "higher_ed"
    CORPORATE = "corporate"
    LIVE_EVENTS = "live_events"
    GOVERNMENT = "government"
    HOUSE_OF_WORSHIP = "house_of_worship"
    HEALTHCARE = "healthcare"
    INDUSTRIAL = "industrial"
    LEGAL = "legal"
    UX_RESEARCH = "ux_research"


class PersonaType(str, Enum):
    """Buyer persona types."""

    AV_DIRECTOR = "av_director"
    LD_DIRECTOR = "ld_director"
    TECHNICAL_DIRECTOR = "technical_director"
    SIMULATION_DIRECTOR = "simulation_director"
    COURT_ADMINISTRATOR = "court_administrator"
    CORP_COMMS_DIRECTOR = "corp_comms_director"
    EHS_MANAGER = "ehs_manager"
    LAW_FIRM_IT = "law_firm_it"


class SPINStage(str, Enum):
    """SPIN Discovery stages."""

    SITUATION = "situation"
    PROBLEM = "problem"
    IMPLICATION = "implication"
    NEED_PAYOFF = "need_payoff"


class QualificationRating(str, Enum):
    """BANT+ qualification rating."""

    HOT = "hot"
    WARM = "warm"
    COOL = "cool"
    COLD = "cold"


class TriggerType(str, Enum):
    """Warm inbound trigger types."""

    CONTENT_DOWNLOAD = "content_download"
    WEBINAR_ATTENDED = "webinar_attended"
    DEMO_REQUEST = "demo_request"
    PRICING_PAGE = "pricing_page"
    CONTACT_FORM = "contact_form"
    TRADE_SHOW = "trade_show"
    REFERRAL = "referral"
    RETURN_VISITOR = "return_visitor"


class CompetitorStatus(str, Enum):
    """Competitor market status."""

    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    COMPLEMENTARY = "complementary"


# ============================================================================
# Nested Models
# ============================================================================


class PainPoint(BaseModel):
    """Pain point with emotional impact and solution mapping."""

    point: str
    emotional_impact: str
    solution: str


class ObjectionResponse(BaseModel):
    """Objection handling pair."""

    objection: str
    response: str


class BuyingSignals(BaseModel):
    """Buying signal indicators by intent level."""

    high: list[str] = Field(default_factory=list)
    medium: list[str] = Field(default_factory=list)


class KeyDifferentiator(BaseModel):
    """Feature comparison between competitor and Pearl."""

    feature: str
    competitor_capability: str
    pearl_capability: str
    why_it_matters: str


class ClaimResponse(BaseModel):
    """Competitor claim with counter-response."""

    claim: str
    response: str


class TalkTrack(BaseModel):
    """Opening and closing talk tracks."""

    opening: str
    closing: str


class ObjectionPivot(BaseModel):
    """Objection with pivot response for calls."""

    objection: str
    response: str


class WarmInboundVariation(BaseModel):
    """Variation of warm inbound script."""

    context: str
    script: str


class QualificationCriterion(BaseModel):
    """BANT+ qualification criterion."""

    id: str
    category: str  # budget, authority, need, timeline, competition
    signal: str
    rating: QualificationRating
    key_question: Optional[str] = None


class MarketSize(BaseModel):
    """Market size data point."""

    year: int
    value_billions: float
    source: Optional[str] = None


# ============================================================================
# Main Entity Models
# ============================================================================


class PersonaProfile(BaseModel):
    """Complete buyer persona profile from BDR playbook."""

    id: str
    title: str
    title_variations: list[str]
    reports_to: str
    team_size: str
    budget_authority: str
    verticals: list[Vertical]
    day_to_day: list[str]
    kpis: list[str]
    pain_points: list[PainPoint]
    hot_buttons: list[str]
    discovery_questions: list[str]
    objections: list[ObjectionResponse]
    buying_signals: BuyingSignals

    class Config:
        use_enum_values = True


class CompetitorBattlecard(BaseModel):
    """Competitive battlecard for sales positioning."""

    id: str
    name: str
    company: str
    price_range: str
    positioning: str
    market_context: str
    status: CompetitorStatus = CompetitorStatus.ACTIVE
    target_verticals: list[Vertical] = Field(default_factory=list)
    when_to_compete: list[str]
    when_to_walk_away: list[str]
    key_differentiators: list[KeyDifferentiator]
    claims: list[ClaimResponse]
    proof_points: list[str]
    talk_track: TalkTrack
    call_mentions: Optional[int] = None
    rank: Optional[int] = None

    class Config:
        use_enum_values = True


class ColdCallScript(BaseModel):
    """Cold call script by vertical."""

    id: str
    vertical: Vertical
    vertical_icon: str
    target_persona: str
    pattern_interrupt: str
    value_hook: str
    pain_question: str
    permission: str
    pivot: str
    why_it_works: list[str]
    objection_pivots: list[ObjectionPivot]

    class Config:
        use_enum_values = True


class WarmInboundScript(BaseModel):
    """Warm inbound call script by trigger type."""

    id: str
    trigger_type: TriggerType
    trigger_icon: str
    hubspot_signal: str
    acknowledge: str
    connect: str
    qualify: str
    propose: str
    variations: list[WarmInboundVariation] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class DiscoveryQuestion(BaseModel):
    """SPIN discovery question."""

    id: str
    stage: SPINStage
    vertical: str  # "universal" or specific vertical
    question: str
    what_you_learn: str

    class Config:
        use_enum_values = True


class EmailTemplate(BaseModel):
    """Email template for outreach sequences."""

    id: str
    name: str
    trigger: str  # construction, equipment_failure, compliance, etc.
    vertical: Optional[Vertical] = None
    subject: str
    body: str
    sequence_day: Optional[int] = None
    template_type: str = "cold"  # cold, warm, follow_up, breakup

    class Config:
        use_enum_values = True


class LinkedInTemplate(BaseModel):
    """LinkedIn message template."""

    id: str
    name: str
    trigger: str
    vertical: Optional[Vertical] = None
    message: str
    character_count: int = 0

    class Config:
        use_enum_values = True


class ReferenceStory(BaseModel):
    """Customer reference story / case study."""

    id: str
    customer: str
    stats: str
    quote: str
    quote_person: str
    quote_title: str
    vertical: Vertical
    product: str
    challenge: str
    solution: str
    results: list[str]
    talking_points: list[str]
    case_study_url: Optional[str] = None

    class Config:
        use_enum_values = True


class CompetitorPricing(BaseModel):
    """Competitor pricing data."""

    product: str
    vendor: str
    price: str
    notes: str


class TechnologyTrend(BaseModel):
    """Technology trend data."""

    name: str
    description: str
    relevance: str
    opportunity: str


class MarketIntelligence(BaseModel):
    """Market intelligence summary."""

    id: str
    category: str  # market_size, competitor_analysis, technology_trends, etc.
    title: str
    summary: str
    data_points: dict = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)
    last_updated: str
