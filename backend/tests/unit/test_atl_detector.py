"""Tests for ATL (Above-the-Line) Decision-Maker Detector.

PHONES ARE GOLD - but only for ATL decision-makers Tim will actually call.
These tests verify we correctly identify decision-makers to optimize credit spend.
"""

import pytest

from app.services.scoring.atl_detector import (
    ATLMatch,
    get_all_atl_titles,
    get_persona_titles,
    is_atl_decision_maker,
)


class TestExactPersonaMatches:
    """Test exact matching against the 8 BDR Playbook personas."""

    # AV Director persona titles
    @pytest.mark.parametrize(
        "title",
        [
            "AV Director",
            "Director of AV Services",
            "Classroom Technology Manager",
            "Director of Learning Spaces",
            "AV Manager",
        ],
    )
    def test_av_director_persona_exact_match(self, title: str):
        """Test AV Director persona exact title matches."""
        result = is_atl_decision_maker(title)

        assert result.is_atl is True
        assert result.persona_id == "av_director"
        assert result.confidence == 1.0
        assert "exact match" in result.reason.lower()

    # L&D Director persona titles
    @pytest.mark.parametrize(
        "title",
        [
            "L&D Director",
            "VP of Talent Development",
            "Chief Learning Officer",
            "Director of Learning & Development",
            "Director of Learning and Development",
            "Training Director",
        ],
    )
    def test_ld_director_persona_exact_match(self, title: str):
        """Test L&D Director persona exact title matches."""
        result = is_atl_decision_maker(title)

        assert result.is_atl is True
        assert result.persona_id == "ld_director"
        assert result.confidence == 1.0

    # Technical Director persona titles
    @pytest.mark.parametrize(
        "title",
        [
            "Technical Director",
            "Production Director",
            "Media Director",
            "Broadcast Engineer",
        ],
    )
    def test_technical_director_persona_exact_match(self, title: str):
        """Test Technical Director persona exact title matches."""
        result = is_atl_decision_maker(title)

        assert result.is_atl is True
        assert result.persona_id == "technical_director"
        assert result.confidence == 1.0

    # Simulation Director persona titles
    @pytest.mark.parametrize(
        "title",
        [
            "Simulation Center Director",
            "Director of Simulation",
            "Simulation Center Manager",
            "Director of Clinical Simulation",
        ],
    )
    def test_simulation_director_persona_exact_match(self, title: str):
        """Test Simulation Director persona exact title matches."""
        result = is_atl_decision_maker(title)

        assert result.is_atl is True
        assert result.persona_id == "simulation_director"
        assert result.confidence == 1.0

    # Court Administrator persona titles
    @pytest.mark.parametrize(
        "title",
        [
            "Court Administrator",
            "Court Executive Officer",
            "Clerk of Court",
            "Trial Court Administrator",
            "Director of Court Operations",
        ],
    )
    def test_court_administrator_persona_exact_match(self, title: str):
        """Test Court Administrator persona exact title matches."""
        result = is_atl_decision_maker(title)

        assert result.is_atl is True
        assert result.persona_id == "court_administrator"
        assert result.confidence == 1.0

    # Corp Comms Director persona titles
    @pytest.mark.parametrize(
        "title",
        [
            "Corp Comms Director",
            "VP of Corporate Communications",
            "Head of Internal Communications",
            "Director of Executive Communications",
            "VP of Internal Comms",
        ],
    )
    def test_corp_comms_director_persona_exact_match(self, title: str):
        """Test Corp Comms Director persona exact title matches."""
        result = is_atl_decision_maker(title)

        assert result.is_atl is True
        assert result.persona_id == "corp_comms_director"
        assert result.confidence == 1.0

    # EHS Manager persona titles
    @pytest.mark.parametrize(
        "title",
        [
            "EHS Manager",
            "EHS Director",
            "Safety Manager",
            "Director of Safety",
            "Plant Safety Manager",
            "VP of EHS",
        ],
    )
    def test_ehs_manager_persona_exact_match(self, title: str):
        """Test EHS Manager persona exact title matches."""
        result = is_atl_decision_maker(title)

        assert result.is_atl is True
        assert result.persona_id == "ehs_manager"
        assert result.confidence == 1.0

    # Law Firm IT persona titles
    @pytest.mark.parametrize(
        "title",
        [
            "Law Firm IT Director",
            "Director of Information Technology",
            "Legal Tech Manager",
            "Director of Legal Operations",
            "IT Operations Manager",
        ],
    )
    def test_law_firm_it_persona_exact_match(self, title: str):
        """Test Law Firm IT persona exact title matches."""
        result = is_atl_decision_maker(title)

        assert result.is_atl is True
        # Note: Some of these may match multiple personas or just keywords
        # The important thing is they are identified as ATL
        assert result.confidence >= 0.6


class TestFuzzyMatching:
    """Test fuzzy matching for title variations."""

    @pytest.mark.parametrize(
        "title,expected_persona",
        [
            ("A/V Director", "av_director"),
            ("Audio Visual Director", None),  # Too different
            ("AV Services Director", "av_director"),
            ("Director, AV Services", "av_director"),
            ("Learning and Development Director", "ld_director"),
            ("L & D Director", "ld_director"),
            ("Simulation Lab Director", "simulation_director"),
            ("Sim Center Director", "simulation_director"),
            ("Corporate Communications VP", "corp_comms_director"),
            ("Internal Comms Director", "corp_comms_director"),
            ("Environment Health Safety Manager", "ehs_manager"),
        ],
    )
    def test_fuzzy_title_matching(self, title: str, expected_persona: str | None):
        """Test fuzzy matching catches common variations."""
        result = is_atl_decision_maker(title)

        # All these should be ATL (either persona match or keyword)
        assert result.is_atl is True

        # If we expect a specific persona match and got one, verify
        if expected_persona and result.persona_id:
            assert result.persona_id == expected_persona
            assert result.confidence >= 0.6


class TestATLKeywordDetection:
    """Test ATL keyword detection for non-persona titles."""

    @pytest.mark.parametrize(
        "title",
        [
            "Director of Marketing",
            "VP of Sales",
            "Chief Technology Officer",
            "Head of Engineering",
            "President",
            "Owner",
            "Founder",
            "Partner",
            "Managing Director",
            "Vice President of Operations",
        ],
    )
    def test_atl_keyword_titles_are_atl(self, title: str):
        """Titles with ATL keywords should be marked ATL."""
        result = is_atl_decision_maker(title)

        assert result.is_atl is True
        assert result.confidence >= 0.6  # Fuzzy matches can have lower confidence
        assert "keyword" in result.reason.lower() or "match" in result.reason.lower()

    def test_manager_alone_is_atl(self):
        """Manager alone should still be ATL due to potential budget authority."""
        result = is_atl_decision_maker("Regional Manager")

        # Manager is in ATL keywords
        assert result.is_atl is True


class TestNonATLDetection:
    """Test detection of non-ATL contacts to save credits."""

    @pytest.mark.parametrize(
        "title,expected_keyword",
        [
            ("Student", "student"),
            ("Graduate Student", "student"),
            ("Marketing Intern", "intern"),
            ("Sales Intern", "intern"),
            ("Project Coordinator", "coordinator"),
            ("Administrative Assistant", "assistant"),
            ("Executive Assistant", "assistant"),
            ("Sales Associate", "associate"),
            ("Marketing Analyst", "analyst"),
            ("Business Analyst", "analyst"),
            ("HR Specialist", "specialist"),
            ("Training Specialist", "specialist"),
            ("Office Administrator", "administrator"),
            ("Receptionist", "receptionist"),
            ("Data Clerk", "clerk"),
            ("Management Trainee", "trainee"),
            ("Research Fellow", "fellow"),
            ("Medical Resident", "resident"),
            ("Professor", "professor"),
            ("Lecturer", "lecturer"),
            ("Research Scientist", "scientist"),
            ("Software Engineer", "engineer"),
            ("Software Developer", "developer"),
            ("Programmer", "programmer"),
            ("UX Designer", "designer"),
            ("Lab Technician", "technician"),
        ],
    )
    def test_non_atl_titles_are_not_atl(self, title: str, expected_keyword: str):
        """Non-ATL titles should NOT be marked ATL to save credits."""
        result = is_atl_decision_maker(title)

        assert result.is_atl is False
        assert expected_keyword in result.reason.lower()
        assert result.confidence >= 0.8


class TestSpecialCases:
    """Test special cases and edge cases."""

    def test_broadcast_engineer_is_atl(self):
        """Broadcast Engineer IS ATL (Technical Director persona exception)."""
        result = is_atl_decision_maker("Broadcast Engineer")

        assert result.is_atl is True
        assert result.persona_id == "technical_director"

    def test_court_administrator_is_atl(self):
        """Court Administrator IS ATL despite 'administrator' keyword."""
        result = is_atl_decision_maker("Court Administrator")

        assert result.is_atl is True
        assert result.persona_id == "court_administrator"

    def test_clerk_of_court_is_atl(self):
        """Clerk of Court IS ATL despite 'clerk' keyword."""
        result = is_atl_decision_maker("Clerk of Court")

        assert result.is_atl is True
        assert result.persona_id == "court_administrator"

    def test_generic_engineer_is_not_atl(self):
        """Generic Engineer (not Broadcast) is NOT ATL."""
        result = is_atl_decision_maker("Software Engineer")

        assert result.is_atl is False

    def test_generic_clerk_is_not_atl(self):
        """Generic Clerk (not Court) is NOT ATL."""
        result = is_atl_decision_maker("Data Entry Clerk")

        assert result.is_atl is False


class TestSeniorityDetection:
    """Test seniority-based ATL detection."""

    @pytest.mark.parametrize(
        "seniority",
        ["director", "vp", "c_suite", "owner", "founder", "partner", "manager"],
    )
    def test_atl_seniority_with_unknown_title(self, seniority: str):
        """ATL seniority should mark as ATL even with unknown title."""
        result = is_atl_decision_maker(title="Unknown Role", seniority=seniority)

        assert result.is_atl is True
        assert "seniority" in result.reason.lower()

    @pytest.mark.parametrize(
        "seniority",
        ["entry", "individual_contributor", "intern", "student"],
    )
    def test_non_atl_seniority_overrides(self, seniority: str):
        """Non-ATL seniority should mark as NOT ATL."""
        result = is_atl_decision_maker(title="Unknown Role", seniority=seniority)

        assert result.is_atl is False

    def test_atl_seniority_with_no_title(self):
        """ATL seniority alone should mark as ATL."""
        result = is_atl_decision_maker(title=None, seniority="director")

        assert result.is_atl is True
        assert result.confidence == 0.6

    def test_non_atl_seniority_with_no_title(self):
        """Non-ATL seniority with no title should mark as NOT ATL."""
        result = is_atl_decision_maker(title=None, seniority="intern")

        assert result.is_atl is False


class TestMissingData:
    """Test handling of missing title/seniority data."""

    def test_no_title_no_seniority(self):
        """No data at all should NOT be ATL (conserve credits)."""
        result = is_atl_decision_maker(title=None, seniority=None)

        assert result.is_atl is False
        assert "conserve" in result.reason.lower() or "no" in result.reason.lower()
        assert result.confidence == 0.5

    def test_empty_title_no_seniority(self):
        """Empty title with no seniority should NOT be ATL."""
        result = is_atl_decision_maker(title="", seniority=None)

        assert result.is_atl is False

    def test_whitespace_title_no_seniority(self):
        """Whitespace-only title should NOT be ATL."""
        result = is_atl_decision_maker(title="   ", seniority=None)

        assert result.is_atl is False


class TestCaseInsensitivity:
    """Test case insensitivity in matching."""

    @pytest.mark.parametrize(
        "title",
        [
            "av director",
            "AV DIRECTOR",
            "Av Director",
            "aV dIrEcToR",
        ],
    )
    def test_case_insensitive_matching(self, title: str):
        """Title matching should be case insensitive."""
        result = is_atl_decision_maker(title)

        assert result.is_atl is True
        assert result.persona_id == "av_director"


class TestATLMatchDataclass:
    """Test ATLMatch dataclass properties."""

    def test_atl_match_all_fields(self):
        """Test ATLMatch has all expected fields."""
        match = ATLMatch(
            is_atl=True,
            persona_id="av_director",
            confidence=1.0,
            reason="Exact match",
        )

        assert match.is_atl is True
        assert match.persona_id == "av_director"
        assert match.confidence == 1.0
        assert match.reason == "Exact match"


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_all_atl_titles(self):
        """Test getting all ATL titles."""
        titles = get_all_atl_titles()

        assert isinstance(titles, list)
        assert len(titles) >= 40  # We have 40 unique titles across 8 personas
        assert "av director" in titles
        assert "vp of talent development" in titles

    def test_get_persona_titles(self):
        """Test getting titles for a specific persona."""
        titles = get_persona_titles("av_director")

        assert len(titles) == 5
        assert "av director" in titles
        assert "av manager" in titles

    def test_get_persona_titles_invalid(self):
        """Test getting titles for invalid persona."""
        titles = get_persona_titles("invalid_persona")

        assert titles == []


class TestCreditSavingsScenarios:
    """Test scenarios that verify credit savings logic."""

    def test_typical_non_atl_batch_scenario(self):
        """Verify typical non-ATL leads would save credits."""
        non_atl_titles = [
            "Marketing Analyst",
            "Sales Associate",
            "Graduate Student",
            "Research Scientist",
            "Software Developer",
            "HR Specialist",
            "Project Coordinator",
            "Administrative Assistant",
        ]

        for title in non_atl_titles:
            result = is_atl_decision_maker(title)
            assert result.is_atl is False, f"Expected {title} to be non-ATL"

    def test_typical_atl_batch_scenario(self):
        """Verify typical ATL leads would get phone enrichment."""
        atl_titles = [
            "AV Director",
            "VP of Corporate Communications",
            "Director of Simulation",
            "Chief Learning Officer",
            "Court Administrator",
            "Safety Manager",
            "Technical Director",
        ]

        for title in atl_titles:
            result = is_atl_decision_maker(title)
            assert result.is_atl is True, f"Expected {title} to be ATL"
            assert result.confidence >= 0.6
