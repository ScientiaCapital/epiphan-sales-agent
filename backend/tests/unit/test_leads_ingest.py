"""Tests for Lead Harvester ingest endpoint and harvester_mapper module.

PHONES ARE GOLD! Tests verify phone enrichment is prioritized.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.langgraph.states import QualificationTier
from app.services.langgraph.tools.harvester_mapper import (
    enrich_phone_numbers,
    get_best_phone,
    map_harvester_tier_to_score,
    map_harvester_to_lead,
)


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_harvester_leads():
    """Sample Harvester lead data."""
    return [
        {
            "external_id": "IPEDS_123456",
            "source": "ipeds_higher_ed",
            "company_name": "State University",
            "industry": "Higher Education",
            "employees": 5000,
            "city": "Boston",
            "state": "MA",
            "contact_name": "John Smith",
            "contact_title": "AV Director",
            "contact_email": "jsmith@stateuniversity.edu",
            "harvester_score": 85.0,
            "harvester_tier": "A",
            "direct_phone": "+1-617-555-1234",
            "work_phone": "+1-617-555-0000",
        },
        {
            "external_id": "IPEDS_789012",
            "source": "ipeds_higher_ed",
            "company_name": "Community College",
            "industry": "Higher Education",
            "employees": 500,
            "city": "Springfield",
            "state": "MA",
            "contact_name": "Jane Doe",
            "contact_title": "IT Director",
            "contact_email": "jdoe@commcollege.edu",
            "harvester_tier": "B",
        },
    ]


# =============================================================================
# Harvester Mapper Unit Tests
# =============================================================================


class TestMapHarvesterToLead:
    """Tests for map_harvester_to_lead function."""

    def test_basic_mapping(self):
        """Test basic field mapping."""
        lead = map_harvester_to_lead(
            external_id="TEST_123",
            source="ipeds_higher_ed",
            company_name="Test University",
            contact_email="test@university.edu",
            contact_name="John Smith",
            contact_title="AV Director",
        )

        assert lead.hubspot_id == "harvester_ipeds_higher_ed_TEST_123"
        assert lead.email == "test@university.edu"
        assert lead.first_name == "John"
        assert lead.last_name == "Smith"
        assert lead.company == "Test University"
        assert lead.title == "AV Director"

    def test_name_parsing_single_name(self):
        """Test name parsing with single name."""
        lead = map_harvester_to_lead(
            external_id="TEST_123",
            source="test",
            company_name="Test Co",
            contact_name="John",
        )

        assert lead.first_name == "John"
        assert lead.last_name is None

    def test_name_parsing_multi_part_last_name(self):
        """Test name parsing with multi-part last name."""
        lead = map_harvester_to_lead(
            external_id="TEST_123",
            source="test",
            company_name="Test Co",
            contact_name="John Van Der Berg",
        )

        assert lead.first_name == "John"
        assert lead.last_name == "Van Der Berg"

    def test_placeholder_email_when_missing(self):
        """Test placeholder email is generated when contact_email is None."""
        lead = map_harvester_to_lead(
            external_id="TEST_123",
            source="test",
            company_name="Test Co",
        )

        assert "@placeholder.harvester.local" in lead.email
        assert "TEST_123" in lead.email

    def test_phone_priority_direct_first(self):
        """Test best phone is direct dial when available. PHONES ARE GOLD!"""
        lead = map_harvester_to_lead(
            external_id="TEST_123",
            source="test",
            company_name="Test Co",
            direct_phone="+1-555-1234",
            mobile_phone="+1-555-5678",
            work_phone="+1-555-0000",
            company_phone="+1-555-9999",
        )

        assert lead.phone == "+1-555-1234"  # Direct phone is best

    def test_phone_priority_mobile_second(self):
        """Test mobile phone is used when direct is missing. PHONES ARE GOLD!"""
        lead = map_harvester_to_lead(
            external_id="TEST_123",
            source="test",
            company_name="Test Co",
            mobile_phone="+1-555-5678",
            work_phone="+1-555-0000",
        )

        assert lead.phone == "+1-555-5678"  # Mobile is second best

    def test_phone_priority_work_third(self):
        """Test work phone is used when direct/mobile missing. PHONES ARE GOLD!"""
        lead = map_harvester_to_lead(
            external_id="TEST_123",
            source="test",
            company_name="Test Co",
            work_phone="+1-555-0000",
            company_phone="+1-555-9999",
        )

        assert lead.phone == "+1-555-0000"

    def test_phone_priority_company_last(self):
        """Test company phone is fallback. PHONES ARE GOLD!"""
        lead = map_harvester_to_lead(
            external_id="TEST_123",
            source="test",
            company_name="Test Co",
            company_phone="+1-555-9999",
        )

        assert lead.phone == "+1-555-9999"


class TestMapHarvesterTierToScore:
    """Tests for map_harvester_tier_to_score function."""

    def test_numeric_score_passthrough(self):
        """Test numeric score is passed through."""
        assert map_harvester_tier_to_score(score=85.5) == 85
        assert map_harvester_tier_to_score(score=72.3) == 72

    def test_score_clamped_to_0_100(self):
        """Test score is clamped to valid range."""
        assert map_harvester_tier_to_score(score=-10) == 0
        assert map_harvester_tier_to_score(score=150) == 100

    def test_tier_a_mapping(self):
        """Test A tier maps to high score."""
        assert map_harvester_tier_to_score(tier="A") == 85
        assert map_harvester_tier_to_score(tier="a") == 85  # Case insensitive

    def test_tier_b_mapping(self):
        """Test B tier maps to medium-high score."""
        assert map_harvester_tier_to_score(tier="B") == 65

    def test_tier_c_mapping(self):
        """Test C tier maps to medium-low score."""
        assert map_harvester_tier_to_score(tier="C") == 45

    def test_tier_d_mapping(self):
        """Test D tier maps to low score."""
        assert map_harvester_tier_to_score(tier="D") == 20

    def test_unknown_tier_returns_zero(self):
        """Test unknown tier returns zero."""
        assert map_harvester_tier_to_score(tier="X") == 0
        assert map_harvester_tier_to_score(tier=None) == 0

    def test_numeric_score_takes_precedence(self):
        """Test numeric score takes precedence over tier."""
        assert map_harvester_tier_to_score(tier="A", score=50) == 50


class TestEnrichPhoneNumbers:
    """Tests for enrich_phone_numbers function. PHONES ARE GOLD!"""

    def test_apollo_direct_phone_extraction(self):
        """Test direct phone extraction from Apollo data."""
        apollo_data = {
            "phone_numbers": [
                {"sanitized_number": "+1-555-1234", "type": "work_direct"},
            ]
        }

        result = enrich_phone_numbers(apollo_data)

        assert result["direct_phone"] == "+1-555-1234"
        assert result["best_phone"] == "+1-555-1234"
        assert "apollo" in result["phone_source"]

    def test_apollo_mobile_phone_extraction(self):
        """Test mobile phone extraction from Apollo data."""
        apollo_data = {
            "phone_numbers": [
                {"sanitized_number": "+1-555-5678", "type": "mobile"},
            ]
        }

        result = enrich_phone_numbers(apollo_data)

        assert result["mobile_phone"] == "+1-555-5678"

    def test_apollo_work_phone_extraction(self):
        """Test work phone extraction from Apollo data."""
        apollo_data = {
            "phone_numbers": [
                {"sanitized_number": "+1-555-0000", "type": "work"},
            ]
        }

        result = enrich_phone_numbers(apollo_data)

        assert result["work_phone"] == "+1-555-0000"

    def test_apollo_company_phone_from_organization(self):
        """Test company phone from Apollo organization data."""
        apollo_data = {
            "phone_numbers": [],
            "organization": {"phone": "+1-555-9999"},
        }

        result = enrich_phone_numbers(apollo_data)

        assert result["company_phone"] == "+1-555-9999"

    def test_harvester_fallback_when_apollo_missing(self):
        """Test Harvester phones are used when Apollo doesn't have them."""
        result = enrich_phone_numbers(
            apollo_data=None,
            harvester_direct="+1-555-1234",
            harvester_mobile="+1-555-5678",
        )

        assert result["direct_phone"] == "+1-555-1234"
        assert result["mobile_phone"] == "+1-555-5678"
        assert "harvester" in result["phone_source"]

    def test_apollo_takes_priority_over_harvester(self):
        """Test Apollo phones take priority over Harvester."""
        apollo_data = {
            "phone_numbers": [
                {"sanitized_number": "+1-APOLLO-1234", "type": "work_direct"},
            ]
        }

        result = enrich_phone_numbers(
            apollo_data=apollo_data,
            harvester_direct="+1-HARVESTER-5678",
        )

        assert result["direct_phone"] == "+1-APOLLO-1234"

    def test_harvester_fills_gaps(self):
        """Test Harvester fills in phone types Apollo doesn't have."""
        apollo_data = {
            "phone_numbers": [
                {"sanitized_number": "+1-555-1234", "type": "work_direct"},
            ]
        }

        result = enrich_phone_numbers(
            apollo_data=apollo_data,
            harvester_mobile="+1-555-5678",
        )

        assert result["direct_phone"] == "+1-555-1234"  # From Apollo
        assert result["mobile_phone"] == "+1-555-5678"  # From Harvester

    def test_best_phone_priority_order(self):
        """Test best_phone follows correct priority. PHONES ARE GOLD!"""
        # Direct is best
        result = enrich_phone_numbers(
            apollo_data=None,
            harvester_direct="+1-DIRECT",
            harvester_mobile="+1-MOBILE",
            harvester_work="+1-WORK",
            harvester_company="+1-COMPANY",
        )
        assert result["best_phone"] == "+1-DIRECT"

        # Mobile is second
        result = enrich_phone_numbers(
            apollo_data=None,
            harvester_mobile="+1-MOBILE",
            harvester_work="+1-WORK",
            harvester_company="+1-COMPANY",
        )
        assert result["best_phone"] == "+1-MOBILE"

        # Work is third
        result = enrich_phone_numbers(
            apollo_data=None,
            harvester_work="+1-WORK",
            harvester_company="+1-COMPANY",
        )
        assert result["best_phone"] == "+1-WORK"

        # Company is last
        result = enrich_phone_numbers(
            apollo_data=None,
            harvester_company="+1-COMPANY",
        )
        assert result["best_phone"] == "+1-COMPANY"

    def test_empty_when_no_phones(self):
        """Test empty result when no phones available."""
        result = enrich_phone_numbers(apollo_data=None)

        assert result["best_phone"] is None
        assert result["phone_source"] is None


class TestGetBestPhone:
    """Tests for get_best_phone function. PHONES ARE GOLD!"""

    def test_returns_direct_first(self):
        """Test direct phone returned first."""
        assert get_best_phone(
            direct_phone="+1-DIRECT",
            mobile_phone="+1-MOBILE",
            work_phone="+1-WORK",
            company_phone="+1-COMPANY",
        ) == "+1-DIRECT"

    def test_returns_mobile_when_no_direct(self):
        """Test mobile phone returned when no direct."""
        assert get_best_phone(
            mobile_phone="+1-MOBILE",
            work_phone="+1-WORK",
            company_phone="+1-COMPANY",
        ) == "+1-MOBILE"

    def test_returns_work_when_no_mobile(self):
        """Test work phone returned when no mobile."""
        assert get_best_phone(
            work_phone="+1-WORK",
            company_phone="+1-COMPANY",
        ) == "+1-WORK"

    def test_returns_company_as_fallback(self):
        """Test company phone as fallback."""
        assert get_best_phone(company_phone="+1-COMPANY") == "+1-COMPANY"

    def test_returns_none_when_no_phones(self):
        """Test None when no phones available."""
        assert get_best_phone() is None


# =============================================================================
# Ingest Endpoint Integration Tests
# =============================================================================


class TestLeadIngestEndpoint:
    """Tests for POST /api/leads/ingest endpoint."""

    def test_ingest_success_with_qualification(
        self, client, sample_harvester_leads
    ):
        """Test successful ingest with qualification scoring."""
        mock_qual_result = {
            "total_score": 75.0,
            "tier": QualificationTier.TIER_1,
            "score_breakdown": {
                "company_size": {
                    "category": "Large Enterprise",
                    "raw_score": 10,
                    "weighted_score": 25.0,
                    "reason": "5000 employees",
                    "confidence": 1.0,
                },
                "industry_vertical": {
                    "category": "Higher Education",
                    "raw_score": 10,
                    "weighted_score": 20.0,
                    "reason": "Target vertical",
                    "confidence": 1.0,
                },
                "use_case_fit": {
                    "category": "Lecture Capture",
                    "raw_score": 9,
                    "weighted_score": 22.5,
                    "reason": "AV Director persona",
                    "confidence": 0.9,
                },
                "tech_stack_signals": {
                    "category": "Unknown",
                    "raw_score": 5,
                    "weighted_score": 7.5,
                    "reason": "No tech stack data",
                    "confidence": 0.4,
                },
                "buying_authority": {
                    "category": "Decision Maker",
                    "raw_score": 10,
                    "weighted_score": 15.0,
                    "reason": "Director level",
                    "confidence": 0.9,
                },
            },
            "confidence": 0.85,
            "next_action": {
                "action_type": "priority_sequence",
                "description": "High priority outreach",
                "priority": "high",
                "ae_involvement": True,
                "missing_info": [],
            },
            "missing_info": [],
            "persona_match": "AV Director",
        }

        with (
            patch(
                "app.api.routes.leads._qualification_agent.run",
                new_callable=AsyncMock,
            ) as mock_qual,
            patch(
                "app.api.routes.leads.apollo_client.enrich_contact",
                new_callable=AsyncMock,
            ) as mock_apollo,
        ):
            mock_qual.return_value = mock_qual_result
            mock_apollo.return_value = {
                "phone_numbers": [
                    {"sanitized_number": "+1-617-555-9999", "type": "work_direct"},
                ]
            }

            response = client.post(
                "/api/leads/ingest",
                json={"leads": sample_harvester_leads[:1]},
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["tier"] == "tier_1"
        assert data["results"][0]["total_score"] == 75.0

    def test_ingest_phone_enrichment_priority(
        self, client, sample_harvester_leads
    ):
        """Test phone enrichment is prioritized. PHONES ARE GOLD!"""
        mock_qual_result = {
            "total_score": 50.0,
            "tier": QualificationTier.TIER_2,
            "score_breakdown": {
                "company_size": {"category": "SMB", "raw_score": 4, "weighted_score": 10.0, "reason": "500 employees", "confidence": 1.0},
                "industry_vertical": {"category": "Higher Ed", "raw_score": 10, "weighted_score": 20.0, "reason": "Target vertical", "confidence": 1.0},
                "use_case_fit": {"category": "Unknown", "raw_score": 5, "weighted_score": 12.5, "reason": "No persona match", "confidence": 0.5},
                "tech_stack_signals": {"category": "Unknown", "raw_score": 5, "weighted_score": 7.5, "reason": "No data", "confidence": 0.4},
                "buying_authority": {"category": "Manager", "raw_score": 7, "weighted_score": 10.5, "reason": "IT Director", "confidence": 0.8},
            },
            "confidence": 0.7,
            "next_action": {"action_type": "standard_sequence", "description": "Standard outreach", "priority": "medium", "ae_involvement": False, "missing_info": []},
            "missing_info": [],
            "persona_match": None,
        }

        with (
            patch(
                "app.api.routes.leads._qualification_agent.run",
                new_callable=AsyncMock,
            ) as mock_qual,
            patch(
                "app.api.routes.leads.apollo_client.enrich_contact",
                new_callable=AsyncMock,
            ) as mock_apollo,
        ):
            mock_qual.return_value = mock_qual_result
            # Apollo returns a mobile phone
            mock_apollo.return_value = {
                "phone_numbers": [
                    {"sanitized_number": "+1-APOLLO-MOBILE", "type": "mobile"},
                ]
            }

            # Lead has a direct phone from harvester
            lead_with_phone = {
                **sample_harvester_leads[1],
                "direct_phone": "+1-HARVESTER-DIRECT",
            }

            response = client.post(
                "/api/leads/ingest",
                json={"leads": [lead_with_phone]},
            )

        assert response.status_code == 200
        data = response.json()
        result = data["results"][0]

        # Should have Harvester direct (Apollo didn't have one)
        assert result["direct_phone"] == "+1-HARVESTER-DIRECT"
        # Should have Apollo mobile
        assert result["mobile_phone"] == "+1-APOLLO-MOBILE"
        # Best phone should be direct
        assert result["best_phone"] == "+1-HARVESTER-DIRECT"

    def test_ingest_returns_summary_with_phone_metrics(
        self, client, sample_harvester_leads
    ):
        """Test summary includes phone metrics. PHONES ARE GOLD!"""
        mock_qual_result = {
            "total_score": 75.0,
            "tier": QualificationTier.TIER_1,
            "score_breakdown": {
                "company_size": {"category": "Enterprise", "raw_score": 10, "weighted_score": 25.0, "reason": "Large", "confidence": 1.0},
                "industry_vertical": {"category": "Higher Ed", "raw_score": 10, "weighted_score": 20.0, "reason": "Target", "confidence": 1.0},
                "use_case_fit": {"category": "Lecture Capture", "raw_score": 9, "weighted_score": 22.5, "reason": "Good fit", "confidence": 0.9},
                "tech_stack_signals": {"category": "Unknown", "raw_score": 5, "weighted_score": 7.5, "reason": "No data", "confidence": 0.4},
                "buying_authority": {"category": "Decision Maker", "raw_score": 10, "weighted_score": 15.0, "reason": "Director", "confidence": 0.9},
            },
            "confidence": 0.85,
            "next_action": {"action_type": "priority_sequence", "description": "Priority", "priority": "high", "ae_involvement": True, "missing_info": []},
            "missing_info": [],
            "persona_match": "AV Director",
        }

        with (
            patch(
                "app.api.routes.leads._qualification_agent.run",
                new_callable=AsyncMock,
            ) as mock_qual,
            patch(
                "app.api.routes.leads.apollo_client.enrich_contact",
                new_callable=AsyncMock,
            ) as mock_apollo,
        ):
            mock_qual.return_value = mock_qual_result
            mock_apollo.return_value = {"phone_numbers": []}

            response = client.post(
                "/api/leads/ingest",
                json={"leads": sample_harvester_leads},
            )

        assert response.status_code == 200
        data = response.json()
        summary = data["summary"]

        # Check phone metrics exist
        assert "leads_with_direct_phone" in summary
        assert "leads_with_any_phone" in summary
        assert "leads_needing_phone_research" in summary

        # First lead has direct_phone, second doesn't
        assert summary["leads_with_direct_phone"] == 1
        assert summary["leads_with_any_phone"] >= 1

    def test_ingest_handles_partial_failure(
        self, client, sample_harvester_leads
    ):
        """Test batch continues when one lead fails."""
        mock_qual_result = {
            "total_score": 50.0,
            "tier": QualificationTier.TIER_2,
            "score_breakdown": {
                "company_size": {"category": "SMB", "raw_score": 4, "weighted_score": 10.0, "reason": "Small", "confidence": 1.0},
                "industry_vertical": {"category": "Higher Ed", "raw_score": 10, "weighted_score": 20.0, "reason": "Target", "confidence": 1.0},
                "use_case_fit": {"category": "Unknown", "raw_score": 5, "weighted_score": 12.5, "reason": "Unknown", "confidence": 0.5},
                "tech_stack_signals": {"category": "Unknown", "raw_score": 5, "weighted_score": 7.5, "reason": "No data", "confidence": 0.4},
                "buying_authority": {"category": "Manager", "raw_score": 7, "weighted_score": 10.5, "reason": "Director", "confidence": 0.8},
            },
            "confidence": 0.7,
            "next_action": {"action_type": "standard_sequence", "description": "Standard", "priority": "medium", "ae_involvement": False, "missing_info": []},
            "missing_info": [],
            "persona_match": None,
        }

        with (
            patch(
                "app.api.routes.leads._qualification_agent.run",
                new_callable=AsyncMock,
            ) as mock_qual,
            patch(
                "app.api.routes.leads.apollo_client.enrich_contact",
                new_callable=AsyncMock,
            ) as mock_apollo,
        ):
            # First fails, second succeeds
            mock_qual.side_effect = [
                Exception("API Error"),
                mock_qual_result,
            ]
            mock_apollo.return_value = {"phone_numbers": []}

            response = client.post(
                "/api/leads/ingest",
                json={"leads": sample_harvester_leads},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["error"] is not None
        assert data["results"][1]["error"] is None
        assert data["summary"]["failed"] == 1
        assert data["summary"]["qualified"] == 1

    def test_ingest_preserves_harvester_phones_on_error(
        self, client, sample_harvester_leads
    ):
        """Test Harvester phones preserved even when enrichment fails. PHONES ARE GOLD!"""
        with (
            patch(
                "app.api.routes.leads._qualification_agent.run",
                new_callable=AsyncMock,
            ) as mock_qual,
            patch(
                "app.api.routes.leads.apollo_client.enrich_contact",
                new_callable=AsyncMock,
            ) as mock_apollo,
        ):
            mock_qual.side_effect = Exception("Qualification failed")
            mock_apollo.side_effect = Exception("Apollo failed")

            response = client.post(
                "/api/leads/ingest",
                json={"leads": sample_harvester_leads[:1]},
            )

        assert response.status_code == 200
        data = response.json()
        result = data["results"][0]

        # Should still have the Harvester phones
        assert result["direct_phone"] == "+1-617-555-1234"
        assert result["work_phone"] == "+1-617-555-0000"
        assert result["best_phone"] == "+1-617-555-1234"
        assert result["phone_source"] == "harvester"

    def test_ingest_skip_enrichment_uses_harvester_data(
        self, client, sample_harvester_leads
    ):
        """Test skip_enrichment flag uses only Harvester data."""
        mock_qual_result = {
            "total_score": 60.0,
            "tier": QualificationTier.TIER_2,
            "score_breakdown": {
                "company_size": {"category": "Enterprise", "raw_score": 8, "weighted_score": 20.0, "reason": "Large", "confidence": 0.5},
                "industry_vertical": {"category": "Higher Ed", "raw_score": 10, "weighted_score": 20.0, "reason": "Target", "confidence": 0.8},
                "use_case_fit": {"category": "Unknown", "raw_score": 5, "weighted_score": 12.5, "reason": "Unknown", "confidence": 0.3},
                "tech_stack_signals": {"category": "Unknown", "raw_score": 5, "weighted_score": 7.5, "reason": "No data", "confidence": 0.3},
                "buying_authority": {"category": "Unknown", "raw_score": 5, "weighted_score": 7.5, "reason": "Unknown", "confidence": 0.3},
            },
            "confidence": 0.5,
            "next_action": {"action_type": "standard_sequence", "description": "Standard", "priority": "medium", "ae_involvement": False, "missing_info": ["tech_stack", "buying_authority"]},
            "missing_info": ["tech_stack", "buying_authority"],
            "persona_match": None,
        }

        with (
            patch(
                "app.api.routes.leads._qualification_agent.run",
                new_callable=AsyncMock,
            ) as mock_qual,
            patch(
                "app.api.routes.leads.apollo_client.tiered_enrich",
                new_callable=AsyncMock,
            ) as mock_tiered,
        ):
            mock_qual.return_value = mock_qual_result
            # Mock tiered_enrich to avoid actual API calls
            from app.services.enrichment.apollo import TieredEnrichmentResult
            mock_tiered.return_value = TieredEnrichmentResult(found=False, credits_used=0)

            client.post(
                "/api/leads/ingest",
                json={
                    "leads": sample_harvester_leads[:1],
                    "enrich": False,
                },
            )

            # With enrich=False, qualification agent gets skip_enrichment=True
            mock_qual.assert_called_once()
            call_kwargs = mock_qual.call_args[1]
            assert call_kwargs["skip_enrichment"] is True

    def test_ingest_validates_required_fields(self, client):
        """Test validation of required fields."""
        # Missing external_id
        response = client.post(
            "/api/leads/ingest",
            json={
                "leads": [
                    {
                        "source": "test",
                        "company_name": "Test Co",
                    }
                ]
            },
        )

        assert response.status_code == 422

    def test_ingest_respects_concurrency_limit(
        self, client, sample_harvester_leads
    ):
        """Test concurrency limit is respected."""
        mock_qual_result = {
            "total_score": 50.0,
            "tier": QualificationTier.TIER_2,
            "score_breakdown": {
                "company_size": {"category": "SMB", "raw_score": 4, "weighted_score": 10.0, "reason": "Small", "confidence": 1.0},
                "industry_vertical": {"category": "Higher Ed", "raw_score": 10, "weighted_score": 20.0, "reason": "Target", "confidence": 1.0},
                "use_case_fit": {"category": "Unknown", "raw_score": 5, "weighted_score": 12.5, "reason": "Unknown", "confidence": 0.5},
                "tech_stack_signals": {"category": "Unknown", "raw_score": 5, "weighted_score": 7.5, "reason": "No data", "confidence": 0.4},
                "buying_authority": {"category": "Manager", "raw_score": 7, "weighted_score": 10.5, "reason": "Director", "confidence": 0.8},
            },
            "confidence": 0.7,
            "next_action": {"action_type": "standard_sequence", "description": "Standard", "priority": "medium", "ae_involvement": False, "missing_info": []},
            "missing_info": [],
            "persona_match": None,
        }

        with (
            patch(
                "app.api.routes.leads._qualification_agent.run",
                new_callable=AsyncMock,
            ) as mock_qual,
            patch(
                "app.api.routes.leads.apollo_client.enrich_contact",
                new_callable=AsyncMock,
            ) as mock_apollo,
        ):
            mock_qual.return_value = mock_qual_result
            mock_apollo.return_value = {"phone_numbers": []}

            response = client.post(
                "/api/leads/ingest",
                json={
                    "leads": sample_harvester_leads,
                    "concurrency": 1,
                },
            )

        assert response.status_code == 200
        assert len(response.json()["results"]) == 2

    def test_ingest_batch_id_generation(self, client, sample_harvester_leads):
        """Test batch ID is generated if not provided."""
        mock_qual_result = {
            "total_score": 50.0,
            "tier": QualificationTier.TIER_2,
            "score_breakdown": {
                "company_size": {"category": "SMB", "raw_score": 4, "weighted_score": 10.0, "reason": "Small", "confidence": 1.0},
                "industry_vertical": {"category": "Higher Ed", "raw_score": 10, "weighted_score": 20.0, "reason": "Target", "confidence": 1.0},
                "use_case_fit": {"category": "Unknown", "raw_score": 5, "weighted_score": 12.5, "reason": "Unknown", "confidence": 0.5},
                "tech_stack_signals": {"category": "Unknown", "raw_score": 5, "weighted_score": 7.5, "reason": "No data", "confidence": 0.4},
                "buying_authority": {"category": "Manager", "raw_score": 7, "weighted_score": 10.5, "reason": "Director", "confidence": 0.8},
            },
            "confidence": 0.7,
            "next_action": {"action_type": "standard_sequence", "description": "Standard", "priority": "medium", "ae_involvement": False, "missing_info": []},
            "missing_info": [],
            "persona_match": None,
        }

        with (
            patch(
                "app.api.routes.leads._qualification_agent.run",
                new_callable=AsyncMock,
            ) as mock_qual,
            patch(
                "app.api.routes.leads.apollo_client.enrich_contact",
                new_callable=AsyncMock,
            ) as mock_apollo,
        ):
            mock_qual.return_value = mock_qual_result
            mock_apollo.return_value = {"phone_numbers": []}

            response = client.post(
                "/api/leads/ingest",
                json={"leads": sample_harvester_leads[:1]},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"].startswith("batch_")

    def test_ingest_custom_batch_id(self, client, sample_harvester_leads):
        """Test custom batch ID is preserved."""
        mock_qual_result = {
            "total_score": 50.0,
            "tier": QualificationTier.TIER_2,
            "score_breakdown": {
                "company_size": {"category": "SMB", "raw_score": 4, "weighted_score": 10.0, "reason": "Small", "confidence": 1.0},
                "industry_vertical": {"category": "Higher Ed", "raw_score": 10, "weighted_score": 20.0, "reason": "Target", "confidence": 1.0},
                "use_case_fit": {"category": "Unknown", "raw_score": 5, "weighted_score": 12.5, "reason": "Unknown", "confidence": 0.5},
                "tech_stack_signals": {"category": "Unknown", "raw_score": 5, "weighted_score": 7.5, "reason": "No data", "confidence": 0.4},
                "buying_authority": {"category": "Manager", "raw_score": 7, "weighted_score": 10.5, "reason": "Director", "confidence": 0.8},
            },
            "confidence": 0.7,
            "next_action": {"action_type": "standard_sequence", "description": "Standard", "priority": "medium", "ae_involvement": False, "missing_info": []},
            "missing_info": [],
            "persona_match": None,
        }

        with (
            patch(
                "app.api.routes.leads._qualification_agent.run",
                new_callable=AsyncMock,
            ) as mock_qual,
            patch(
                "app.api.routes.leads.apollo_client.enrich_contact",
                new_callable=AsyncMock,
            ) as mock_apollo,
        ):
            mock_qual.return_value = mock_qual_result
            mock_apollo.return_value = {"phone_numbers": []}

            response = client.post(
                "/api/leads/ingest",
                json={
                    "leads": sample_harvester_leads[:1],
                    "batch_id": "my_custom_batch_123",
                },
            )

        assert response.status_code == 200
        assert response.json()["batch_id"] == "my_custom_batch_123"

    def test_ingest_tier_distribution_in_summary(
        self, client, sample_harvester_leads
    ):
        """Test tier distribution is tracked in summary."""
        tier_1_result = {
            "total_score": 75.0,
            "tier": QualificationTier.TIER_1,
            "score_breakdown": {
                "company_size": {"category": "Enterprise", "raw_score": 10, "weighted_score": 25.0, "reason": "Large", "confidence": 1.0},
                "industry_vertical": {"category": "Higher Ed", "raw_score": 10, "weighted_score": 20.0, "reason": "Target", "confidence": 1.0},
                "use_case_fit": {"category": "Lecture Capture", "raw_score": 9, "weighted_score": 22.5, "reason": "Good fit", "confidence": 0.9},
                "tech_stack_signals": {"category": "Unknown", "raw_score": 5, "weighted_score": 7.5, "reason": "No data", "confidence": 0.4},
                "buying_authority": {"category": "Decision Maker", "raw_score": 10, "weighted_score": 15.0, "reason": "Director", "confidence": 0.9},
            },
            "confidence": 0.85,
            "next_action": {"action_type": "priority_sequence", "description": "Priority", "priority": "high", "ae_involvement": True, "missing_info": []},
            "missing_info": [],
            "persona_match": "AV Director",
        }
        tier_2_result = {
            "total_score": 55.0,
            "tier": QualificationTier.TIER_2,
            "score_breakdown": {
                "company_size": {"category": "SMB", "raw_score": 4, "weighted_score": 10.0, "reason": "Small", "confidence": 1.0},
                "industry_vertical": {"category": "Higher Ed", "raw_score": 10, "weighted_score": 20.0, "reason": "Target", "confidence": 1.0},
                "use_case_fit": {"category": "Unknown", "raw_score": 5, "weighted_score": 12.5, "reason": "Unknown", "confidence": 0.5},
                "tech_stack_signals": {"category": "Unknown", "raw_score": 5, "weighted_score": 7.5, "reason": "No data", "confidence": 0.4},
                "buying_authority": {"category": "Manager", "raw_score": 7, "weighted_score": 10.5, "reason": "Director", "confidence": 0.8},
            },
            "confidence": 0.7,
            "next_action": {"action_type": "standard_sequence", "description": "Standard", "priority": "medium", "ae_involvement": False, "missing_info": []},
            "missing_info": [],
            "persona_match": None,
        }

        with (
            patch(
                "app.api.routes.leads._qualification_agent.run",
                new_callable=AsyncMock,
            ) as mock_qual,
            patch(
                "app.api.routes.leads.apollo_client.enrich_contact",
                new_callable=AsyncMock,
            ) as mock_apollo,
        ):
            mock_qual.side_effect = [tier_1_result, tier_2_result]
            mock_apollo.return_value = {"phone_numbers": []}

            response = client.post(
                "/api/leads/ingest",
                json={"leads": sample_harvester_leads},
            )

        assert response.status_code == 200
        summary = response.json()["summary"]
        assert summary["tier_1"] == 1
        assert summary["tier_2"] == 1
        assert summary["tier_3"] == 0
        assert summary["not_icp"] == 0
