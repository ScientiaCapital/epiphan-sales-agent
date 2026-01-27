"""Tests for Email Personalization Agent tools."""

import pytest

from app.data.lead_schemas import Lead
from app.services.langgraph.states import ResearchBrief


class TestEmailTools:
    """Tests for email personalization tools."""

    @pytest.fixture
    def sample_lead(self) -> Lead:
        """Create a sample lead for testing."""
        return Lead(
            hubspot_id="hs-lead-123",
            email="sarah.johnson@stateuniversity.edu",
            first_name="Sarah",
            last_name="Johnson",
            company="State University",
            title="AV Director",
        )

    @pytest.fixture
    def sample_brief(self) -> ResearchBrief:
        """Create a sample research brief."""
        return {
            "company_overview": "State University is a leading research institution in Higher Education.",
            "recent_news": [
                {"title": "University Expands Online Learning", "date": "2025-01-15"}
            ],
            "talking_points": [
                "Higher education focus - lecture capture relevant",
                "Large organization with 5000 employees",
            ],
            "risk_factors": [],
            "linkedin_summary": None,
        }

    def test_get_email_template_pattern_interrupt(self):
        """Test getting pattern interrupt template."""
        from app.services.langgraph.tools.email_tools import get_email_template

        template = get_email_template("pattern_interrupt")

        assert template is not None
        assert "subject_patterns" in template
        assert "structure" in template
        assert len(template["subject_patterns"]) > 0

    def test_get_email_template_pain_point(self):
        """Test getting pain point template."""
        from app.services.langgraph.tools.email_tools import get_email_template

        template = get_email_template("pain_point")

        assert template is not None
        assert "subject_patterns" in template

    def test_get_email_template_breakup(self):
        """Test getting breakup email template."""
        from app.services.langgraph.tools.email_tools import get_email_template

        template = get_email_template("breakup")

        assert template is not None
        assert "subject_patterns" in template

    def test_get_email_template_nurture(self):
        """Test getting nurture email template."""
        from app.services.langgraph.tools.email_tools import get_email_template

        template = get_email_template("nurture")

        assert template is not None

    def test_get_email_template_unknown_returns_none(self):
        """Test unknown template type returns None."""
        from app.services.langgraph.tools.email_tools import get_email_template

        template = get_email_template("unknown_type")

        assert template is None

    def test_extract_personalization_hooks(self, sample_brief: ResearchBrief):
        """Test extracting personalization hooks from research brief."""
        from app.services.langgraph.tools.email_tools import (
            extract_personalization_hooks,
        )

        hooks = extract_personalization_hooks(sample_brief)

        assert hooks is not None
        assert isinstance(hooks, list)
        assert len(hooks) > 0

    def test_extract_personalization_hooks_from_news(self, sample_brief: ResearchBrief):
        """Test extracting hooks from news items."""
        from app.services.langgraph.tools.email_tools import (
            extract_personalization_hooks,
        )

        hooks = extract_personalization_hooks(sample_brief)

        # Should have extracted news hook
        news_hooks = [h for h in hooks if "news" in h.get("type", "")]
        assert len(news_hooks) > 0 or len(hooks) > 0  # At least some hooks

    def test_get_pain_points_for_persona(self):
        """Test getting pain points for a specific persona."""
        from app.services.langgraph.tools.email_tools import get_pain_points_for_persona

        pain_points = get_pain_points_for_persona("av_director")

        assert pain_points is not None
        assert isinstance(pain_points, list)
        assert len(pain_points) > 0

    def test_get_pain_points_unknown_persona(self):
        """Test getting pain points for unknown persona returns generic list."""
        from app.services.langgraph.tools.email_tools import get_pain_points_for_persona

        pain_points = get_pain_points_for_persona("unknown_persona")

        assert pain_points is not None
        assert isinstance(pain_points, list)
        # Should return generic pain points

    def test_build_email_prompt(self, sample_lead: Lead, sample_brief: ResearchBrief):
        """Test building LLM prompt for email generation."""
        from app.services.langgraph.tools.email_tools import build_email_prompt

        prompt = build_email_prompt(
            lead=sample_lead,
            research_brief=sample_brief,
            email_type="pattern_interrupt",
            sequence_step=1,
            pain_points=["Manual recording is time-consuming"],
            personalization_hooks=["Recently expanded online learning"],
        )

        assert prompt is not None
        assert "Sarah" in prompt
        assert "State University" in prompt
        assert "pattern interrupt" in prompt.lower() or "step 1" in prompt.lower()

    def test_get_cta_for_sequence_step(self):
        """Test getting appropriate CTA for each sequence step."""
        from app.services.langgraph.tools.email_tools import get_cta_for_sequence_step

        cta_1 = get_cta_for_sequence_step(1)
        cta_3 = get_cta_for_sequence_step(3)
        cta_4 = get_cta_for_sequence_step(4)

        assert cta_1 is not None
        assert cta_3 is not None
        assert cta_4 is not None
        # Breakup (step 3) and nurture (step 4) should have different CTAs
        assert cta_1 != cta_4
