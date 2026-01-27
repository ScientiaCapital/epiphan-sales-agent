"""Tests for Persona Matcher service.

TDD tests for matching leads to buyer personas using title and company signals.
"""

import pytest

from app.services.scoring.persona_matcher import PersonaMatch, PersonaMatcher


class TestPersonaMatcher:
    """Tests for PersonaMatcher service."""

    @pytest.fixture
    def matcher(self):
        """Create PersonaMatcher instance."""
        return PersonaMatcher()

    # =========================================================================
    # Exact Title Matches
    # =========================================================================

    def test_exact_title_match_av_director(self, matcher):
        """Test exact match for AV Director."""
        result = matcher.match_persona(title="AV Director", company="State University")

        assert isinstance(result, PersonaMatch)
        assert result.persona_id == "av_director"
        assert result.confidence >= 0.9  # High confidence for exact match

    def test_exact_title_match_ld_director(self, matcher):
        """Test exact match for L&D Director."""
        result = matcher.match_persona(title="L&D Director", company="TechCorp Inc")

        assert result.persona_id == "ld_director"
        assert result.confidence >= 0.9

    def test_exact_title_match_simulation_director(self, matcher):
        """Test exact match for Simulation Center Director."""
        result = matcher.match_persona(
            title="Simulation Center Director", company="Medical University"
        )

        assert result.persona_id == "simulation_director"
        assert result.confidence >= 0.9

    # =========================================================================
    # Title Variation Matches
    # =========================================================================

    def test_title_variation_av_manager(self, matcher):
        """Test title variation for AV Director persona."""
        result = matcher.match_persona(
            title="AV Manager", company="Community College"
        )

        assert result.persona_id == "av_director"
        assert result.confidence >= 0.8

    def test_title_variation_classroom_technology_manager(self, matcher):
        """Test title variation for AV Director persona."""
        result = matcher.match_persona(
            title="Classroom Technology Manager", company="University of Example"
        )

        assert result.persona_id == "av_director"
        assert result.confidence >= 0.8

    def test_title_variation_chief_learning_officer(self, matcher):
        """Test title variation for L&D Director persona."""
        result = matcher.match_persona(
            title="Chief Learning Officer", company="Fortune 500 Company"
        )

        assert result.persona_id == "ld_director"
        assert result.confidence >= 0.8

    def test_title_variation_training_director(self, matcher):
        """Test title variation for L&D Director persona."""
        result = matcher.match_persona(
            title="Training Director", company="Manufacturing Corp"
        )

        assert result.persona_id == "ld_director"
        assert result.confidence >= 0.8

    def test_title_variation_media_director(self, matcher):
        """Test title variation for Technical Director persona."""
        result = matcher.match_persona(
            title="Media Director", company="First Baptist Church"
        )

        assert result.persona_id == "technical_director"
        assert result.confidence >= 0.8

    # =========================================================================
    # Partial/Fuzzy Title Matches
    # =========================================================================

    def test_partial_title_match_director_av(self, matcher):
        """Test partial match with 'Director of AV Services'."""
        result = matcher.match_persona(
            title="Director of AV Services", company="State College"
        )

        assert result.persona_id == "av_director"
        assert result.confidence >= 0.7

    def test_partial_title_match_vp_learning_development(self, matcher):
        """Test partial match with VP title."""
        result = matcher.match_persona(
            title="VP of Talent Development", company="Enterprise Corp"
        )

        assert result.persona_id == "ld_director"
        assert result.confidence >= 0.7

    def test_fuzzy_match_case_insensitive(self, matcher):
        """Test that matching is case insensitive."""
        result = matcher.match_persona(
            title="av director", company="University"
        )

        assert result.persona_id == "av_director"
        assert result.confidence >= 0.9

    def test_fuzzy_match_with_extra_words(self, matcher):
        """Test matching with extra words in title."""
        result = matcher.match_persona(
            title="Senior AV Director & Technology Lead", company="University"
        )

        assert result.persona_id == "av_director"
        assert result.confidence >= 0.6

    # =========================================================================
    # All Persona Type Matches
    # =========================================================================

    def test_match_technical_director(self, matcher):
        """Test matching Technical Director."""
        result = matcher.match_persona(
            title="Production Director", company="Mega Church"
        )
        assert result.persona_id == "technical_director"

    def test_match_court_administrator(self, matcher):
        """Test matching Court Administrator."""
        result = matcher.match_persona(
            title="Court Administrator", company="County Court"
        )
        assert result.persona_id == "court_administrator"

    def test_match_clerk_of_court(self, matcher):
        """Test matching Court Administrator via Clerk of Court."""
        result = matcher.match_persona(
            title="Clerk of Court", company="District Court"
        )
        assert result.persona_id == "court_administrator"

    def test_match_corp_comms_director(self, matcher):
        """Test matching Corp Comms Director."""
        result = matcher.match_persona(
            title="VP of Corporate Communications", company="Tech Giant"
        )
        assert result.persona_id == "corp_comms_director"

    def test_match_ehs_manager(self, matcher):
        """Test matching EHS Manager."""
        result = matcher.match_persona(
            title="Safety Manager", company="Manufacturing Plant"
        )
        assert result.persona_id == "ehs_manager"

    def test_match_law_firm_it(self, matcher):
        """Test matching Law Firm IT Director."""
        result = matcher.match_persona(
            title="Director of Information Technology", company="Smith & Associates LLP"
        )
        assert result.persona_id == "law_firm_it"

    # =========================================================================
    # No Match Cases
    # =========================================================================

    def test_no_match_generic_title(self, matcher):
        """Test no match for generic title."""
        result = matcher.match_persona(
            title="Software Engineer", company="Tech Company"
        )

        assert result.persona_id is None
        assert result.confidence < 0.5

    def test_no_match_empty_title(self, matcher):
        """Test handling of empty title."""
        result = matcher.match_persona(title="", company="Some Company")

        assert result.persona_id is None
        assert result.confidence == 0.0

    def test_no_match_none_title(self, matcher):
        """Test handling of None title."""
        result = matcher.match_persona(title=None, company="Some Company")

        assert result.persona_id is None
        assert result.confidence == 0.0

    # =========================================================================
    # Company/Vertical Inference
    # =========================================================================

    def test_vertical_inference_university(self, matcher):
        """Test vertical inference from university company name."""
        result = matcher.match_persona(
            title="IT Manager", company="Stanford University"
        )

        # Even with non-matching title, should suggest higher_ed vertical
        assert result.inferred_vertical == "higher_ed"

    def test_vertical_inference_hospital(self, matcher):
        """Test vertical inference from hospital company name."""
        result = matcher.match_persona(
            title="Director", company="Johns Hopkins Hospital"
        )

        assert result.inferred_vertical == "healthcare"

    def test_vertical_inference_church(self, matcher):
        """Test vertical inference from church company name."""
        result = matcher.match_persona(
            title="Director", company="First Baptist Church"
        )

        assert result.inferred_vertical == "house_of_worship"

    def test_vertical_inference_law_firm(self, matcher):
        """Test vertical inference from law firm company name."""
        result = matcher.match_persona(
            title="IT Manager", company="Baker McKenzie LLP"
        )

        assert result.inferred_vertical == "legal"

    def test_vertical_inference_government(self, matcher):
        """Test vertical inference from government organization."""
        result = matcher.match_persona(
            title="Director", company="City of Austin"
        )

        assert result.inferred_vertical == "government"

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_multiple_possible_matches_picks_highest(self, matcher):
        """Test that the best match is selected when multiple could apply."""
        # "Director of Technology" could match multiple personas
        result = matcher.match_persona(
            title="Director of Technology", company="University"
        )

        # Should return the best match based on scoring
        assert result.persona_id is not None or result.confidence < 0.5

    def test_company_context_boosts_confidence(self, matcher):
        """Test that company context can boost match confidence."""
        # AV Manager at a university should be higher confidence
        university_result = matcher.match_persona(
            title="AV Manager", company="State University"
        )
        generic_result = matcher.match_persona(
            title="AV Manager", company="Random Corp"
        )

        # University context should boost confidence for av_director
        assert university_result.confidence >= generic_result.confidence
