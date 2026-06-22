"""End-to-end fixture test for clean_contacts.clean_contacts().

Provides a deterministic input CSV with known values and asserts exact output
field values in the cleaned and rejected CSVs plus the summary JSON.

This is the single most important integration test in the pipeline: it covers
the full normalization chain (phone, email, name parse, building code, rejection)
in one shot without touching the real DB or filesystem outside tmp.
"""
import csv
import json
import tempfile
from pathlib import Path

import pytest

from clean_contacts import clean_contacts, CLEANED_FIELDS, REJECTED_FIELDS

# ---------------------------------------------------------------------------
# Fixture CSV definition — every row is deterministic and documented
# ---------------------------------------------------------------------------

FIXTURE_HEADER = [
    "source_file", "source_sheet", "source_row_number", "source_format",
    "raw_name", "raw_phone", "raw_email",
    "building_code_hint", "building_name_hint", "wing_hint", "unit_number_hint",
    "relationship_hint", "source_label", "source_category", "organization",
    "website", "google_maps_link", "raw_notes", "raw_payload_json",
    "raw_phones_json", "raw_emails_json", "aliases_json",
    "job_title", "campaign_name", "lead_status",
    "requirement_json", "inventory_hint_json",
]

def _row(**kwargs):
    base = {h: "" for h in FIXTURE_HEADER}
    base.update(kwargs)
    return base

FIXTURE_ROWS = [
    # ── Row 1: fully structured — expect cleaned with parsed wing/unit/role
    _row(
        source_file="test_fixture.csv", source_sheet="Sheet1", source_row_number="2",
        source_format="messy_phonebook_property_csv",
        raw_name="IH A-203 Owner Rohan Mehta",
        raw_phone="9876543210",
        raw_email="rohan@example.com",
    ),
    # ── Row 2: valid phone, no name — expect rejected (missing_name)
    _row(
        source_file="test_fixture.csv", source_sheet="Sheet1", source_row_number="3",
        source_format="messy_phonebook_property_csv",
        raw_name="",
        raw_phone="8765432109",
        raw_email="",
    ),
    # ── Row 3: name only, no phone/email — expect rejected (missing_valid_phone_or_email)
    _row(
        source_file="test_fixture.csv", source_sheet="Sheet1", source_row_number="4",
        source_format="messy_phonebook_property_csv",
        raw_name="Priya Sharma",
        raw_phone="",
        raw_email="",
    ),
    # ── Row 4: placeholder phone, valid email — email saves it
    _row(
        source_file="test_fixture.csv", source_sheet="Sheet1", source_row_number="5",
        source_format="messy_phonebook_property_csv",
        raw_name="Amit Singh",
        raw_phone="n/a",
        raw_email="amit@example.com",
    ),
    # ── Row 5: both phone and email invalid/absent, name present — reject
    _row(
        source_file="test_fixture.csv", source_sheet="Sheet1", source_row_number="6",
        source_format="messy_phonebook_property_csv",
        raw_name="Unknown Person",
        raw_phone="abcde",
        raw_email="notanemail",
    ),
    # ── Row 6: +91 prefix phone, wing hint from separate column
    _row(
        source_file="test_fixture.csv", source_sheet="Sheet1", source_row_number="7",
        source_format="structured_owner_workbook",
        raw_name="Kavita Joshi",
        raw_phone="+919123456789",
        raw_email="",
        wing_hint="B",
        unit_number_hint="404",
        relationship_hint="owner",
    ),
    # ── Row 7: country-code-prefixed 12-digit phone
    _row(
        source_file="test_fixture.csv", source_sheet="Sheet1", source_row_number="8",
        source_format="messy_phonebook_property_csv",
        raw_name="Sunita Rao",
        raw_phone="917777888899",
        raw_email="sunita@test.org",
    ),
    # ── Row 8: empty row (no name, no phone, no email) — rejected
    _row(
        source_file="test_fixture.csv", source_sheet="Sheet1", source_row_number="9",
        source_format="messy_phonebook_property_csv",
        raw_name="",
        raw_phone="",
        raw_email="",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_fixture_csv(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIXTURE_HEADER)
        writer.writeheader()
        writer.writerows(FIXTURE_ROWS)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def run_result():
    """Run clean_contacts once on the fixture; share across tests in this module."""
    with tempfile.TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "test_fixture.csv"
        output_dir = Path(tmp) / "out"
        output_dir.mkdir()
        write_fixture_csv(input_path)
        summary = clean_contacts(input_path, output_dir)
        cleaned = read_csv(Path(summary["cleaned_file"]))
        rejected = read_csv(Path(summary["rejected_file"]))
        yield {"summary": summary, "cleaned": cleaned, "rejected": rejected}


class TestSummaryCounts:
    def test_total_rows(self, run_result):
        assert run_result["summary"]["total_rows"] == len(FIXTURE_ROWS)

    def test_cleaned_plus_rejected_equals_total(self, run_result):
        s = run_result["summary"]
        assert s["cleaned_rows"] + s["rejected_rows"] == s["total_rows"]

    def test_expected_cleaned_count(self, run_result):
        # Rows 1, 4, 6, 7 → 4 cleaned
        assert run_result["summary"]["cleaned_rows"] == 4

    def test_expected_rejected_count(self, run_result):
        # Rows 2, 3, 5, 8 → 4 rejected
        assert run_result["summary"]["rejected_rows"] == 4

    def test_mobile_phone_count(self, run_result):
        # 3 cleaned rows have mobile phones (Rohan, Kavita, Sunita).
        # Amit Singh is cleaned via email-only — no phone normalized.
        assert run_result["summary"]["rows_with_mobile_phones"] == 3

    def test_email_count(self, run_result):
        # Rows 1 (rohan@), 4 (amit@), 7 (sunita@) have valid emails = 3
        assert run_result["summary"]["rows_with_email"] == 3

    def test_building_hint_count(self, run_result):
        # Row 1 parses "A-203"; Row 6 has wing_hint B + unit 404 = 2
        assert run_result["summary"]["rows_with_building_hints"] == 2


class TestCleanedRows:
    """Assert specific field values on known-clean rows (by raw_name lookup)."""

    def _find(self, rows, raw_name):
        matches = [r for r in rows if r["raw_name"] == raw_name]
        assert matches, f"No cleaned row with raw_name={raw_name!r}"
        return matches[0]

    def test_row1_phone_normalized(self, run_result):
        row = self._find(run_result["cleaned"], "IH A-203 Owner Rohan Mehta")
        assert row["phone_normalized"] == "+919876543210"
        assert row["phone_type"] == "mobile"

    def test_row1_email_normalized(self, run_result):
        row = self._find(run_result["cleaned"], "IH A-203 Owner Rohan Mehta")
        assert row["email_normalized"] == "rohan@example.com"

    def test_row1_wing_parsed(self, run_result):
        row = self._find(run_result["cleaned"], "IH A-203 Owner Rohan Mehta")
        assert row["parsed_wing"] == "A"

    def test_row1_unit_parsed(self, run_result):
        row = self._find(run_result["cleaned"], "IH A-203 Owner Rohan Mehta")
        assert row["parsed_unit_number"] == "203"

    def test_row1_role_parsed(self, run_result):
        row = self._find(run_result["cleaned"], "IH A-203 Owner Rohan Mehta")
        assert row["parsed_role"] == "owner"

    def test_row4_email_saves_no_phone(self, run_result):
        # Row 4: placeholder phone → falls through to email
        row = self._find(run_result["cleaned"], "Amit Singh")
        assert row["email_normalized"] == "amit@example.com"
        assert row["phone_normalized"] == ""

    def test_row6_wing_from_hint_column(self, run_result):
        row = self._find(run_result["cleaned"], "Kavita Joshi")
        assert row["parsed_wing"] == "B"
        assert row["parsed_unit_number"] == "404"
        assert row["parsed_role"] == "owner"

    def test_row7_country_prefix_stripped(self, run_result):
        row = self._find(run_result["cleaned"], "Sunita Rao")
        assert row["phone_normalized"] == "+917777888899"
        assert row["phone_type"] == "mobile"

    def test_cleaned_rows_have_no_rejection_reason(self, run_result):
        for row in run_result["cleaned"]:
            assert row.get("rejection_reason", "") == ""

    def test_cleaned_csv_has_all_expected_fields(self, run_result):
        if not run_result["cleaned"]:
            pytest.skip("No cleaned rows")
        row_keys = set(run_result["cleaned"][0].keys())
        from clean_contacts import CLEANED_FIELDS
        for field in CLEANED_FIELDS:
            assert field in row_keys, f"Missing field: {field}"


class TestRejectedRows:
    def _find(self, rows, reason_fragment):
        matches = [r for r in rows if reason_fragment in (r.get("rejection_reason") or "")]
        assert matches, f"No rejected row with reason containing {reason_fragment!r}"
        return matches[0]

    def test_missing_name_rejection(self, run_result):
        # Row 2: no name
        matches = [r for r in run_result["rejected"] if r["raw_name"] == ""]
        assert any("missing_name" in (r.get("rejection_reason") or "") for r in matches)

    def test_missing_phone_and_email_rejection(self, run_result):
        # Row 3: name only, no phone/email
        row = next(r for r in run_result["rejected"] if r["raw_name"] == "Priya Sharma")
        assert "missing_valid_phone_or_email" in row["rejection_reason"]

    def test_invalid_phone_and_email_rejection(self, run_result):
        # Row 5: invalid phone + invalid email
        row = next(r for r in run_result["rejected"] if r["raw_name"] == "Unknown Person")
        assert row["rejection_reason"] != ""

    def test_rejected_csv_has_rejection_reason_field(self, run_result):
        if not run_result["rejected"]:
            pytest.skip("No rejected rows")
        assert "rejection_reason" in run_result["rejected"][0]

    def test_rejected_rows_have_rejection_reason(self, run_result):
        for row in run_result["rejected"]:
            assert row.get("rejection_reason", "").strip() != "", \
                f"Rejected row missing reason: {row.get('raw_name')}"


class TestOutputFiles:
    def test_summary_has_required_keys(self, run_result):
        required = {
            "input_file", "cleaned_file", "rejected_file",
            "total_rows", "cleaned_rows", "rejected_rows",
            "rows_with_mobile_phones", "rows_with_email",
            "rejection_counts",
        }
        assert required.issubset(run_result["summary"].keys())

    def test_rejection_counts_non_negative(self, run_result):
        for key, count in run_result["summary"]["rejection_counts"].items():
            assert count >= 0, f"Negative rejection count for {key}"

    def test_rejection_counts_sum_lte_rejected(self, run_result):
        # A row can have multiple rejection reasons; total counts >= rejected_rows
        total_counted = sum(run_result["summary"]["rejection_counts"].values())
        assert total_counted >= run_result["summary"]["rejected_rows"]
