"""Coaching intelligence types ported from Souffleur (Rust → Python).

MEDDIC tracking, DISC buyer profiling, call stage FSM, coaching responses,
and partner progress tracking. All state types enforce monotonic progression —
once confirmed, never regress.

Source: epiphan-ai-souffleur/crates/souffleur-core/src/types.rs
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, Field

# Module-level constants — single source of truth for criterion names
MEDDIC_CRITERION_NAMES: list[str] = [
    "Metrics", "Economic Buyer", "Decision Criteria",
    "Decision Process", "Pain", "Champion",
]
MEDDIC_CRITERION_KEYS: list[str] = [
    "metrics", "economic_buyer", "decision_criteria",
    "decision_process", "identify_pain", "champion",
]
MEDDIC_CRITERION_LABELS: list[str] = ["M", "E", "D", "D", "I", "C"]

PARTNER_CRITERION_NAMES: list[str] = [
    "Product Familiarity", "Active Projects", "Displacement",
    "Spec-In", "Margin", "Certification",
]
PARTNER_CRITERION_LABELS: list[str] = ["P", "A", "D", "S", "M", "C"]

# =============================================================================
# Enums
# =============================================================================


class CallStage(str, Enum):
    """Sales call stage — 9 stages with FSM transition rules."""

    OPENING = "opening"
    DISCOVERY = "discovery"
    QUALIFICATION = "qualification"
    DEMO = "demo"
    NEGOTIATION = "negotiation"
    OBJECTION_HANDLING = "objection_handling"
    CLOSING = "closing"
    SUPPORT = "support"
    RENEWAL = "renewal"

    @property
    def stage_index(self) -> int:
        return _STAGE_INDEX[self]

    @property
    def level(self) -> int:
        """Sales flow level. Support/Renewal are lateral (level 0)."""
        return _STAGE_LEVEL[self]

    def can_transition_to(self, next_stage: CallStage) -> bool:
        """Check if transition is valid per the 9x9 matrix."""
        return TRANSITIONS[self.stage_index][next_stage.stage_index]

    def validated_transition(
        self, proposed: CallStage, watermark: int
    ) -> tuple[CallStage, int]:
        """Validate transition with watermark anti-regression.

        Returns (actual_next_stage, new_watermark).
        Lateral stages (Support/Renewal) don't update watermark.
        """
        if not self.can_transition_to(proposed):
            return (self, watermark)

        is_lateral = proposed in (CallStage.SUPPORT, CallStage.RENEWAL)

        if is_lateral:
            return (proposed, watermark)
        elif proposed.level >= watermark:
            return (proposed, proposed.level)
        else:
            return (self, watermark)


_STAGE_INDEX: dict[CallStage, int] = {s: i for i, s in enumerate(CallStage)}

_STAGE_LEVEL: dict[CallStage, int] = {
    CallStage.OPENING: 0,
    CallStage.DISCOVERY: 1,
    CallStage.QUALIFICATION: 2,
    CallStage.DEMO: 3,
    CallStage.NEGOTIATION: 4,
    CallStage.OBJECTION_HANDLING: 5,
    CallStage.CLOSING: 6,
    CallStage.SUPPORT: 0,
    CallStage.RENEWAL: 0,
}

# 9x9 transition matrix: TRANSITIONS[from][to] = allowed
# Rules: diagonal=true, forward=true, ObjHandling/Support/Renewal reachable from anywhere
# Backward in sales flow = false
#                          Op    Dis   Qua   Dem   Neg   Obj   Clo   Sup   Ren
TRANSITIONS: list[list[bool]] = [
    # Opening
    [True, True, True, True, True, True, True, True, True],
    # Discovery
    [False, True, True, True, True, True, True, True, True],
    # Qualification
    [False, False, True, True, True, True, True, True, True],
    # Demo
    [False, False, False, True, True, True, True, True, True],
    # Negotiation
    [False, False, False, False, True, True, True, True, True],
    # ObjHandling
    [False, False, False, False, False, True, True, True, True],
    # Closing
    [False, False, False, False, False, True, True, True, True],
    # Support
    [True, True, True, True, True, True, True, True, True],
    # Renewal
    [True, True, True, True, True, True, True, True, True],
]


class CustomerSentiment(str, Enum):
    """Detected customer emotional state."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    SKEPTICAL = "skeptical"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"
    INTERESTED = "interested"
    RESISTANT = "resistant"
    EAGER = "eager"


class CoachingType(str, Enum):
    """Type of coaching intervention."""

    WHISPER = "whisper"
    QUESTION_PROMPT = "question_prompt"
    OBJECTION_HANDLER = "objection_handler"
    DATA_POINT = "data_point"
    STAGE_TRANSITION = "stage_transition"
    SILENCE = "silence"
    LISTEN = "listen"


class CoachingUrgency(str, Enum):
    """Urgency level for coaching tip."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CoachingFocus(str, Enum):
    """What the rep should focus on."""

    ASK_QUESTION = "ask_question"
    ANSWER_NOW = "answer_now"
    HANDLE_OBJECTION = "handle_objection"
    BOOK_DEMO = "book_demo"
    USE_CRM = "use_crm"
    POSITION_PRODUCT = "position_product"
    STAY_SILENT = "stay_silent"


class NextGoal(str, Enum):
    """Recommended next coaching goal."""

    DISCOVER_PAIN = "discover_pain"
    QUALIFY = "qualify"
    ANSWER_QUESTION = "answer_question"
    POSITION_PRODUCT = "position_product"
    BOOK_DEMO = "book_demo"
    CONFIRM_NEXT_STEP = "confirm_next_step"
    SUPPORT_CUSTOMER = "support_customer"


class ObjectionType(str, Enum):
    """Type of objection detected."""

    PRICE = "price"
    COMPETITOR = "competitor"
    RISK = "risk"
    TIMING = "timing"
    FEATURE_GAP = "feature_gap"
    SOFT = "soft"
    NONE = "none"


class BookingSignal(str, Enum):
    """Strength of demo/meeting booking signal."""

    NONE = "none"
    SOFT = "soft"
    DIRECT = "direct"


class DiscType(str, Enum):
    """DISC buyer personality type."""

    DOMINANT = "dominant"
    INFLUENTIAL = "influential"
    STEADY = "steady"
    CONSCIENTIOUS = "conscientious"
    UNKNOWN = "unknown"


class DiscConfidence(str, Enum):
    """Confidence level for DISC detection."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def level(self) -> int:
        return _DISC_CONF_LEVEL[self]


_DISC_CONF_LEVEL: dict[DiscConfidence, int] = {
    DiscConfidence.LOW: 0,
    DiscConfidence.MEDIUM: 1,
    DiscConfidence.HIGH: 2,
}


class AudienceType(str, Enum):
    """Sales conversation audience type."""

    DIRECT_SALE = "direct_sale"
    CHANNEL_PARTNER = "channel_partner"

    @property
    def is_channel(self) -> bool:
        return self == AudienceType.CHANNEL_PARTNER


class PartnerFamiliarity(str, Enum):
    """How familiar the partner is with Epiphan products. Monotonic."""

    UNKNOWN = "unknown"
    AWARE = "aware"
    FAMILIAR = "familiar"
    CERTIFIED = "certified"

    @property
    def level(self) -> int:
        return _PARTNER_FAM_LEVEL[self]

    def merge_higher(self, incoming: PartnerFamiliarity) -> PartnerFamiliarity:
        """Return the higher of self and incoming."""
        if incoming.level > self.level:
            return incoming
        return self


_PARTNER_FAM_LEVEL: dict[PartnerFamiliarity, int] = {
    PartnerFamiliarity.UNKNOWN: 0,
    PartnerFamiliarity.AWARE: 1,
    PartnerFamiliarity.FAMILIAR: 2,
    PartnerFamiliarity.CERTIFIED: 3,
}


class SpecInStatus(str, Enum):
    """Whether the partner will spec Epiphan in proposals. Monotonic."""

    NONE = "none"
    INTERESTED = "interested"
    COMMITTED = "committed"

    @property
    def level(self) -> int:
        return _SPEC_IN_LEVEL[self]

    def merge_higher(self, incoming: SpecInStatus) -> SpecInStatus:
        """Return the higher of self and incoming."""
        if incoming.level > self.level:
            return incoming
        return self


_SPEC_IN_LEVEL: dict[SpecInStatus, int] = {
    SpecInStatus.NONE: 0,
    SpecInStatus.INTERESTED: 1,
    SpecInStatus.COMMITTED: 2,
}


# =============================================================================
# Models — MEDDIC
# =============================================================================


class MeddicCriterion(BaseModel):
    """Single MEDDIC criterion with evidence. Monotonic: confirmed can only go false→true."""

    confirmed: bool = False
    evidence: str | None = None

    def confirm(self, evidence: str) -> None:
        """Confirm with evidence. Once confirmed, never regress. Evidence set on first confirm only."""
        if not self.confirmed:
            self.confirmed = True
            self.evidence = evidence


class MeddicScore(BaseModel):
    """Bool-only MEDDIC — wire format from LLM structured output."""

    metrics: bool = False
    economic_buyer: bool = False
    decision_criteria: bool = False
    decision_process: bool = False
    identify_pain: bool = False
    champion: bool = False

    KEYS: ClassVar[list[str]] = MEDDIC_CRITERION_KEYS
    LABELS: ClassVar[list[str]] = MEDDIC_CRITERION_LABELS
    NAMES: ClassVar[list[str]] = MEDDIC_CRITERION_NAMES

    def score(self) -> int:
        return sum(self.values())

    def values(self) -> list[bool]:
        return [
            self.metrics, self.economic_buyer, self.decision_criteria,
            self.decision_process, self.identify_pain, self.champion,
        ]

    def gaps(self) -> list[str]:
        return [n for v, n in zip(self.values(), MEDDIC_CRITERION_NAMES, strict=True) if not v]


class MeddicTracker(BaseModel):
    """MEDDIC tracker with evidence per criterion. Monotonic — once confirmed, never regresses."""

    metrics: MeddicCriterion = Field(default_factory=MeddicCriterion)
    economic_buyer: MeddicCriterion = Field(default_factory=MeddicCriterion)
    decision_criteria: MeddicCriterion = Field(default_factory=MeddicCriterion)
    decision_process: MeddicCriterion = Field(default_factory=MeddicCriterion)
    identify_pain: MeddicCriterion = Field(default_factory=MeddicCriterion)
    champion: MeddicCriterion = Field(default_factory=MeddicCriterion)

    def score(self) -> int:
        return sum(self.values())

    def values(self) -> list[bool]:
        return [
            self.metrics.confirmed, self.economic_buyer.confirmed,
            self.decision_criteria.confirmed, self.decision_process.confirmed,
            self.identify_pain.confirmed, self.champion.confirmed,
        ]

    def criteria(self) -> list[MeddicCriterion]:
        return [
            self.metrics, self.economic_buyer, self.decision_criteria,
            self.decision_process, self.identify_pain, self.champion,
        ]

    def gaps(self) -> list[str]:
        return [n for v, n in zip(self.values(), MEDDIC_CRITERION_NAMES, strict=True) if not v]

    def to_score(self) -> MeddicScore:
        return MeddicScore(
            metrics=self.metrics.confirmed,
            economic_buyer=self.economic_buyer.confirmed,
            decision_criteria=self.decision_criteria.confirmed,
            decision_process=self.decision_process.confirmed,
            identify_pain=self.identify_pain.confirmed,
            champion=self.champion.confirmed,
        )

    def update_from_score(self, score: MeddicScore, evidence: str) -> None:
        """Update from LLM's bool-only MeddicScore. Only flips false→true."""
        if score.metrics:
            self.metrics.confirm(evidence)
        if score.economic_buyer:
            self.economic_buyer.confirm(evidence)
        if score.decision_criteria:
            self.decision_criteria.confirm(evidence)
        if score.decision_process:
            self.decision_process.confirm(evidence)
        if score.identify_pain:
            self.identify_pain.confirm(evidence)
        if score.champion:
            self.champion.confirm(evidence)


# =============================================================================
# Models — DISC
# =============================================================================


class BuyerDisc(BaseModel):
    """DISC buyer profile. Monotonic — only updates on first detection or higher confidence."""

    disc_type: DiscType = DiscType.UNKNOWN
    confidence: DiscConfidence = DiscConfidence.LOW
    signals: str = ""

    def merge_higher(self, incoming: BuyerDisc) -> None:
        """Merge incoming DISC. Only update on first detection or strictly higher confidence.
        Prevents flicker when equal-confidence types alternate.
        """
        if incoming.disc_type != DiscType.UNKNOWN:
            incoming_level = incoming.confidence.level
            current_level = self.confidence.level
            if self.disc_type == DiscType.UNKNOWN or incoming_level > current_level:
                self.disc_type = incoming.disc_type
                self.confidence = incoming.confidence
                self.signals = incoming.signals


# =============================================================================
# Models — Partner Progress (channel mode)
# =============================================================================


class PartnerProgress(BaseModel):
    """Channel partner progress tracking — replaces MEDDIC for integrator conversations.
    All fields monotonically increasing.
    """

    product_familiarity: PartnerFamiliarity = PartnerFamiliarity.UNKNOWN
    active_projects: int = 0
    displacement_opportunities: list[str] = Field(default_factory=list)
    spec_in_status: SpecInStatus = SpecInStatus.NONE
    margin_discussed: bool = False
    certification_interest: bool = False

    LABELS: ClassVar[list[str]] = PARTNER_CRITERION_LABELS
    NAMES: ClassVar[list[str]] = PARTNER_CRITERION_NAMES

    def score(self) -> int:
        return sum(self.field_values())

    def field_values(self) -> list[bool]:
        return [
            self.product_familiarity.level >= 1,
            self.active_projects > 0,
            len(self.displacement_opportunities) > 0,
            self.spec_in_status.level >= 1,
            self.margin_discussed,
            self.certification_interest,
        ]

    def gaps(self) -> list[str]:
        return [n for v, n in zip(self.field_values(), PARTNER_CRITERION_NAMES, strict=True) if not v]

    def merge(self, incoming: PartnerProgress) -> None:
        """Merge incoming progress — only advances, never regresses."""
        self.product_familiarity = self.product_familiarity.merge_higher(
            incoming.product_familiarity
        )
        if incoming.active_projects > self.active_projects:
            self.active_projects = incoming.active_projects
        for opp in incoming.displacement_opportunities:
            if len(self.displacement_opportunities) < 8 and opp not in self.displacement_opportunities:
                self.displacement_opportunities.append(opp)
        self.spec_in_status = self.spec_in_status.merge_higher(incoming.spec_in_status)
        if incoming.margin_discussed:
            self.margin_discussed = True
        if incoming.certification_interest:
            self.certification_interest = True


# =============================================================================
# Models — Cross-call context
# =============================================================================


class CallHistoryEntry(BaseModel):
    """Single call history entry for cross-call context building."""

    id: str
    date: str
    duration: int | None = None
    stage_reached: str | None = None
    summary: str | None = None
    key_topics: list[str] | None = None


class CrossCallContext(BaseModel):
    """Context from previous calls with the same lead."""

    confirmed_pains: list[str] = Field(default_factory=list)
    open_commitments: list[str] = Field(default_factory=list)
    unresolved_objections: list[str] = Field(default_factory=list)
    recurring_topics: list[str] = Field(default_factory=list)
    last_stage_reached: str | None = None
    total_previous_calls: int = 0


# =============================================================================
# Models — LLM structured output
# =============================================================================


class CurrentState(BaseModel):
    """Current call state snapshot — LLM structured output."""

    call_stage: CallStage = CallStage.OPENING
    customer_sentiment: CustomerSentiment = CustomerSentiment.NEUTRAL
    topic_being_discussed: str = ""
    customer_pain_point: str | None = None
    next_goal: NextGoal = NextGoal.DISCOVER_PAIN
    prospect_company_guess: str | None = None
    meddic: MeddicScore = Field(default_factory=MeddicScore)
    buyer_disc: BuyerDisc = Field(default_factory=BuyerDisc)
    rep_followed_coaching: bool | None = None


class CoachingResponse(BaseModel):
    """Coaching output from the LLM — what to show the rep."""

    coaching_type: CoachingType = CoachingType.WHISPER
    urgency: CoachingUrgency = CoachingUrgency.MEDIUM
    focus: CoachingFocus = CoachingFocus.ASK_QUESTION
    response: str = ""
    rationale: str = ""
    suggested_question: str | None = None
    product_hint: str | None = None
    objection_type: ObjectionType = ObjectionType.NONE
    booking_signal: BookingSignal = BookingSignal.NONE
    summary_update: str = ""
    topics_added: list[str] = Field(default_factory=list)
    objections_added: list[str] = Field(default_factory=list)


# =============================================================================
# Models — Accumulated state
# =============================================================================


class AccumulatedState(BaseModel):
    """Accumulated state tracked across turns. Monotonic: MEDDIC false→true, DISC confidence-only."""

    meddic: MeddicTracker = Field(default_factory=MeddicTracker)
    disc: BuyerDisc = Field(default_factory=BuyerDisc)
    partner: PartnerProgress = Field(default_factory=PartnerProgress)

    def update_from_current_state(self, cs: CurrentState, evidence: str) -> None:
        """Update MEDDIC and DISC from a CurrentState snapshot."""
        self.meddic.update_from_score(cs.meddic, evidence)
        self.disc.merge_higher(cs.buyer_disc)
