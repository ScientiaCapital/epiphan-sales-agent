"""Persona Matcher service for matching leads to buyer personas.

Uses title variations and company context to match leads to one of the 8
buyer personas with a confidence score.
"""

import re
from dataclasses import dataclass

from app.data.personas import PERSONAS


@dataclass
class PersonaMatch:
    """Result of persona matching."""

    persona_id: str | None
    confidence: float  # 0.0 to 1.0
    matched_title: str | None = None
    inferred_vertical: str | None = None


# Vertical inference patterns (company name → vertical)
VERTICAL_PATTERNS: dict[str, list[str]] = {
    "higher_ed": [
        r"\buniversity\b",
        r"\bcollege\b",
        r"\bschool\b",
        r"\bacademy\b",
        r"\binstitute\b",
        r"\beducation\b",
        r"\bseminary\b",
    ],
    "healthcare": [
        r"\bhospital\b",
        r"\bmedical\b",
        r"\bclinic\b",
        r"\bhealth\b",
        r"\bpharma\b",
        r"\bbiotech\b",
        r"\bsurgical\b",
        r"\bdiagnostic\b",
    ],
    "house_of_worship": [
        r"\bchurch\b",
        r"\btemple\b",
        r"\bmosque\b",
        r"\bsynagogue\b",
        r"\bministr(y|ies)\b",
        r"\bworship\b",
        r"\bfaith\b",
        r"\breligious\b",
        r"\bcathedral\b",
        r"\bparish\b",
    ],
    "government": [
        r"\bcity of\b",
        r"\bcounty\b",
        r"\bstate of\b",
        r"\bfederal\b",
        r"\bgovernment\b",
        r"\bmunicipal\b",
        r"\bpublic\b",
        r"\bcourt\b",
    ],
    "legal": [
        r"\bllp\b",
        r"\blaw\s*(firm|office|group)\b",
        r"\battorney\b",
        r"\blegal\b",
        r"\b&\s*associates\b",
        r"\bpartners\b",
    ],
    "live_events": [
        r"\bevent(s)?\b",
        r"\bproduction(s)?\b",
        r"\bstadium\b",
        r"\barena\b",
        r"\btheater\b",
        r"\btheatre\b",
        r"\bvenue\b",
        r"\bconcert\b",
    ],
    "corporate": [
        r"\binc\b",
        r"\bcorp\b",
        r"\bllc\b",
        r"\bltd\b",
        r"\bcompany\b",
        r"\bglobal\b",
        r"\benterprise\b",
    ],
    "industrial": [
        r"\bmanufacturing\b",
        r"\bplant\b",
        r"\bfactor(y|ies)\b",
        r"\bindustrial\b",
        r"\bproduction\b",
        r"\bassembly\b",
        r"\bwarehouse\b",
    ],
}


class PersonaMatcher:
    """
    Service for matching leads to buyer personas.

    Uses a combination of:
    1. Exact title matching
    2. Title variation matching
    3. Fuzzy/partial title matching
    4. Company/vertical context inference

    Returns a PersonaMatch with persona_id and confidence score (0-1).
    """

    def __init__(self) -> None:
        """Initialize matcher with persona data."""
        self.personas = PERSONAS
        self._build_title_index()

    def _build_title_index(self) -> None:
        """Build an index of titles and variations for fast lookup."""
        self.title_to_persona: dict[str, tuple[str, float]] = {}

        for persona in self.personas:
            # Primary title - highest confidence
            primary_title = persona.title.lower()
            self.title_to_persona[primary_title] = (persona.id, 1.0)

            # Title variations - slightly lower confidence
            for variation in persona.title_variations:
                var_lower = variation.lower()
                self.title_to_persona[var_lower] = (persona.id, 0.95)

    def match_persona(
        self,
        title: str | None,
        company: str | None = None,
        industry: str | None = None,
    ) -> PersonaMatch:
        """
        Match a lead to a buyer persona.

        Args:
            title: Job title from the lead
            company: Company name for vertical inference
            industry: Industry for additional context

        Returns:
            PersonaMatch with persona_id, confidence, and inferred_vertical
        """
        # Handle empty/None title
        if not title or not title.strip():
            inferred_vertical = self._infer_vertical(company, industry)
            return PersonaMatch(
                persona_id=None,
                confidence=0.0,
                matched_title=None,
                inferred_vertical=inferred_vertical,
            )

        title_lower = title.lower().strip()

        # Try exact match first
        if title_lower in self.title_to_persona:
            persona_id, base_confidence = self.title_to_persona[title_lower]
            inferred_vertical = self._infer_vertical(company, industry)

            # Boost confidence if company matches persona's verticals
            confidence = self._apply_vertical_boost(
                base_confidence, persona_id, inferred_vertical
            )

            return PersonaMatch(
                persona_id=persona_id,
                confidence=confidence,
                matched_title=title,
                inferred_vertical=inferred_vertical,
            )

        # Try fuzzy matching
        best_match = self._fuzzy_match(title_lower)
        inferred_vertical = self._infer_vertical(company, industry)

        if best_match:
            persona_id, confidence, matched_title = best_match
            confidence = self._apply_vertical_boost(
                confidence, persona_id, inferred_vertical
            )
            return PersonaMatch(
                persona_id=persona_id,
                confidence=confidence,
                matched_title=matched_title,
                inferred_vertical=inferred_vertical,
            )

        # No match found
        return PersonaMatch(
            persona_id=None,
            confidence=0.0,
            matched_title=None,
            inferred_vertical=inferred_vertical,
        )

    def _fuzzy_match(
        self, title_lower: str
    ) -> tuple[str, float, str] | None:
        """
        Perform fuzzy matching on title.

        Returns tuple of (persona_id, confidence, matched_title) or None.
        """
        best_match: tuple[str, float, str] | None = None
        best_score = 0.0

        for persona in self.personas:
            # Check against primary title
            score = self._calculate_similarity(title_lower, persona.title.lower())
            if score > best_score and score >= 0.5:
                best_score = score
                best_match = (persona.id, score, persona.title)

            # Check against title variations
            for variation in persona.title_variations:
                var_lower = variation.lower()
                score = self._calculate_similarity(title_lower, var_lower)
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_match = (persona.id, score * 0.95, variation)  # Slight penalty for variation

        return best_match

    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity score between two titles.

        Uses a combination of:
        - Contains check
        - Word overlap
        - Key term matching
        """
        # Exact match
        if title1 == title2:
            return 1.0

        # Contains check (partial match)
        if title2 in title1 or title1 in title2:
            shorter = min(len(title1), len(title2))
            longer = max(len(title1), len(title2))
            return 0.7 + (0.3 * (shorter / longer))

        # Word overlap
        words1 = set(title1.split())
        words2 = set(title2.split())

        # Remove common filler words
        filler_words = {"of", "the", "and", "&", "a", "an", "for", "in", "at"}
        words1 = words1 - filler_words
        words2 = words2 - filler_words

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        # Jaccard similarity with boost for key terms
        jaccard = len(intersection) / len(union)

        # Boost for matching key role terms
        key_terms = {
            "director", "manager", "vp", "chief", "head", "lead",
            "av", "l&d", "learning", "training", "simulation",
            "court", "safety", "ehs", "communications", "comms",
            "technical", "production", "media", "it"
        }
        key_matches = intersection.intersection(key_terms)

        if key_matches:
            jaccard += 0.2 * len(key_matches)

        return min(jaccard, 1.0)

    def _infer_vertical(
        self, company: str | None, industry: str | None
    ) -> str | None:
        """
        Infer vertical from company name and/or industry.

        Args:
            company: Company name
            industry: Industry classification (if available)

        Returns:
            Inferred vertical string or None
        """
        if not company and not industry:
            return None

        text = ((company or "") + " " + (industry or "")).lower()

        for vertical, patterns in VERTICAL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return vertical

        return None

    def _apply_vertical_boost(
        self,
        base_confidence: float,
        persona_id: str,
        inferred_vertical: str | None,
    ) -> float:
        """
        Apply confidence boost if vertical matches persona.

        Args:
            base_confidence: Base confidence score
            persona_id: Matched persona ID
            inferred_vertical: Inferred vertical from company

        Returns:
            Adjusted confidence score
        """
        if not inferred_vertical:
            return base_confidence

        # Find the persona
        persona = next((p for p in self.personas if p.id == persona_id), None)
        if not persona:
            return base_confidence

        # Check if inferred vertical is in persona's target verticals
        # Note: PersonaProfile uses use_enum_values=True so verticals are already strings
        persona_verticals = persona.verticals

        if inferred_vertical in persona_verticals:
            # Boost confidence (up to 1.0 max)
            return min(base_confidence + 0.05, 1.0)

        return base_confidence


# Singleton instance
persona_matcher = PersonaMatcher()
