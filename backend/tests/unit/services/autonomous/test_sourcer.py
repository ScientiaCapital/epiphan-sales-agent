"""Tests for lead sourcer."""

from app.services.autonomous.sourcer import LeadSourcer


class TestBuildTitleKeywords:
    def test_returns_comma_separated_titles(self) -> None:
        sourcer = LeadSourcer()
        result = sourcer._build_title_keywords()
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain ATL titles
        parts = result.split(", ")
        assert len(parts) >= 1

    def test_caps_at_20_titles(self) -> None:
        sourcer = LeadSourcer()
        result = sourcer._build_title_keywords()
        parts = result.split(", ")
        assert len(parts) <= 20
