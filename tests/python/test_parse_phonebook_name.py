"""Unit tests for parse_phonebook_name.

This parser runs on every raw phonebook entry before DB ingestion. Regressions
here silently drop wing/unit/role data that can never be recovered from the source.
"""
import pytest
from parse_phonebook_name import parse_phonebook_name, _find_unit, _find_role, _clean_spaces


# ---------------------------------------------------------------------------
# _find_unit — internal unit parser
# ---------------------------------------------------------------------------

class TestFindUnit:
    def test_wing_dash_unit(self):
        wing, unit, _, _ = _find_unit("A-203 Owner")
        assert wing == "A"
        assert unit == "203"

    def test_wing_space_unit(self):
        wing, unit, _, _ = _find_unit("B 304 Tenant")
        assert wing == "B"
        assert unit == "304"

    def test_flat_keyword(self):
        wing, unit, _, _ = _find_unit("Flat 1203 Resident")
        assert wing is None
        assert unit == "1203"

    def test_wing_word_format(self):
        wing, unit, _, _ = _find_unit("C Wing 502")
        assert wing == "C"
        assert unit == "502"

    def test_no_unit(self):
        wing, unit, _, _ = _find_unit("John Smith")
        assert wing is None
        assert unit is None


class TestFindRole:
    def test_owner(self):
        role, _, _ = _find_role("A-101 Owner")
        assert role == "owner"

    def test_tenant(self):
        role, _, _ = _find_role("B-202 Tenant Rohan")
        assert role == "tenant"

    def test_broker(self):
        role, _, _ = _find_role("Sanjay Broker")
        assert role == "broker"

    def test_no_role(self):
        role, _, _ = _find_role("Priya Sharma")
        assert role is None

    def test_case_insensitive(self):
        role, _, _ = _find_role("OWNER of flat 101")
        assert role == "owner"


# ---------------------------------------------------------------------------
# parse_phonebook_name — integration
# ---------------------------------------------------------------------------

class TestParsePhonebookName:
    """Pass empty building_codes={} to avoid filesystem reads in unit tests."""

    def test_full_structured_entry(self):
        result = parse_phonebook_name("IH A-203 Owner Rohan Mehta", building_codes={})
        assert result["parsed_wing"] == "A"
        assert result["parsed_unit_number"] == "203"
        assert result["parsed_role"] == "owner"
        assert "Rohan Mehta" in result["cleaned_display_name"]

    def test_display_name_strips_hints(self):
        result = parse_phonebook_name("B-304 Tenant Priya", building_codes={})
        name = result["cleaned_display_name"]
        assert "304" not in name
        assert "Tenant" not in name
        assert "Priya" in name

    def test_empty_string(self):
        result = parse_phonebook_name("", building_codes={})
        assert result["cleaned_display_name"] == ""
        # Function returns empty string "" for absent fields, not Python None
        assert result["parsed_wing"] == ""
        assert result["parsed_unit_number"] == ""
        assert result["needs_review"] is True

    def test_none_input(self):
        result = parse_phonebook_name(None, building_codes={})
        assert result["needs_review"] is True

    def test_unknown_name_flagged(self):
        result = parse_phonebook_name("unknown", building_codes={})
        assert result["needs_review"] is True
        assert "unknown_name" in (result.get("parsed_tags") or [])

    def test_na_name_flagged(self):
        result = parse_phonebook_name("n/a", building_codes={})
        assert result["needs_review"] is True

    def test_confidence_high_with_full_data(self):
        result = parse_phonebook_name("C-502 Owner Amit Shah", building_codes={})
        assert result["parse_confidence"] >= 0.70

    def test_confidence_low_without_unit(self):
        result = parse_phonebook_name("Just a name", building_codes={})
        # No building, no unit, no role → confidence stays low
        assert result["parse_confidence"] < 0.70

    def test_wing_uppercase_normalised(self):
        result = parse_phonebook_name("a-101 Owner Kavita", building_codes={})
        assert result["parsed_wing"] == "A"

    def test_flat_keyword_no_wing(self):
        result = parse_phonebook_name("Flat 1203 Nisha", building_codes={})
        assert result["parsed_wing"] == ""  # no wing present, returns "" not None
        assert result["parsed_unit_number"] == "1203"

    def test_building_code_lookup(self):
        codes = {"IH": {"code": "IH", "building_name": "Imperial Heights"}}
        result = parse_phonebook_name("IH B-405 Owner", building_codes=codes)
        assert result["parsed_building_code"] == "IH"
        assert result["parsed_building_name"] == "Imperial Heights"

    def test_original_name_not_mutated(self):
        raw = "A-101 Owner Rohan"
        result = parse_phonebook_name(raw, building_codes={})
        assert raw == "A-101 Owner Rohan"  # caller's value unchanged


# ---------------------------------------------------------------------------
# _clean_spaces — helper
# ---------------------------------------------------------------------------

class TestCleanSpaces:
    def test_trims_edges(self):
        assert _clean_spaces("  hello  ") == "hello"

    def test_collapses_internal(self):
        assert _clean_spaces("hello   world") == "hello world"

    def test_strips_trailing_dash(self):
        assert _clean_spaces("hello -") == "hello"
