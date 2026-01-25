"""Seed data module for Epiphan Sales Agent.

Contains structured data extracted from the BDR Playbook:
- Personas (buyer profiles with discovery questions, objections)
- Competitors (battlecards with positioning)
- Scripts (cold calls, warm inbound)
- Discovery (SPIN framework questions)
- Templates (email, LinkedIn outreach)
- Market Intelligence (trends, pricing, opportunities)
"""

from app.data.competitors import COMPETITORS
from app.data.discovery import DISCOVERY_QUESTIONS, QUALIFICATION_CRITERIA
from app.data.market_intel import MARKET_INTELLIGENCE
from app.data.personas import PERSONAS
from app.data.schemas import (
    ColdCallScript,
    CompetitorBattlecard,
    DiscoveryQuestion,
    EmailTemplate,
    MarketIntelligence,
    PersonaProfile,
    ReferenceStory,
    WarmInboundScript,
)
from app.data.scripts import COLD_CALL_SCRIPTS, WARM_INBOUND_SCRIPTS
from app.data.stories import REFERENCE_STORIES
from app.data.templates import EMAIL_TEMPLATES, LINKEDIN_TEMPLATES

__all__ = [
    # Schemas
    "PersonaProfile",
    "CompetitorBattlecard",
    "ColdCallScript",
    "WarmInboundScript",
    "DiscoveryQuestion",
    "EmailTemplate",
    "ReferenceStory",
    "MarketIntelligence",
    # Data
    "PERSONAS",
    "COMPETITORS",
    "COLD_CALL_SCRIPTS",
    "WARM_INBOUND_SCRIPTS",
    "DISCOVERY_QUESTIONS",
    "QUALIFICATION_CRITERIA",
    "EMAIL_TEMPLATES",
    "LINKEDIN_TEMPLATES",
    "REFERENCE_STORIES",
    "MARKET_INTELLIGENCE",
]
