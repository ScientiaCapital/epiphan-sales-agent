"""Tests for Qualification Agent tools.

TDD RED phase: These tests define the expected behavior of qualification tools.
Tests for ICP scoring functions based on Tim's 5-dimension weighted criteria:
- Company Size (25%)
- Industry Vertical (20%)
- Use Case Fit (25%)
- Tech Stack Signals (15%)
- Buying Authority (15%)
"""


from app.services.langgraph.states import QualificationTier


class TestClassifyCompanySize:
    """Tests for company size classification.

    Scoring (Weight: 25%):
    - Enterprise (1000+): 10 points
    - Mid-market (100-999): 8 points
    - SMB (10-99): 4 points
    - Too small (<10): 0 points
    """

    def test_enterprise_company_scores_10(self):
        """Enterprise companies (1000+ employees) should score 10."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_company_size,
        )

        category, score, reason = classify_company_size(5000)
        assert score == 10
        assert category == "Enterprise"
        assert "5,000" in reason or "5000" in reason

    def test_midmarket_company_scores_8(self):
        """Mid-market companies (100-999 employees) should score 8."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_company_size,
        )

        category, score, reason = classify_company_size(500)
        assert score == 8
        assert category == "Mid-market"

    def test_smb_company_scores_4(self):
        """SMB companies (10-99 employees) should score 4."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_company_size,
        )

        category, score, reason = classify_company_size(50)
        assert score == 4
        assert category == "SMB"

    def test_too_small_company_scores_0(self):
        """Companies with <10 employees should score 0."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_company_size,
        )

        category, score, reason = classify_company_size(5)
        assert score == 0
        assert category == "Too small"

    def test_boundary_1000_is_enterprise(self):
        """Exactly 1000 employees should be Enterprise."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_company_size,
        )

        category, score, _ = classify_company_size(1000)
        assert category == "Enterprise"
        assert score == 10

    def test_boundary_100_is_midmarket(self):
        """Exactly 100 employees should be Mid-market."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_company_size,
        )

        category, score, _ = classify_company_size(100)
        assert category == "Mid-market"
        assert score == 8

    def test_boundary_10_is_smb(self):
        """Exactly 10 employees should be SMB."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_company_size,
        )

        category, score, _ = classify_company_size(10)
        assert category == "SMB"
        assert score == 4

    def test_none_employees_returns_unknown(self):
        """None employee count should return Unknown with score 0."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_company_size,
        )

        category, score, reason = classify_company_size(None)
        assert score == 0
        assert category == "Unknown"
        assert "missing" in reason.lower() or "unknown" in reason.lower()


class TestClassifyVertical:
    """Tests for industry vertical classification.

    Scoring (Weight: 20%):
    - Higher Ed: 10 points
    - Healthcare: 9 points
    - Corporate: 8 points
    - Broadcast/Media: 7 points
    - Legal/Government: 6 points
    - Other: 3 points
    """

    def test_higher_ed_scores_10(self):
        """Higher education industry should score 10."""
        from app.services.langgraph.tools.qualification_tools import classify_vertical

        category, score, _ = classify_vertical("Higher Education", "Stanford University")
        assert score == 10
        assert category == "Higher Ed"

    def test_education_keyword_scores_10(self):
        """Education keyword in industry should score 10."""
        from app.services.langgraph.tools.qualification_tools import classify_vertical

        category, score, _ = classify_vertical("Education", "MIT")
        assert score == 10

    def test_healthcare_scores_9(self):
        """Healthcare industry should score 9."""
        from app.services.langgraph.tools.qualification_tools import classify_vertical

        category, score, _ = classify_vertical("Healthcare", "Mayo Clinic")
        assert score == 9
        assert category == "Healthcare"

    def test_hospital_keyword_scores_9(self):
        """Hospital keyword in company should score 9."""
        from app.services.langgraph.tools.qualification_tools import classify_vertical

        category, score, _ = classify_vertical(None, "Boston General Hospital")
        assert score == 9

    def test_corporate_scores_8(self):
        """Corporate/Enterprise industry should score 8."""
        from app.services.langgraph.tools.qualification_tools import classify_vertical

        category, score, _ = classify_vertical("Enterprise Software", "Salesforce")
        assert score == 8
        assert category == "Corporate"

    def test_broadcast_scores_7(self):
        """Broadcast/Media industry should score 7."""
        from app.services.langgraph.tools.qualification_tools import classify_vertical

        category, score, _ = classify_vertical("Media & Entertainment", "CNN")
        assert score == 7
        assert category == "Broadcast"

    def test_legal_scores_6(self):
        """Legal industry should score 6."""
        from app.services.langgraph.tools.qualification_tools import classify_vertical

        category, score, _ = classify_vertical("Legal Services", "Jones Day")
        assert score == 6
        assert category == "Legal/Government"

    def test_government_scores_6(self):
        """Government industry should score 6."""
        from app.services.langgraph.tools.qualification_tools import classify_vertical

        category, score, _ = classify_vertical("Government", "City of Seattle")
        assert score == 6

    def test_other_industry_scores_3(self):
        """Other/Unknown industries should score 3."""
        from app.services.langgraph.tools.qualification_tools import classify_vertical

        category, score, _ = classify_vertical("Retail", "Target")
        assert score == 3
        assert category == "Other"

    def test_inferred_vertical_used_when_industry_none(self):
        """Should use inferred vertical when industry is None."""
        from app.services.langgraph.tools.qualification_tools import classify_vertical

        category, score, _ = classify_vertical(
            None, "Unknown Corp", inferred="Higher Ed"
        )
        assert score == 10

    def test_university_in_company_name_scores_higher_ed(self):
        """University in company name should detect Higher Ed."""
        from app.services.langgraph.tools.qualification_tools import classify_vertical

        category, score, _ = classify_vertical(None, "State University")
        assert score == 10
        assert category == "Higher Ed"


class TestClassifyUseCase:
    """Tests for use case fit classification.

    Scoring (Weight: 25%):
    - Live streaming: 10 points
    - Lecture capture: 9 points
    - Recording only: 6 points
    - Consumer/Other: 0 points
    """

    def test_av_director_persona_scores_10(self):
        """AV Director persona should indicate live streaming fit (10)."""
        from app.services.langgraph.tools.qualification_tools import classify_use_case

        category, score, _ = classify_use_case(
            persona="AV Director", vertical="Higher Ed", title="AV Director"
        )
        assert score == 10
        assert category == "Live streaming"

    def test_ld_director_persona_scores_9(self):
        """L&D Director persona should indicate lecture capture fit (9)."""
        from app.services.langgraph.tools.qualification_tools import classify_use_case

        category, score, _ = classify_use_case(
            persona="L&D Director", vertical="Corporate", title="Director of L&D"
        )
        assert score == 9
        assert category == "Lecture capture"

    def test_simulation_director_scores_9(self):
        """Simulation Director should indicate simulation training fit (9)."""
        from app.services.langgraph.tools.qualification_tools import classify_use_case

        category, score, _ = classify_use_case(
            persona="Simulation Director", vertical="Healthcare", title="Sim Lab Director"
        )
        assert score == 9

    def test_technical_director_scores_10(self):
        """Technical Director should indicate live production fit (10)."""
        from app.services.langgraph.tools.qualification_tools import classify_use_case

        category, score, _ = classify_use_case(
            persona="Technical Director", vertical="Broadcast", title="Technical Director"
        )
        assert score == 10

    def test_court_admin_scores_recording(self):
        """Court Administrator should indicate recording fit (6)."""
        from app.services.langgraph.tools.qualification_tools import classify_use_case

        category, score, _ = classify_use_case(
            persona="Court Administrator",
            vertical="Legal/Government",
            title="Court Administrator",
        )
        assert score >= 6
        assert "Recording" in category or "recording" in category.lower()

    def test_unknown_persona_with_video_title_scores_reasonably(self):
        """Unknown persona but video-related title should score reasonably."""
        from app.services.langgraph.tools.qualification_tools import classify_use_case

        category, score, _ = classify_use_case(
            persona=None, vertical="Corporate", title="Video Production Manager"
        )
        assert score >= 6

    def test_consumer_persona_scores_0(self):
        """Consumer/non-business persona should score 0."""
        from app.services.langgraph.tools.qualification_tools import classify_use_case

        category, score, _ = classify_use_case(
            persona=None, vertical="Other", title="Student"
        )
        assert score == 0
        assert category == "Consumer"

    def test_tech_stack_with_streaming_tools_boosts_score(self):
        """Having streaming tools in tech stack should boost score."""
        from app.services.langgraph.tools.qualification_tools import classify_use_case

        category, score, _ = classify_use_case(
            persona=None,
            vertical="Corporate",
            title="IT Manager",
            tech_stack=["Zoom", "Teams", "OBS"],
        )
        assert score >= 6


class TestClassifyTechStack:
    """Tests for tech stack signals classification.

    Scoring (Weight: 15%):
    - Competitive solution (Vaddio, Crestron, etc.): 10 points
    - LMS/collaboration need (Canvas, Teams, etc.): 8 points
    - No relevant solution: 5 points
    """

    def test_competitive_solution_scores_10(self):
        """Having competitor solution should score 10 (replacement opportunity)."""
        from app.services.langgraph.tools.qualification_tools import classify_tech_stack

        category, score, _ = classify_tech_stack(["Vaddio", "Crestron AV"])
        assert score == 10
        assert category == "Competitive solution"

    def test_panopto_competitor_scores_10(self):
        """Panopto (competitor) should score 10."""
        from app.services.langgraph.tools.qualification_tools import classify_tech_stack

        category, score, _ = classify_tech_stack(["Panopto", "Canvas LMS"])
        assert score == 10

    def test_lms_only_scores_8(self):
        """LMS without competitor should score 8 (integration opportunity)."""
        from app.services.langgraph.tools.qualification_tools import classify_tech_stack

        category, score, _ = classify_tech_stack(["Canvas", "Blackboard"])
        assert score == 8
        assert category == "LMS need"

    def test_collaboration_tools_score_8(self):
        """Collaboration tools should score 8."""
        from app.services.langgraph.tools.qualification_tools import classify_tech_stack

        category, score, _ = classify_tech_stack(["Microsoft Teams", "Zoom"])
        assert score == 8

    def test_no_relevant_tech_scores_5(self):
        """No relevant tech should score 5."""
        from app.services.langgraph.tools.qualification_tools import classify_tech_stack

        category, score, _ = classify_tech_stack(["Salesforce", "Workday"])
        assert score == 5
        assert category == "No solution"

    def test_empty_tech_stack_scores_5(self):
        """Empty tech stack should score 5."""
        from app.services.langgraph.tools.qualification_tools import classify_tech_stack

        category, score, _ = classify_tech_stack([])
        assert score == 5

    def test_none_tech_stack_scores_5(self):
        """None tech stack should score 5."""
        from app.services.langgraph.tools.qualification_tools import classify_tech_stack

        category, score, _ = classify_tech_stack(None)
        assert score == 5

    def test_enrichment_data_tech_stack_extracted(self):
        """Should extract tech stack from enrichment data."""
        from app.services.langgraph.tools.qualification_tools import classify_tech_stack

        enrichment_data = {"tech_stack": ["Panopto", "Zoom"]}
        category, score, _ = classify_tech_stack(None, enrichment_data)
        assert score == 10


class TestClassifyBuyingAuthority:
    """Tests for buying authority classification.

    Scoring (Weight: 15%):
    - Budget holder (Director+): 10 points
    - Influencer (Manager, Sr.): 7 points
    - End user (Specialist, Analyst): 4 points
    - Student/Intern: 0 points
    """

    def test_director_scores_10(self):
        """Director title should score 10 (budget holder)."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_buying_authority,
        )

        category, score, _ = classify_buying_authority("AV Director", seniority="Director")
        assert score == 10
        assert category == "Budget holder"

    def test_vp_scores_10(self):
        """VP title should score 10."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_buying_authority,
        )

        category, score, _ = classify_buying_authority("VP of IT")
        assert score == 10

    def test_c_level_scores_10(self):
        """C-level title should score 10."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_buying_authority,
        )

        category, score, _ = classify_buying_authority("CTO")
        assert score == 10

    def test_manager_scores_7(self):
        """Manager title should score 7 (influencer)."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_buying_authority,
        )

        category, score, _ = classify_buying_authority("IT Manager")
        assert score == 7
        assert category == "Influencer"

    def test_senior_engineer_scores_7(self):
        """Senior Engineer should score 7."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_buying_authority,
        )

        category, score, _ = classify_buying_authority("Senior AV Engineer")
        assert score == 7

    def test_analyst_scores_4(self):
        """Analyst title should score 4 (end user)."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_buying_authority,
        )

        category, score, _ = classify_buying_authority("Systems Analyst")
        assert score == 4
        assert category == "End user"

    def test_specialist_scores_4(self):
        """Specialist title should score 4."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_buying_authority,
        )

        category, score, _ = classify_buying_authority("AV Specialist")
        assert score == 4

    def test_student_scores_0(self):
        """Student title should score 0."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_buying_authority,
        )

        category, score, _ = classify_buying_authority("Graduate Student")
        assert score == 0
        assert category == "Student"

    def test_intern_scores_0(self):
        """Intern title should score 0."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_buying_authority,
        )

        category, score, _ = classify_buying_authority("IT Intern")
        assert score == 0

    def test_apollo_seniority_used(self):
        """Should use Apollo seniority data when available."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_buying_authority,
        )

        apollo_data = {"seniority": "director"}
        category, score, _ = classify_buying_authority(
            "Some Title", apollo_data=apollo_data
        )
        assert score == 10

    def test_none_title_with_seniority(self):
        """Should handle None title with seniority from data."""
        from app.services.langgraph.tools.qualification_tools import (
            classify_buying_authority,
        )

        category, score, _ = classify_buying_authority(None, seniority="manager")
        assert score == 7


class TestCalculateWeightedScore:
    """Tests for weighted score calculation."""

    def test_perfect_scores_yields_100(self):
        """All dimension scores of 10 should yield 100."""
        from app.services.langgraph.tools.qualification_tools import (
            calculate_weighted_score,
        )

        breakdown = {
            "company_size": {
                "category": "Enterprise",
                "raw_score": 10,
                "weighted_score": 25.0,
                "reason": "5000 employees",
                "confidence": 1.0,
            },
            "industry_vertical": {
                "category": "Higher Ed",
                "raw_score": 10,
                "weighted_score": 20.0,
                "reason": "Higher Education",
                "confidence": 1.0,
            },
            "use_case_fit": {
                "category": "Live streaming",
                "raw_score": 10,
                "weighted_score": 25.0,
                "reason": "AV Director",
                "confidence": 1.0,
            },
            "tech_stack_signals": {
                "category": "Competitive solution",
                "raw_score": 10,
                "weighted_score": 15.0,
                "reason": "Has Vaddio",
                "confidence": 1.0,
            },
            "buying_authority": {
                "category": "Budget holder",
                "raw_score": 10,
                "weighted_score": 15.0,
                "reason": "Director title",
                "confidence": 1.0,
            },
        }

        total = calculate_weighted_score(breakdown)
        assert total == 100.0

    def test_zero_scores_yields_0(self):
        """All dimension scores of 0 should yield 0."""
        from app.services.langgraph.tools.qualification_tools import (
            calculate_weighted_score,
        )

        breakdown = {
            "company_size": {
                "category": "Too small",
                "raw_score": 0,
                "weighted_score": 0.0,
                "reason": "5 employees",
                "confidence": 1.0,
            },
            "industry_vertical": {
                "category": "Other",
                "raw_score": 0,
                "weighted_score": 0.0,
                "reason": "Unknown",
                "confidence": 0.0,
            },
            "use_case_fit": {
                "category": "Consumer",
                "raw_score": 0,
                "weighted_score": 0.0,
                "reason": "Student",
                "confidence": 1.0,
            },
            "tech_stack_signals": {
                "category": "No solution",
                "raw_score": 0,
                "weighted_score": 0.0,
                "reason": "Unknown",
                "confidence": 0.0,
            },
            "buying_authority": {
                "category": "Student",
                "raw_score": 0,
                "weighted_score": 0.0,
                "reason": "Student",
                "confidence": 1.0,
            },
        }

        total = calculate_weighted_score(breakdown)
        assert total == 0.0

    def test_weights_sum_to_100(self):
        """Verify weights are correctly applied: 25+20+25+15+15=100."""
        from app.services.langgraph.tools.qualification_tools import (
            calculate_weighted_score,
        )

        # Each dimension scores 10 (max)
        # company_size: 10 * 0.25 = 2.5 (represented as 25.0 when *10)
        breakdown = {
            "company_size": {
                "category": "Enterprise",
                "raw_score": 10,
                "weighted_score": 25.0,
                "reason": "",
                "confidence": 1.0,
            },
            "industry_vertical": {
                "category": "Higher Ed",
                "raw_score": 10,
                "weighted_score": 20.0,
                "reason": "",
                "confidence": 1.0,
            },
            "use_case_fit": {
                "category": "Live streaming",
                "raw_score": 10,
                "weighted_score": 25.0,
                "reason": "",
                "confidence": 1.0,
            },
            "tech_stack_signals": {
                "category": "Competitive",
                "raw_score": 10,
                "weighted_score": 15.0,
                "reason": "",
                "confidence": 1.0,
            },
            "buying_authority": {
                "category": "Budget holder",
                "raw_score": 10,
                "weighted_score": 15.0,
                "reason": "",
                "confidence": 1.0,
            },
        }

        total = calculate_weighted_score(breakdown)
        assert total == 100.0

    def test_mixed_scores_calculated_correctly(self):
        """Test calculation with mixed scores.

        Score: (8*2.5) + (10*2.0) + (6*2.5) + (5*1.5) + (7*1.5) = 20+20+15+7.5+10.5 = 73
        """
        from app.services.langgraph.tools.qualification_tools import (
            calculate_weighted_score,
        )

        breakdown = {
            "company_size": {
                "category": "Mid-market",
                "raw_score": 8,
                "weighted_score": 20.0,
                "reason": "",
                "confidence": 1.0,
            },
            "industry_vertical": {
                "category": "Higher Ed",
                "raw_score": 10,
                "weighted_score": 20.0,
                "reason": "",
                "confidence": 1.0,
            },
            "use_case_fit": {
                "category": "Recording",
                "raw_score": 6,
                "weighted_score": 15.0,
                "reason": "",
                "confidence": 1.0,
            },
            "tech_stack_signals": {
                "category": "No solution",
                "raw_score": 5,
                "weighted_score": 7.5,
                "reason": "",
                "confidence": 1.0,
            },
            "buying_authority": {
                "category": "Influencer",
                "raw_score": 7,
                "weighted_score": 10.5,
                "reason": "",
                "confidence": 1.0,
            },
        }

        total = calculate_weighted_score(breakdown)
        assert total == 73.0


class TestAssignTier:
    """Tests for tier assignment based on weighted score."""

    def test_score_70_plus_is_tier_1(self):
        """Score of 70+ should be Tier 1."""
        from app.services.langgraph.tools.qualification_tools import assign_tier

        assert assign_tier(70.0) == QualificationTier.TIER_1
        assert assign_tier(85.0) == QualificationTier.TIER_1
        assert assign_tier(100.0) == QualificationTier.TIER_1

    def test_score_50_to_69_is_tier_2(self):
        """Score of 50-69 should be Tier 2."""
        from app.services.langgraph.tools.qualification_tools import assign_tier

        assert assign_tier(50.0) == QualificationTier.TIER_2
        assert assign_tier(60.0) == QualificationTier.TIER_2
        assert assign_tier(69.0) == QualificationTier.TIER_2
        assert assign_tier(69.9) == QualificationTier.TIER_2

    def test_score_30_to_49_is_tier_3(self):
        """Score of 30-49 should be Tier 3."""
        from app.services.langgraph.tools.qualification_tools import assign_tier

        assert assign_tier(30.0) == QualificationTier.TIER_3
        assert assign_tier(40.0) == QualificationTier.TIER_3
        assert assign_tier(49.0) == QualificationTier.TIER_3
        assert assign_tier(49.9) == QualificationTier.TIER_3

    def test_score_below_30_is_not_icp(self):
        """Score below 30 should be Not ICP."""
        from app.services.langgraph.tools.qualification_tools import assign_tier

        assert assign_tier(29.9) == QualificationTier.NOT_ICP
        assert assign_tier(20.0) == QualificationTier.NOT_ICP
        assert assign_tier(0.0) == QualificationTier.NOT_ICP


class TestDetermineNextAction:
    """Tests for next action determination based on tier."""

    def test_tier_1_recommends_priority_sequence(self):
        """Tier 1 leads should get priority sequence with AE involvement."""
        from app.services.langgraph.tools.qualification_tools import (
            determine_next_action,
        )

        action = determine_next_action(
            tier=QualificationTier.TIER_1,
            missing_info=[],
            confidence=0.9,
        )

        assert action["action_type"] == "priority_sequence"
        assert action["priority"] == "high"
        assert action["ae_involvement"] is True

    def test_tier_2_recommends_standard_sequence(self):
        """Tier 2 leads should get standard sequence."""
        from app.services.langgraph.tools.qualification_tools import (
            determine_next_action,
        )

        action = determine_next_action(
            tier=QualificationTier.TIER_2,
            missing_info=[],
            confidence=0.8,
        )

        assert action["action_type"] == "standard_sequence"
        assert action["priority"] == "medium"
        assert action["ae_involvement"] is False

    def test_tier_3_recommends_nurture(self):
        """Tier 3 leads should get marketing nurture."""
        from app.services.langgraph.tools.qualification_tools import (
            determine_next_action,
        )

        action = determine_next_action(
            tier=QualificationTier.TIER_3,
            missing_info=[],
            confidence=0.7,
        )

        assert action["action_type"] == "nurture"
        assert action["priority"] == "low"
        assert action["ae_involvement"] is False

    def test_not_icp_recommends_disqualify(self):
        """Not ICP leads should be disqualified."""
        from app.services.langgraph.tools.qualification_tools import (
            determine_next_action,
        )

        action = determine_next_action(
            tier=QualificationTier.NOT_ICP,
            missing_info=[],
            confidence=0.9,
        )

        assert action["action_type"] == "disqualify"
        assert action["ae_involvement"] is False

    def test_missing_info_included_in_action(self):
        """Missing info should be included in action recommendation."""
        from app.services.langgraph.tools.qualification_tools import (
            determine_next_action,
        )

        missing = ["company_size", "tech_stack"]
        action = determine_next_action(
            tier=QualificationTier.TIER_2,
            missing_info=missing,
            confidence=0.5,
        )

        assert action["missing_info"] == missing

    def test_low_confidence_tier_1_suggests_research(self):
        """Low confidence Tier 1 should suggest more research."""
        from app.services.langgraph.tools.qualification_tools import (
            determine_next_action,
        )

        action = determine_next_action(
            tier=QualificationTier.TIER_1,
            missing_info=["company_size"],
            confidence=0.4,
        )

        assert "research" in action["description"].lower() or len(action["missing_info"]) > 0
