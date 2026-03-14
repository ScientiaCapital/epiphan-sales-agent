"""Tests for product catalog — loading, search, and prompt formatting."""

import pytest

from app.data.product_catalog import ProductCatalog, product_catalog


# =============================================================================
# Loading
# =============================================================================


class TestProductCatalogLoading:
    def test_loads_and_parses(self) -> None:
        assert len(product_catalog.families) > 0
        assert product_catalog.product_count() > 20

    def test_version_exists(self) -> None:
        assert product_catalog.version

    def test_family_by_id(self) -> None:
        pearl2 = product_catalog.family("pearl-2")
        assert pearl2 is not None
        assert len(pearl2.products) >= 1


# =============================================================================
# Search
# =============================================================================


class TestProductCatalogSearch:
    def test_search_by_keyword(self) -> None:
        results = product_catalog.search(["lecture", "classroom"])
        assert len(results) > 0

    def test_search_ndi(self) -> None:
        results = product_catalog.search(["NDI"])
        assert len(results) > 0
        # Pearl Nexus should be top for NDI
        assert results[0].id == "pearl-nexus"

    def test_search_by_competitor(self) -> None:
        results = product_catalog.search(["Extron"])
        assert len(results) > 0

    def test_search_4k(self) -> None:
        results = product_catalog.search(["4K"])
        assert len(results) > 0

    def test_search_empty_keywords(self) -> None:
        results = product_catalog.search([])
        assert results == []

    def test_search_no_match(self) -> None:
        results = product_catalog.search(["zzz_nonexistent_xyz"])
        assert results == []

    def test_search_text_freeform(self) -> None:
        results = product_catalog.search_text(
            "surgical video capture in hospital, need SDI input"
        )
        assert len(results) > 0

    def test_search_text_stopwords_filtered(self) -> None:
        # "the and for" are stopwords — should still find results from real words
        results = product_catalog.search_text("the and for streaming encoder")
        assert len(results) > 0

    def test_search_structured(self) -> None:
        results = product_catalog.search_structured(
            ["pearl"], context="university lecture capture"
        )
        assert len(results) > 0

    def test_by_category(self) -> None:
        encoders = product_catalog.by_category("encoder")
        assert len(encoders) >= 4


# =============================================================================
# Prompt formatting
# =============================================================================


class TestProductCatalogFormat:
    def test_format_for_prompt(self) -> None:
        results = product_catalog.search(["pearl"])
        formatted = product_catalog.format_for_prompt(results, max_families=2)
        assert "###" in formatted
        assert "$" in formatted

    def test_format_respects_max(self) -> None:
        results = product_catalog.search(["pearl"])
        formatted = product_catalog.format_for_prompt(results, max_families=1)
        # Only one ### header
        assert formatted.count("###") == 1

    def test_relevant_products_prompt(self) -> None:
        prompt = product_catalog.relevant_products_prompt(
            "lecture capture university classroom", max_families=3
        )
        assert prompt.startswith("## Relevant Epiphan Products")
        assert "###" in prompt

    def test_relevant_products_prompt_empty_on_no_match(self) -> None:
        prompt = product_catalog.relevant_products_prompt("zzz_nothing_matches_xyz")
        assert prompt == ""
