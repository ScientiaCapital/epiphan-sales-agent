"""Tests for Review Gates.

Tests the quality checkpoint gates that enforce mandatory checks
before phase transitions.
"""

import pytest

from app.data.lead_schemas import Lead
from app.services.langgraph.gates import (
    CheckResult,
    DataCompletenessGate,
    EnrichmentQualityGate,
    GateEvaluationResult,
    OutputQualityGate,
    get_gate,
)
from app.services.langgraph.states import QualificationTier


@pytest.fixture
def sample_lead() -> Lead:
    """Create a sample lead for testing."""
    return Lead(
        hubspot_id="hs-test-123",
        email="test@company.com",
        first_name="Test",
        last_name="User",
        company="Test Company",
        title="Director",
    )


@pytest.fixture
def complete_state(sample_lead: Lead) -> dict:
    """Create a state with all data complete."""
    return {
        "lead": sample_lead,
        "qualification_result": {"tier": QualificationTier.TIER_1, "score": 85},
        "research_brief": {"company_overview": "Test company overview"},
        "enrichment_data": {"phone": "123-456-7890", "title": "Director"},
        "has_phone": True,
        "tier": QualificationTier.TIER_1,
        "script_result": {"personalized_script": "Hi, I noticed..."},
        "email_result": {"subject_line": "Quick question", "email_body": "Hi..."},
    }


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_check_result_defaults(self) -> None:
        """Test CheckResult has correct defaults."""
        result = CheckResult(name="test", passed=True, reason="Test passed")
        assert result.severity == "error"
        assert result.remediation is None

    def test_check_result_with_remediation(self) -> None:
        """Test CheckResult with remediation."""
        result = CheckResult(
            name="test",
            passed=False,
            reason="Test failed",
            remediation="Fix it",
        )
        assert result.remediation == "Fix it"


class TestGateEvaluationResult:
    """Tests for GateEvaluationResult dataclass."""

    def test_evaluation_result_defaults(self) -> None:
        """Test GateEvaluationResult has correct defaults."""
        result = GateEvaluationResult(proceed=True)
        assert result.passed_checks == []
        assert result.failed_checks == []
        assert result.warnings == []
        assert result.remediation is None
        assert result.confidence == 1.0


class TestDataCompletenessGate:
    """Tests for DataCompletenessGate."""

    @pytest.mark.asyncio
    async def test_passes_with_complete_data(self, complete_state: dict) -> None:
        """Test gate passes when data is complete."""
        gate = DataCompletenessGate()
        decision = await gate.evaluate(complete_state)

        assert decision["proceed"] is True
        assert decision["gate_name"] == "data_completeness"
        assert "qualification_completed" in decision["passed_checks"]
        assert "research_data_available" in decision["passed_checks"]
        assert "email_exists" in decision["passed_checks"]

    @pytest.mark.asyncio
    async def test_fails_without_qualification(
        self, complete_state: dict
    ) -> None:
        """Test gate fails when qualification is missing."""
        gate = DataCompletenessGate()
        state = {**complete_state, "qualification_result": None}
        decision = await gate.evaluate(state)

        assert decision["proceed"] is False
        assert "qualification_completed" in decision["failed_checks"]
        assert decision["remediation"] is not None

    @pytest.mark.asyncio
    async def test_fails_without_research_data(
        self, complete_state: dict
    ) -> None:
        """Test gate fails when no research data available."""
        gate = DataCompletenessGate()
        state = {
            **complete_state,
            "research_brief": None,
            "enrichment_data": None,
        }
        decision = await gate.evaluate(state)

        assert decision["proceed"] is False
        assert "research_data_available" in decision["failed_checks"]

    @pytest.mark.asyncio
    async def test_passes_with_enrichment_only(self, complete_state: dict) -> None:
        """Test gate passes with enrichment data but no research brief."""
        gate = DataCompletenessGate()
        state = {**complete_state, "research_brief": None}
        decision = await gate.evaluate(state)

        assert decision["proceed"] is True
        assert "research_data_available" in decision["passed_checks"]

    @pytest.mark.asyncio
    async def test_passes_without_phone_with_warning(
        self, complete_state: dict
    ) -> None:
        """Test gate passes but warns when phone is missing."""
        gate = DataCompletenessGate()
        state = {**complete_state, "has_phone": False}
        decision = await gate.evaluate(state)

        # Gate should still pass - phone is important but not blocking
        assert decision["proceed"] is True
        assert "phone_available" in decision["passed_checks"]  # Warning treated as pass

    @pytest.mark.asyncio
    async def test_fails_without_email(self, complete_state: dict) -> None:
        """Test gate fails when lead has no email."""
        gate = DataCompletenessGate()
        lead_no_email = Lead(
            hubspot_id="test",
            email="",  # Empty email
            company="Test",
        )
        state = {**complete_state, "lead": lead_no_email}
        decision = await gate.evaluate(state)

        assert decision["proceed"] is False
        assert "email_exists" in decision["failed_checks"]

    @pytest.mark.asyncio
    async def test_routes_not_icp_to_archive(self, complete_state: dict) -> None:
        """Test not ICP leads are routed to archive."""
        gate = DataCompletenessGate()
        state = {**complete_state, "tier": QualificationTier.NOT_ICP}
        decision = await gate.evaluate(state)

        assert decision["proceed"] is True
        assert decision["next_phase"] == "archive"

    @pytest.mark.asyncio
    async def test_routes_qualified_to_outreach(self, complete_state: dict) -> None:
        """Test qualified leads are routed to outreach."""
        gate = DataCompletenessGate()
        decision = await gate.evaluate(complete_state)

        assert decision["proceed"] is True
        assert decision["next_phase"] == "outreach"

    def test_gate_name(self) -> None:
        """Test gate has correct name."""
        gate = DataCompletenessGate()
        assert gate.gate_name == "data_completeness"


class TestOutputQualityGate:
    """Tests for OutputQualityGate."""

    @pytest.mark.asyncio
    async def test_passes_with_script(self, complete_state: dict) -> None:
        """Test gate passes when script is generated."""
        gate = OutputQualityGate()
        state = {**complete_state, "email_result": None}
        decision = await gate.evaluate(state)

        assert decision["proceed"] is True
        assert "script_generated" in decision["passed_checks"]

    @pytest.mark.asyncio
    async def test_passes_with_email(self, complete_state: dict) -> None:
        """Test gate passes when email is generated."""
        gate = OutputQualityGate()
        state = {**complete_state, "script_result": None}
        decision = await gate.evaluate(state)

        assert decision["proceed"] is True
        assert "email_generated" in decision["passed_checks"]

    @pytest.mark.asyncio
    async def test_passes_with_both(self, complete_state: dict) -> None:
        """Test gate passes when both script and email are generated."""
        gate = OutputQualityGate()
        decision = await gate.evaluate(complete_state)

        assert decision["proceed"] is True
        assert "script_generated" in decision["passed_checks"]
        assert "email_generated" in decision["passed_checks"]

    @pytest.mark.asyncio
    async def test_fails_without_any_content(self, complete_state: dict) -> None:
        """Test gate fails when no content is generated."""
        gate = OutputQualityGate()
        state = {**complete_state, "script_result": None, "email_result": None}
        decision = await gate.evaluate(state)

        assert decision["proceed"] is False
        assert "script_generated" in decision["failed_checks"]
        assert "email_generated" in decision["failed_checks"]
        assert decision["remediation"] is not None

    @pytest.mark.asyncio
    async def test_validates_script_content(self, complete_state: dict) -> None:
        """Test script must have actual content."""
        gate = OutputQualityGate()
        state = {
            **complete_state,
            "script_result": {},  # Empty script
            "email_result": None,
        }
        decision = await gate.evaluate(state)

        assert decision["proceed"] is False

    @pytest.mark.asyncio
    async def test_validates_email_content(self, complete_state: dict) -> None:
        """Test email must have subject and body."""
        gate = OutputQualityGate()
        state = {
            **complete_state,
            "script_result": None,
            "email_result": {"subject_line": "Hi"},  # Missing body
        }
        decision = await gate.evaluate(state)

        assert decision["proceed"] is False

    @pytest.mark.asyncio
    async def test_routes_to_sync_on_success(self, complete_state: dict) -> None:
        """Test successful gate routes to sync phase."""
        gate = OutputQualityGate()
        decision = await gate.evaluate(complete_state)

        assert decision["proceed"] is True
        assert decision["next_phase"] == "sync"

    def test_gate_name(self) -> None:
        """Test gate has correct name."""
        gate = OutputQualityGate()
        assert gate.gate_name == "output_quality"


class TestEnrichmentQualityGate:
    """Tests for EnrichmentQualityGate."""

    @pytest.mark.asyncio
    async def test_passes_with_complete_enrichment(
        self, sample_lead: Lead
    ) -> None:
        """Test gate passes with complete enrichment."""
        gate = EnrichmentQualityGate()
        state = {
            "lead": sample_lead,
            "enrichment_data": {
                "company": "Test Corp",
                "title": "Director",
                "phone": "123-456",
            },
        }
        decision = await gate.evaluate(state)

        assert decision["proceed"] is True
        assert "company_info" in decision["passed_checks"]
        assert "role_info" in decision["passed_checks"]
        assert "contact_method" in decision["passed_checks"]

    @pytest.mark.asyncio
    async def test_passes_with_minimal_data(self, sample_lead: Lead) -> None:
        """Test gate passes with just contact method (email from lead)."""
        gate = EnrichmentQualityGate()
        state = {
            "lead": sample_lead,  # Has email
            "enrichment_data": {},
        }
        decision = await gate.evaluate(state)

        # Should pass - missing company/role are warnings, not errors
        assert decision["proceed"] is True

    @pytest.mark.asyncio
    async def test_warns_about_missing_company(self, sample_lead: Lead) -> None:
        """Test gate warns when company info is missing."""
        gate = EnrichmentQualityGate()
        state = {
            "lead": sample_lead,
            "enrichment_data": {"title": "Director"},
        }
        decision = await gate.evaluate(state)

        # Passes but company_info should be in failed checks (warning)
        assert decision["proceed"] is True
        assert "company_info" in decision["failed_checks"]

    @pytest.mark.asyncio
    async def test_warns_about_missing_role(self, sample_lead: Lead) -> None:
        """Test gate warns when role info is missing."""
        gate = EnrichmentQualityGate()
        state = {
            "lead": sample_lead,
            "enrichment_data": {"company": "Test Corp"},
        }
        decision = await gate.evaluate(state)

        assert decision["proceed"] is True
        assert "role_info" in decision["failed_checks"]

    def test_gate_name(self) -> None:
        """Test gate has correct name."""
        gate = EnrichmentQualityGate()
        assert gate.gate_name == "enrichment_quality"


class TestGateRegistry:
    """Tests for gate registry."""

    def test_get_data_completeness_gate(self) -> None:
        """Test getting data completeness gate."""
        gate = get_gate("data_completeness")
        assert isinstance(gate, DataCompletenessGate)

    def test_get_output_quality_gate(self) -> None:
        """Test getting output quality gate."""
        gate = get_gate("output_quality")
        assert isinstance(gate, OutputQualityGate)

    def test_get_enrichment_quality_gate(self) -> None:
        """Test getting enrichment quality gate."""
        gate = get_gate("enrichment_quality")
        assert isinstance(gate, EnrichmentQualityGate)

    def test_get_unknown_gate_raises(self) -> None:
        """Test getting unknown gate raises error."""
        with pytest.raises(ValueError, match="Unknown gate"):
            get_gate("nonexistent_gate")
