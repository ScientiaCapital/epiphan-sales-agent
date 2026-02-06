"""Tests for Clay phone merging into the phone priority system.

PHONES ARE GOLD! Priority: Apollo > Harvester > Clay.
Clay is the tertiary fallback — it only fills gaps.
"""

from app.services.langgraph.tools.harvester_mapper import enrich_phone_numbers


class TestClayPhoneMerging:
    """Tests for Clay as the third phone source."""

    def test_clay_phones_fill_gap(self) -> None:
        """When Apollo and Harvester have no phones, Clay fills the gap."""
        result = enrich_phone_numbers(
            apollo_data=None,
            clay_phones=[
                {"number": "+14155551234", "type": "work_direct"},
                {"number": "+14155555678", "type": "mobile"},
            ],
        )
        assert result["direct_phone"] == "+14155551234"
        assert result["mobile_phone"] == "+14155555678"
        assert result["best_phone"] == "+14155551234"
        assert "clay" in result["phone_source"]

    def test_clay_phones_lower_priority_than_apollo(self) -> None:
        """Apollo phone wins over Clay phone for the same type."""
        result = enrich_phone_numbers(
            apollo_data={
                "phone_numbers": [
                    {"number": "+1-apollo-direct", "type": "work_direct"},
                ],
            },
            clay_phones=[
                {"number": "+1-clay-direct", "type": "work_direct"},
                {"number": "+1-clay-mobile", "type": "mobile"},
            ],
        )
        # Apollo wins for direct
        assert result["direct_phone"] == "+1-apollo-direct"
        # Clay fills the mobile gap
        assert result["mobile_phone"] == "+1-clay-mobile"
        assert "apollo" in result["phone_source"]
        assert "clay" in result["phone_source"]

    def test_clay_phones_deduplication(self) -> None:
        """Same phone type from Apollo and Clay — Apollo kept, Clay ignored."""
        result = enrich_phone_numbers(
            apollo_data={
                "phone_numbers": [
                    {"number": "+14155551111", "type": "mobile"},
                ],
            },
            clay_phones=[
                {"number": "+14155552222", "type": "mobile"},
            ],
        )
        # Apollo's mobile wins
        assert result["mobile_phone"] == "+14155551111"
        # Clay's mobile is ignored (slot already filled)
        assert "clay" not in (result["phone_source"] or "")

    def test_clay_phones_none_param(self) -> None:
        """Backward compatible — clay_phones=None works like before."""
        result = enrich_phone_numbers(
            apollo_data=None,
            harvester_direct="+1-harv-direct",
            clay_phones=None,
        )
        assert result["direct_phone"] == "+1-harv-direct"
        assert result["phone_source"] == "harvester"

    def test_clay_phones_multiple_types(self) -> None:
        """Multiple Clay phone types are all used when slots are empty."""
        result = enrich_phone_numbers(
            apollo_data=None,
            clay_phones=[
                {"number": "+1-direct", "type": "work_direct"},
                {"number": "+1-mobile", "type": "mobile"},
                {"number": "+1-work", "type": "work"},
                {"number": "+1-hq", "type": "work_hq"},
            ],
        )
        assert result["direct_phone"] == "+1-direct"
        assert result["mobile_phone"] == "+1-mobile"
        assert result["work_phone"] == "+1-work"
        assert result["company_phone"] == "+1-hq"
        assert result["best_phone"] == "+1-direct"

    def test_clay_phones_empty_list(self) -> None:
        """Empty list treated same as None — no phones from Clay."""
        result = enrich_phone_numbers(
            apollo_data=None,
            clay_phones=[],
        )
        assert result["best_phone"] is None
        assert result["phone_source"] is None
