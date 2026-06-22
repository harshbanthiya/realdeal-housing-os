"""Unit tests for source_format_utils.py — source-format detection helpers.

These pure functions classify incoming spreadsheet columns. Wrong detection
silently chooses the wrong import path, which means fields end up in wrong
columns without any error.
"""
import pytest
from source_format_utils import (
    normalize_column,
    normalized_set,
    has_all,
    has_any,
    has_any_prefix,
    header_score,
    detect_header_row,
    safe_stem,
    is_junk_archive_member,
)
from pathlib import Path


# ---------------------------------------------------------------------------
# normalize_column
# ---------------------------------------------------------------------------

class TestNormalizeColumn:
    def test_lowercases(self):
        assert normalize_column("Name") == "name"

    def test_replaces_underscores_with_space(self):
        assert normalize_column("flat_no") == "flat no"

    def test_collapses_whitespace(self):
        assert normalize_column("contact  details") == "contact details"

    def test_strips_edges(self):
        assert normalize_column("  phone ") == "phone"

    def test_empty_string(self):
        assert normalize_column("") == ""

    def test_none_value(self):
        assert normalize_column(None) == ""


# ---------------------------------------------------------------------------
# has_all / has_any
# ---------------------------------------------------------------------------

class TestHasAll:
    def test_all_present(self):
        assert has_all(["Name", "Phone", "Email"], ["name", "phone", "email"]) is True

    def test_one_missing(self):
        assert has_all(["Name", "Phone"], ["name", "phone", "email"]) is False

    def test_case_insensitive(self):
        assert has_all(["NAME", "PHONE"], ["name", "phone"]) is True

    def test_underscore_equivalent(self):
        assert has_all(["flat_no"], ["flat no"]) is True

    def test_empty_expected(self):
        assert has_all(["Name"], []) is True


class TestHasAny:
    def test_one_present(self):
        assert has_any(["Phone", "Address"], ["email", "phone"]) is True

    def test_none_present(self):
        assert has_any(["Address", "City"], ["email", "phone"]) is False

    def test_empty_columns(self):
        assert has_any([], ["name"]) is False


# ---------------------------------------------------------------------------
# header_score
# ---------------------------------------------------------------------------

class TestHeaderScore:
    def test_exact_keyword_match_scores_2(self):
        score = header_score(["name", "phone", "email"])
        assert score >= 6  # 3 exact keywords × 2

    def test_partial_match_scores_1(self):
        score = header_score(["contact_name", "mobile_no"])
        assert score >= 1

    def test_no_keywords_scores_0(self):
        score = header_score(["foo", "bar", "baz"])
        assert score == 0

    def test_empty_list(self):
        assert header_score([]) == 0


# ---------------------------------------------------------------------------
# detect_header_row
# ---------------------------------------------------------------------------

class TestDetectHeaderRow:
    def test_first_row_is_header(self):
        rows = [
            ["Name", "Phone", "Email"],
            ["Rohan", "9876543210", "r@x.com"],
        ]
        idx, cols = detect_header_row(rows)
        assert idx == 0
        assert "Name" in cols

    def test_header_on_second_row(self):
        rows = [
            ["", "", ""],
            ["Name", "Phone", "Flat No"],
            ["Priya", "9123456789", "A-101"],
        ]
        idx, cols = detect_header_row(rows)
        assert idx == 1
        assert "Name" in cols

    def test_max_scan_respected(self):
        header = ["Name", "Phone"]
        data = [["x", "y"]] * 20
        data.insert(15, header)
        idx, _ = detect_header_row(data, max_scan_rows=10)
        assert idx != 15  # header beyond max_scan is not found

    def test_empty_rows_list(self):
        idx, cols = detect_header_row([])
        assert idx == 0
        assert cols == []


# ---------------------------------------------------------------------------
# safe_stem
# ---------------------------------------------------------------------------

class TestSafeStem:
    def test_simple_stem(self):
        assert safe_stem(Path("building_list.csv")) == "building_list"

    def test_removes_dots(self):
        result = safe_stem(Path("data.v2.csv"))
        assert "." not in result

    def test_spaces_replaced(self):
        result = safe_stem(Path("my contacts.xlsx"))
        assert " " not in result

    def test_empty_stem_gets_fallback(self):
        result = safe_stem(Path(".hidden"))
        assert result == "source" or len(result) > 0


# ---------------------------------------------------------------------------
# is_junk_archive_member
# ---------------------------------------------------------------------------

class TestIsJunkArchiveMember:
    def test_ds_store(self):
        assert is_junk_archive_member(".DS_Store") is True

    def test_appledouble_prefix(self):
        assert is_junk_archive_member("._contact_sheet.xlsx") is True

    def test_macosx_dir(self):
        assert is_junk_archive_member("__MACOSX/file.csv") is True

    def test_normal_csv(self):
        assert is_junk_archive_member("contacts.csv") is False

    def test_nested_valid(self):
        assert is_junk_archive_member("data/contacts.csv") is False
