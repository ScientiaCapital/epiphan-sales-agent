"""Product catalog with search — Epiphan Video product families and SKUs.

Ported from souffleur-core/src/products.rs.
Loads product-catalog.json, provides keyword search for prompt injection.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# =============================================================================
# Models
# =============================================================================


class Product(BaseModel):
    """Single product SKU."""

    name: str
    sku: str
    price_usd: float
    note: str = ""


class ProductFamily(BaseModel):
    """Product family (e.g., Pearl-2, Pearl Mini)."""

    id: str
    name: str
    category: str
    tagline: str
    use_cases: list[str] = Field(default_factory=list)
    key_features: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    products: list[Product] = Field(default_factory=list)


class ProductCatalogData(BaseModel):
    """Top-level catalog structure."""

    version: str
    families: list[ProductFamily]


# =============================================================================
# Stopwords
# =============================================================================

_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
    "has", "have", "had", "not", "but", "can", "will", "our", "their", "also",
    "into", "been", "some", "more", "very", "than", "just", "about", "over",
    "such", "after", "all", "its", "http", "https", "www", "com", "company",
    "domain", "contact", "summary", "crm", "pre", "call",
})

_WORD_RE = re.compile(r"[a-zA-Z0-9]+")


def _is_stopword(word: str) -> bool:
    return word.lower() in _STOPWORDS


# =============================================================================
# Product Catalog
# =============================================================================


class ProductCatalog:
    """Searchable product catalog — singleton, loaded from JSON."""

    def __init__(self, data: ProductCatalogData) -> None:
        self._data = data
        # Pre-build lowercased search text for each family (avoids per-query .lower())
        self._search_texts: dict[str, str] = {
            f.id: _build_search_text(f).lower() for f in data.families
        }
        # O(1) family lookup by ID
        self._family_index: dict[str, ProductFamily] = {
            f.id: f for f in data.families
        }

    @staticmethod
    def load_default() -> ProductCatalog:
        """Load from the bundled JSON file."""
        catalog_path = Path(__file__).parent / "product-catalog.json"
        with open(catalog_path) as f:
            raw: dict[str, Any] = json.load(f)
        data = ProductCatalogData(**raw)
        return ProductCatalog(data)

    @property
    def families(self) -> list[ProductFamily]:
        return self._data.families

    @property
    def version(self) -> str:
        return self._data.version

    def product_count(self) -> int:
        return sum(len(f.products) for f in self._data.families)

    def family(self, family_id: str) -> ProductFamily | None:
        """Get family by ID."""
        return self._family_index.get(family_id)

    def by_category(self, category: str) -> list[ProductFamily]:
        """Get all families in a category."""
        return [f for f in self._data.families if f.category == category]

    def search(self, keywords: list[str]) -> list[ProductFamily]:
        """Find families matching any keywords. Sorted by relevance (match count)."""
        if not keywords:
            return []

        kw_lower = [k.lower() for k in keywords]
        scored: list[tuple[ProductFamily, int]] = []

        for family in self._data.families:
            search_text = self._search_texts[family.id]
            score = sum(search_text.count(kw) for kw in kw_lower)
            if score > 0:
                scored.append((family, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [f for f, _ in scored]

    def search_text(self, text: str) -> list[ProductFamily]:
        """Find families relevant to free text. Extracts keywords, skips stopwords."""
        words = [
            w for w in _split_words(text)
            if len(w) >= 2 and not _is_stopword(w)
        ]
        return self.search(words)

    def search_structured(
        self, terms: list[str], context: str | None = None
    ) -> list[ProductFamily]:
        """Structured search: explicit keywords + free text context."""
        all_kw = list(terms)
        if context:
            extra = [
                w for w in _split_words(context)
                if len(w) >= 2 and not _is_stopword(w)
            ]
            all_kw.extend(extra)
        return self.search(all_kw)

    def format_for_prompt(self, families: list[ProductFamily], max_families: int = 4) -> str:
        """Format matched families as concise markdown for prompt injection."""
        lines: list[str] = []
        for f in families[:max_families]:
            lines.append(f"### {f.name}")
            lines.append(f.tagline)
            if f.products:
                prices = [f"- {p.name} — ${p.price_usd:.0f}" for p in f.products]
                lines.append("\n".join(prices))
            if f.key_features:
                feats = ", ".join(f.key_features[:4])
                lines.append(f"Features: {feats}")
            if f.use_cases:
                cases = ", ".join(f.use_cases)
                lines.append(f"Use cases: {cases}")
            if f.competitors:
                comps = ", ".join(f.competitors)
                lines.append(f"Competes with: {comps}")
            lines.append("")
        return "\n".join(lines)

    def relevant_products_prompt(self, context: str, max_families: int = 4) -> str:
        """Search + format in one call. Returns empty string if no matches."""
        matches = self.search_text(context)
        if not matches:
            return ""
        return f"## Relevant Epiphan Products\n\n{self.format_for_prompt(matches, max_families)}"


def _split_words(text: str) -> list[str]:
    """Split text into alphanumeric words."""
    return _WORD_RE.findall(text)


def _build_search_text(family: ProductFamily) -> str:
    """Build searchable text blob with field weighting via repetition."""
    parts: list[str] = []
    # Name 3x weight
    for _ in range(3):
        parts.append(family.name)
    # Product names 2x weight
    for p in family.products:
        parts.append(p.name)
        parts.append(p.name)
    # Competitors 2x weight
    for c in family.competitors:
        parts.append(c)
        parts.append(c)
    # Single weight
    parts.append(family.tagline)
    parts.append(family.category)
    parts.extend(family.use_cases)
    parts.extend(family.key_features)
    return " ".join(parts)


# Module-level singleton — shared by both direct import and get_product_catalog()
product_catalog = ProductCatalog.load_default()


def get_product_catalog() -> ProductCatalog:
    """Get the product catalog singleton."""
    return product_catalog
