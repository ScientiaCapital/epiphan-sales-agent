"""Tests for call brief effectiveness deep analytics.

Tests ConversionFunnel builder, phone type impact, extraction helpers,
enhanced main endpoint, persona deep dive, script matrix, and edge cases.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.data.call_outcome_schemas import (
    BriefEffectivenessResponse,
    ConversionFunnel,
    PersonaEffectivenessDetail,
    PhoneTypeImpact,
    QualityConversion,
    ScriptEffectivenessResponse,
    ScriptTemplateRow,
    TierAnalytics,
)
from app.main import app
from app.services.call_outcomes.service import CallOutcomeService

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def service() -> CallOutcomeService:
    return CallOutcomeService()


@pytest.fixture
def connected_meeting_outcome() -> dict[str, Any]:
    """Outcome: connected call → meeting booked."""
    return {
        "id": "o-1",
        "disposition": "connected",
        "result": "meeting_booked",
        "objections": ["budget", "timing"],
        "buying_signals": ["asked about pricing", "mentioned competitor"],
        "phone_type": "direct",
        "duration_seconds": 180,
        "called_at": "2026-02-06T10:00:00Z",
    }


@pytest.fixture
def voicemail_outcome() -> dict[str, Any]:
    """Outcome: voicemail → no contact."""
    return {
        "id": "o-2",
        "disposition": "voicemail",
        "result": "no_contact",
        "objections": None,
        "buying_signals": None,
        "phone_type": "mobile",
        "duration_seconds": 0,
        "called_at": "2026-02-06T11:00:00Z",
    }


@pytest.fixture
def connected_follow_up_outcome() -> dict[str, Any]:
    """Outcome: connected → follow-up needed."""
    return {
        "id": "o-3",
        "disposition": "connected",
        "result": "follow_up_needed",
        "objections": ["budget"],
        "buying_signals": ["interested in demo"],
        "phone_type": "work",
        "duration_seconds": 120,
        "called_at": "2026-02-06T12:00:00Z",
    }


@pytest.fixture
def sample_brief(
    connected_meeting_outcome: dict[str, Any],
    voicemail_outcome: dict[str, Any],
) -> dict[str, Any]:
    """A brief with linked outcomes and rich brief_json."""
    return {
        "id": "brief-1",
        "brief_quality": "HIGH",
        "brief_json": {
            "contact": {
                "persona_id": "av_director",
                "persona_title": "AV Director",
                "title": "AV Director",
            },
            "qualification": {
                "tier": "Tier 1",
                "score": 85,
                "persona": "av_director",
            },
            "trigger": "demo_request",
            "objection_prep": {
                "objections": [
                    {"objection": "budget"},
                    {"objection": "timing"},
                ],
            },
        },
        "call_outcomes": [connected_meeting_outcome, voicemail_outcome],
    }


# =============================================================================
# 1. ConversionFunnel Builder
# =============================================================================


class TestBuildConversionFunnel:
    def test_empty_outcomes(self, service: CallOutcomeService) -> None:
        funnel = service._build_conversion_funnel([])
        assert funnel.total_outcomes == 0
        assert funnel.connections == 0
        assert funnel.meetings_booked == 0
        assert funnel.connect_rate == 0.0
        assert funnel.meeting_rate == 0.0
        assert funnel.conversion_rate == 0.0

    def test_single_meeting(
        self,
        service: CallOutcomeService,
        connected_meeting_outcome: dict[str, Any],
    ) -> None:
        funnel = service._build_conversion_funnel([connected_meeting_outcome])
        assert funnel.total_outcomes == 1
        assert funnel.connections == 1
        assert funnel.meetings_booked == 1
        assert funnel.connect_rate == 100.0
        assert funnel.meeting_rate == 100.0
        assert funnel.conversion_rate == 100.0

    def test_mixed_outcomes(
        self,
        service: CallOutcomeService,
        connected_meeting_outcome: dict[str, Any],
        voicemail_outcome: dict[str, Any],
        connected_follow_up_outcome: dict[str, Any],
    ) -> None:
        outcomes = [connected_meeting_outcome, voicemail_outcome, connected_follow_up_outcome]
        funnel = service._build_conversion_funnel(outcomes)
        assert funnel.total_outcomes == 3
        assert funnel.connections == 2
        assert funnel.meetings_booked == 1
        assert funnel.follow_ups == 1
        assert funnel.no_contact == 1
        assert funnel.connect_rate == 66.7  # 2/3 * 100
        assert funnel.meeting_rate == 50.0  # 1/2 * 100
        assert funnel.conversion_rate == 33.3  # 1/3 * 100

    def test_total_briefs_passed_through(self, service: CallOutcomeService) -> None:
        funnel = service._build_conversion_funnel([], total_briefs=42)
        assert funnel.total_briefs == 42

    def test_all_result_types(self, service: CallOutcomeService) -> None:
        outcomes = [
            {"disposition": "connected", "result": "meeting_booked"},
            {"disposition": "connected", "result": "follow_up_needed"},
            {"disposition": "connected", "result": "qualified_out"},
            {"disposition": "connected", "result": "nurture"},
            {"disposition": "connected", "result": "dead"},
            {"disposition": "voicemail", "result": "no_contact"},
        ]
        funnel = service._build_conversion_funnel(outcomes)
        assert funnel.meetings_booked == 1
        assert funnel.follow_ups == 1
        assert funnel.qualified_out == 1
        assert funnel.nurture == 1
        assert funnel.dead == 1
        assert funnel.no_contact == 1


# =============================================================================
# 2. Phone Type Impact
# =============================================================================


class TestComputePhoneTypeImpact:
    def test_empty_outcomes(self, service: CallOutcomeService) -> None:
        result = service._compute_phone_type_impact([])
        assert result == []

    def test_single_phone_type(
        self,
        service: CallOutcomeService,
        connected_meeting_outcome: dict[str, Any],
    ) -> None:
        result = service._compute_phone_type_impact([connected_meeting_outcome])
        assert len(result) == 1
        assert result[0].phone_type == "direct"
        assert result[0].dials == 1
        assert result[0].connections == 1
        assert result[0].meetings == 1
        assert result[0].connect_rate == 100.0
        assert result[0].meeting_rate == 100.0

    def test_multiple_phone_types(self, service: CallOutcomeService) -> None:
        outcomes = [
            {"phone_type": "direct", "disposition": "connected", "result": "meeting_booked"},
            {"phone_type": "direct", "disposition": "connected", "result": "follow_up_needed"},
            {"phone_type": "mobile", "disposition": "voicemail", "result": "no_contact"},
        ]
        result = service._compute_phone_type_impact(outcomes)
        assert len(result) == 2
        phone_map = {p.phone_type: p for p in result}
        assert phone_map["direct"].dials == 2
        assert phone_map["direct"].connections == 2
        assert phone_map["direct"].meetings == 1
        assert phone_map["mobile"].dials == 1
        assert phone_map["mobile"].connections == 0

    def test_null_phone_type_defaults_to_unknown(self, service: CallOutcomeService) -> None:
        result = service._compute_phone_type_impact([
            {"phone_type": None, "disposition": "voicemail", "result": "no_contact"},
        ])
        assert len(result) == 1
        assert result[0].phone_type == "unknown"


# =============================================================================
# 3. Extract Top Items
# =============================================================================


class TestExtractTopItems:
    def test_empty_outcomes(self, service: CallOutcomeService) -> None:
        result = service._extract_top_items([], "objections")
        assert result == []

    def test_frequency_sorted(self, service: CallOutcomeService) -> None:
        outcomes = [
            {"objections": ["budget", "timing"]},
            {"objections": ["budget", "authority"]},
            {"objections": ["budget"]},
        ]
        result = service._extract_top_items(outcomes, "objections")
        assert result[0] == {"budget": 3}
        assert len(result) <= 3

    def test_limit_respected(self, service: CallOutcomeService) -> None:
        outcomes = [
            {"objections": ["a", "b", "c", "d", "e"]},
        ]
        result = service._extract_top_items(outcomes, "objections", limit=2)
        assert len(result) == 2

    def test_none_items_skipped(self, service: CallOutcomeService) -> None:
        outcomes = [
            {"objections": None},
            {"objections": ["budget"]},
        ]
        result = service._extract_top_items(outcomes, "objections")
        assert result == [{"budget": 1}]

    def test_buying_signals_field(self, service: CallOutcomeService) -> None:
        outcomes = [
            {"buying_signals": ["asked about pricing", "asked about pricing"]},
            {"buying_signals": ["mentioned competitor"]},
        ]
        result = service._extract_top_items(outcomes, "buying_signals")
        assert result[0] == {"asked about pricing": 2}

    def test_case_insensitive(self, service: CallOutcomeService) -> None:
        outcomes = [
            {"objections": ["Budget"]},
            {"objections": ["budget"]},
            {"objections": ["BUDGET"]},
        ]
        result = service._extract_top_items(outcomes, "objections")
        assert result == [{"budget": 3}]


# =============================================================================
# 4. Compute Average Duration
# =============================================================================


class TestComputeAvgDuration:
    def test_empty_outcomes(self, service: CallOutcomeService) -> None:
        assert service._compute_avg_duration([]) == 0.0

    def test_connected_only(self, service: CallOutcomeService) -> None:
        outcomes = [
            {"disposition": "connected", "duration_seconds": 120},
            {"disposition": "connected", "duration_seconds": 180},
            {"disposition": "voicemail", "duration_seconds": 30},
        ]
        result = service._compute_avg_duration(outcomes)
        assert result == 150.0

    def test_zero_duration_excluded(self, service: CallOutcomeService) -> None:
        outcomes = [
            {"disposition": "connected", "duration_seconds": 0},
            {"disposition": "connected", "duration_seconds": 120},
        ]
        result = service._compute_avg_duration(outcomes)
        assert result == 120.0


# =============================================================================
# 5. Extract Persona From Brief
# =============================================================================


class TestExtractPersonaFromBrief:
    def test_from_contact(self, service: CallOutcomeService) -> None:
        brief_json = {
            "contact": {"persona_id": "av_director", "persona_title": "AV Director"},
        }
        pid, title = service._extract_persona_from_brief(brief_json)
        assert pid == "av_director"
        assert title == "AV Director"

    def test_fallback_to_qualification(self, service: CallOutcomeService) -> None:
        brief_json = {
            "contact": {"title": "AV Director"},
            "qualification": {"persona": "av_director"},
        }
        pid, title = service._extract_persona_from_brief(brief_json)
        assert pid == "av_director"
        assert title == "AV Director"

    def test_missing_persona(self, service: CallOutcomeService) -> None:
        pid, title = service._extract_persona_from_brief({})
        assert pid is None
        assert title is None


# =============================================================================
# 6. Extract Tier From Brief
# =============================================================================


class TestExtractTierFromBrief:
    def test_from_qualification(self, service: CallOutcomeService) -> None:
        brief_json = {"qualification": {"tier": "Tier 1"}}
        assert service._extract_tier_from_brief(brief_json) == "Tier 1"

    def test_missing_tier(self, service: CallOutcomeService) -> None:
        assert service._extract_tier_from_brief({}) is None


# =============================================================================
# 7. Enhanced get_brief_effectiveness
# =============================================================================


class TestGetBriefEffectiveness:
    @patch("app.services.call_outcomes.service.supabase_client")
    def test_returns_brief_effectiveness_response(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        mock_db.get_briefs_with_outcomes.return_value = []
        result = service.get_brief_effectiveness()
        assert isinstance(result, BriefEffectivenessResponse)

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_backward_compatible_fields(
        self,
        mock_db: MagicMock,
        service: CallOutcomeService,
        sample_brief: dict[str, Any],
    ) -> None:
        mock_db.get_briefs_with_outcomes.return_value = [sample_brief]
        result = service.get_brief_effectiveness()
        assert result.total_briefs_used == 1
        assert result.total_outcomes_linked == 2
        assert "HIGH" in result.conversion_by_quality
        assert isinstance(result.conversion_by_quality["HIGH"], QualityConversion)
        assert result.objection_prediction_accuracy >= 0.0
        assert result.avg_brief_quality_for_meetings in ("HIGH", "MEDIUM", "LOW", "N/A")

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_persona_effectiveness_populated(
        self,
        mock_db: MagicMock,
        service: CallOutcomeService,
        sample_brief: dict[str, Any],
    ) -> None:
        mock_db.get_briefs_with_outcomes.return_value = [sample_brief]
        result = service.get_brief_effectiveness()
        assert len(result.persona_effectiveness) >= 1
        persona = result.persona_effectiveness[0]
        assert persona.persona_id == "av_director"

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_tier_analytics_populated(
        self,
        mock_db: MagicMock,
        service: CallOutcomeService,
        sample_brief: dict[str, Any],
    ) -> None:
        mock_db.get_briefs_with_outcomes.return_value = [sample_brief]
        result = service.get_brief_effectiveness()
        assert len(result.tier_analytics) >= 1
        tier = result.tier_analytics[0]
        assert tier.tier == "Tier 1"

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_phone_type_impact_populated(
        self,
        mock_db: MagicMock,
        service: CallOutcomeService,
        sample_brief: dict[str, Any],
    ) -> None:
        mock_db.get_briefs_with_outcomes.return_value = [sample_brief]
        result = service.get_brief_effectiveness()
        assert len(result.phone_type_impact) >= 1

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_overall_funnel_populated(
        self,
        mock_db: MagicMock,
        service: CallOutcomeService,
        sample_brief: dict[str, Any],
    ) -> None:
        mock_db.get_briefs_with_outcomes.return_value = [sample_brief]
        result = service.get_brief_effectiveness()
        assert result.overall_funnel.total_outcomes == 2
        assert result.overall_funnel.connections == 1
        assert result.overall_funnel.meetings_booked == 1

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_empty_data(self, mock_db: MagicMock, service: CallOutcomeService) -> None:
        mock_db.get_briefs_with_outcomes.return_value = []
        result = service.get_brief_effectiveness()
        assert result.total_briefs_used == 0
        assert result.total_outcomes_linked == 0
        assert result.overall_funnel.total_outcomes == 0


# =============================================================================
# 8. Persona Deep Dive
# =============================================================================


class TestGetPersonaEffectiveness:
    @patch("app.services.call_outcomes.service.supabase_client")
    def test_returns_persona_detail(
        self,
        mock_db: MagicMock,
        service: CallOutcomeService,
        sample_brief: dict[str, Any],
    ) -> None:
        mock_db.get_briefs_with_outcomes.return_value = [sample_brief]
        result = service.get_persona_effectiveness("av_director")
        assert isinstance(result, PersonaEffectivenessDetail)
        assert result.persona_id == "av_director"

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_per_trigger_breakdown(
        self,
        mock_db: MagicMock,
        service: CallOutcomeService,
        sample_brief: dict[str, Any],
    ) -> None:
        mock_db.get_briefs_with_outcomes.return_value = [sample_brief]
        result = service.get_persona_effectiveness("av_director")
        assert len(result.by_trigger) >= 1
        assert result.by_trigger[0].trigger == "demo_request"

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_top_objections_populated(
        self,
        mock_db: MagicMock,
        service: CallOutcomeService,
        sample_brief: dict[str, Any],
    ) -> None:
        mock_db.get_briefs_with_outcomes.return_value = [sample_brief]
        result = service.get_persona_effectiveness("av_director")
        assert len(result.top_objections) >= 1

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_sample_size_warning(self, mock_db: MagicMock, service: CallOutcomeService) -> None:
        """Triggers with < 5 outcomes should have sample_size_warning=True."""
        brief = {
            "id": "b-1",
            "brief_quality": "HIGH",
            "brief_json": {"trigger": "demo_request"},
            "call_outcomes": [
                {"disposition": "connected", "result": "meeting_booked"},
            ],
        }
        mock_db.get_briefs_with_outcomes.return_value = [brief]
        result = service.get_persona_effectiveness("av_director")
        if result.by_trigger:
            assert result.by_trigger[0].sample_size_warning is True

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_empty_persona_data(self, mock_db: MagicMock, service: CallOutcomeService) -> None:
        mock_db.get_briefs_with_outcomes.return_value = []
        result = service.get_persona_effectiveness("av_director")
        assert result.overall_funnel.total_outcomes == 0
        assert result.by_trigger == []


# =============================================================================
# 9. Script Effectiveness Matrix
# =============================================================================


class TestGetScriptEffectiveness:
    @patch("app.services.call_outcomes.service.supabase_client")
    def test_returns_script_response(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        mock_db.get_briefs_with_outcomes.return_value = []
        result = service.get_script_effectiveness()
        assert isinstance(result, ScriptEffectivenessResponse)

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_rows_sorted_by_meeting_rate(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        briefs = [
            {
                "id": "b-1",
                "brief_quality": "HIGH",
                "brief_json": {
                    "contact": {"persona_id": "av_director"},
                    "trigger": "demo_request",
                },
                "call_outcomes": [
                    {"disposition": "connected", "result": "meeting_booked"},
                ],
            },
            {
                "id": "b-2",
                "brief_quality": "MEDIUM",
                "brief_json": {
                    "contact": {"persona_id": "ld_director"},
                    "trigger": "content_download",
                },
                "call_outcomes": [
                    {"disposition": "voicemail", "result": "no_contact"},
                ],
            },
        ]
        mock_db.get_briefs_with_outcomes.return_value = briefs
        result = service.get_script_effectiveness()
        assert len(result.rows) == 2
        assert result.rows[0].funnel.meeting_rate >= result.rows[1].funnel.meeting_rate

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_best_worst_min_sample(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """best/worst should only include rows with >= 5 outcomes."""
        briefs = [
            {
                "id": f"b-{i}",
                "brief_quality": "HIGH",
                "brief_json": {"contact": {"persona_id": "av_director"}, "trigger": "demo_request"},
                "call_outcomes": [{"disposition": "connected", "result": "meeting_booked"}],
            }
            for i in range(6)
        ]
        mock_db.get_briefs_with_outcomes.return_value = briefs
        result = service.get_script_effectiveness()
        # 6 outcomes for same combo → sample_size_warning=False → eligible
        assert result.best_performing is not None

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_no_eligible_best_worst(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """When all combos have < 5 samples, best/worst should be None."""
        briefs = [
            {
                "id": "b-1",
                "brief_quality": "HIGH",
                "brief_json": {"contact": {"persona_id": "av_director"}, "trigger": "demo_request"},
                "call_outcomes": [{"disposition": "connected", "result": "meeting_booked"}],
            },
        ]
        mock_db.get_briefs_with_outcomes.return_value = briefs
        result = service.get_script_effectiveness()
        assert result.best_performing is None
        assert result.worst_performing is None

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_empty_data(self, mock_db: MagicMock, service: CallOutcomeService) -> None:
        mock_db.get_briefs_with_outcomes.return_value = []
        result = service.get_script_effectiveness()
        assert result.rows == []
        assert result.best_performing is None


# =============================================================================
# 10. API Endpoint Tests
# =============================================================================


class TestBriefEffectivenessAPI:
    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_enhanced_endpoint_returns_200(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        mock_service.get_brief_effectiveness.return_value = BriefEffectivenessResponse(
            total_briefs_used=10,
            total_outcomes_linked=8,
        )
        response = client.get("/api/call-outcomes/brief-effectiveness")
        assert response.status_code == 200
        data = response.json()
        assert data["total_briefs_used"] == 10
        assert "overall_funnel" in data
        assert "persona_effectiveness" in data

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_persona_endpoint_valid(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        mock_service.get_persona_effectiveness.return_value = PersonaEffectivenessDetail(
            persona_id="av_director",
            persona_title="AV Director",
        )
        response = client.get("/api/call-outcomes/brief-effectiveness/persona/av_director")
        assert response.status_code == 200
        data = response.json()
        assert data["persona_id"] == "av_director"

    def test_persona_endpoint_invalid_persona(self, client: TestClient) -> None:
        response = client.get("/api/call-outcomes/brief-effectiveness/persona/not_a_persona")
        assert response.status_code == 404
        assert "Unknown persona" in response.json()["detail"]

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_scripts_endpoint_returns_200(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        mock_service.get_script_effectiveness.return_value = ScriptEffectivenessResponse()
        response = client.get("/api/call-outcomes/brief-effectiveness/scripts")
        assert response.status_code == 200
        data = response.json()
        assert "rows" in data

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_persona_endpoint_all_valid_personas(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """All 8 personas should be accepted."""
        mock_service.get_persona_effectiveness.return_value = PersonaEffectivenessDetail(
            persona_id="av_director",
        )
        personas = [
            "av_director", "ld_director", "technical_director", "simulation_director",
            "court_administrator", "corp_comms_director", "ehs_manager", "law_firm_it",
        ]
        for persona in personas:
            mock_service.get_persona_effectiveness.return_value = PersonaEffectivenessDetail(
                persona_id=persona,
            )
            response = client.get(f"/api/call-outcomes/brief-effectiveness/persona/{persona}")
            assert response.status_code == 200, f"Failed for {persona}"


# =============================================================================
# 11. Edge Cases & Graceful Degradation
# =============================================================================


class TestEdgeCases:
    def test_conversion_funnel_model_defaults(self) -> None:
        funnel = ConversionFunnel()
        assert funnel.total_briefs == 0
        assert funnel.connect_rate == 0.0
        assert funnel.meeting_rate == 0.0

    def test_quality_conversion_model_defaults(self) -> None:
        qc = QualityConversion()
        assert qc.total == 0
        assert qc.meetings == 0
        assert qc.rate == 0.0

    def test_phone_type_impact_model(self) -> None:
        impact = PhoneTypeImpact(phone_type="direct", dials=10, connections=5, meetings=2)
        assert impact.connect_rate == 0.0  # defaults, rates computed by service
        assert impact.phone_type == "direct"

    def test_tier_analytics_model(self) -> None:
        tier = TierAnalytics(tier="Tier 1")
        assert tier.avg_duration == 0.0
        assert tier.avg_score == 0.0

    def test_script_template_row_model(self) -> None:
        row = ScriptTemplateRow(persona="av_director", trigger="demo_request")
        assert row.sample_size_warning is False

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_missing_brief_json_sections(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """Briefs with missing brief_json sections should not crash."""
        brief = {
            "id": "b-1",
            "brief_quality": "HIGH",
            "brief_json": {},  # No contact, qualification, trigger, etc.
            "call_outcomes": [
                {"disposition": "connected", "result": "meeting_booked"},
            ],
        }
        mock_db.get_briefs_with_outcomes.return_value = [brief]
        result = service.get_brief_effectiveness()
        assert result.total_outcomes_linked == 1

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_null_brief_json(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """Briefs with null brief_json should not crash."""
        brief = {
            "id": "b-1",
            "brief_quality": "MEDIUM",
            "brief_json": None,
            "call_outcomes": [
                {"disposition": "voicemail", "result": "no_contact"},
            ],
        }
        mock_db.get_briefs_with_outcomes.return_value = [brief]
        result = service.get_brief_effectiveness()
        assert result.total_outcomes_linked == 1

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_empty_call_outcomes_list(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """Briefs with empty outcomes list should be counted but not linked."""
        brief = {
            "id": "b-1",
            "brief_quality": "LOW",
            "brief_json": {"contact": {"persona_id": "av_director"}},
            "call_outcomes": [],
        }
        mock_db.get_briefs_with_outcomes.return_value = [brief]
        result = service.get_brief_effectiveness()
        assert result.total_briefs_used == 1
        assert result.total_outcomes_linked == 0

    def test_brief_effectiveness_response_serialization(self) -> None:
        """BriefEffectivenessResponse should serialize cleanly to JSON-compatible dict."""
        response = BriefEffectivenessResponse(
            total_briefs_used=5,
            total_outcomes_linked=3,
            conversion_by_quality={
                "HIGH": QualityConversion(total=3, meetings=2, rate=66.7),
            },
            overall_funnel=ConversionFunnel(total_outcomes=3, connections=2, meetings_booked=2),
        )
        data = response.model_dump()
        assert data["total_briefs_used"] == 5
        assert data["conversion_by_quality"]["HIGH"]["total"] == 3
        assert data["overall_funnel"]["connections"] == 2

    def test_persona_effectiveness_detail_serialization(self) -> None:
        detail = PersonaEffectivenessDetail(
            persona_id="av_director",
            top_objections=[{"budget": 5}, {"timing": 3}],
        )
        data = detail.model_dump()
        assert data["persona_id"] == "av_director"
        assert data["top_objections"][0] == {"budget": 5}

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_tier_score_counted_once_per_brief_not_per_outcome(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """Tier avg_score should count each brief's score once, not once per outcome.

        Regression test: a brief with score=85 and 3 outcomes should contribute
        one score entry (85), not three (85, 85, 85). This matters when briefs
        have different outcome counts — the average would skew toward
        briefs with more outcomes.
        """
        # Brief A: score 85, 3 outcomes
        brief_a: dict[str, Any] = {
            "id": "b-1",
            "brief_quality": "HIGH",
            "brief_json": {
                "qualification": {"tier": "tier_1", "score": 85},
                "contact": {},
            },
            "call_outcomes": [
                {"disposition": "connected", "result": "meeting_booked"},
                {"disposition": "connected", "result": "follow_up_needed"},
                {"disposition": "connected", "result": "no_interest"},
            ],
        }
        # Brief B: score 65, 1 outcome
        brief_b: dict[str, Any] = {
            "id": "b-2",
            "brief_quality": "MEDIUM",
            "brief_json": {
                "qualification": {"tier": "tier_1", "score": 65},
                "contact": {},
            },
            "call_outcomes": [
                {"disposition": "voicemail", "result": "no_contact"},
            ],
        }
        mock_db.get_briefs_with_outcomes.return_value = [brief_a, brief_b]
        result = service.get_brief_effectiveness()

        # Find tier_1 analytics
        tier_1 = next(
            (t for t in result.tier_analytics if t.tier == "tier_1"), None
        )
        assert tier_1 is not None

        # Correct: avg of [85, 65] = 75.0 (one score per brief)
        # Bug would give: avg of [85, 85, 85, 65] = 80.0 (scores duplicated per outcome)
        assert tier_1.avg_score == 75.0
