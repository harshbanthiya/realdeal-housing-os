"""Unit tests for normalize_phone and normalize_email in clean_contacts.py.

These functions are pure (no I/O, no DB) and are the foundation of every
contact import pipeline. Bugs here corrupt all downstream canonical records.
"""
import pytest
from clean_contacts import normalize_phone, normalize_email


# ---------------------------------------------------------------------------
# normalize_phone
# ---------------------------------------------------------------------------

class TestNormalizePhoneValid:
    def test_ten_digit_mobile_no_prefix(self):
        number, kind, err = normalize_phone("9876543210")
        assert number == "+919876543210"
        assert kind == "mobile"
        assert err == ""

    def test_with_country_code_91(self):
        number, kind, err = normalize_phone("919876543210")
        assert number == "+919876543210"
        assert kind == "mobile"
        assert err == ""

    def test_with_isd_prefix_plus_91(self):
        number, kind, err = normalize_phone("+91 98765 43210")
        assert number == "+919876543210"
        assert kind == "mobile"
        assert err == ""

    def test_with_leading_zero(self):
        number, kind, err = normalize_phone("09876543210")
        assert number == "+919876543210"
        assert kind == "mobile"
        assert err == ""

    def test_mobile_starts_with_6(self):
        number, kind, err = normalize_phone("6123456789")
        assert number == "+916123456789"
        assert kind == "mobile"
        assert err == ""

    def test_mobile_starts_with_7(self):
        number, kind, err = normalize_phone("7012345678")
        assert number == "+917012345678"
        assert kind == "mobile"
        assert err == ""

    def test_mobile_starts_with_8(self):
        number, kind, err = normalize_phone("8765432109")
        assert number == "+918765432109"
        assert kind == "mobile"
        assert err == ""

    def test_spaces_stripped(self):
        number, kind, err = normalize_phone("  9876543210  ")
        assert number == "+919876543210"
        assert kind == "mobile"
        assert err == ""

    def test_dashes_stripped(self):
        number, kind, err = normalize_phone("98765-43210")
        assert number == "+919876543210"
        assert kind == "mobile"
        assert err == ""


class TestNormalizePhoneInvalid:
    def test_empty_string(self):
        number, kind, err = normalize_phone("")
        assert number == ""
        assert err == ""  # empty → empty, not an error

    def test_whitespace_only(self):
        number, kind, err = normalize_phone("   ")
        assert number == ""

    def test_placeholder_na(self):
        _, _, err = normalize_phone("n/a")
        assert err == "placeholder_phone"

    def test_placeholder_na_uppercase(self):
        _, _, err = normalize_phone("N/A")
        assert err == "placeholder_phone"

    def test_placeholder_null(self):
        _, _, err = normalize_phone("null")
        assert err == "placeholder_phone"

    def test_placeholder_dash(self):
        _, _, err = normalize_phone("-")
        assert err == "placeholder_phone"

    def test_repeated_digit_placeholder(self):
        # e.g. 9999999999 — all same digit
        _, _, err = normalize_phone("9999999999")
        assert err == "placeholder_phone"

    def test_too_short(self):
        _, _, err = normalize_phone("12345")
        assert err == "invalid_phone"

    def test_starts_with_invalid_digit_accepted_as_landline(self):
        # The normalizer intentionally accepts any 8-11 digit number as landline
        # (loose rule to capture STD+landline combos). A 10-digit 5xxxxxxxxx is
        # NOT a valid Indian mobile but is not rejected — it becomes landline.
        # This is a known permissiveness: import review catches it in NocoDB.
        number, kind, err = normalize_phone("5123456789")
        assert kind == "landline"
        assert err == ""
        assert number.startswith("+91")

    def test_letters_only(self):
        _, _, err = normalize_phone("abcdefghij")
        assert err == "invalid_phone"

    def test_none_value(self):
        number, kind, err = normalize_phone(None)
        assert number == ""


# ---------------------------------------------------------------------------
# normalize_email
# ---------------------------------------------------------------------------

class TestNormalizeEmail:
    def test_valid_email(self):
        email, err = normalize_email("user@example.com")
        assert email == "user@example.com"
        assert err == ""

    def test_lowercases(self):
        email, err = normalize_email("User@Example.COM")
        assert email == "user@example.com"
        assert err == ""

    def test_strips_whitespace(self):
        email, err = normalize_email("  user@example.com  ")
        assert email == "user@example.com"
        assert err == ""

    def test_subdomain(self):
        email, err = normalize_email("user@mail.example.co.in")
        assert email == "user@mail.example.co.in"
        assert err == ""

    def test_empty_string(self):
        email, err = normalize_email("")
        assert email == ""
        assert err == ""

    def test_none_value(self):
        email, err = normalize_email(None)
        assert email == ""
        assert err == ""

    def test_missing_at(self):
        email, err = normalize_email("notanemail")
        assert email == ""
        assert err == "invalid_email"

    def test_missing_domain(self):
        email, err = normalize_email("user@")
        assert email == ""
        assert err == "invalid_email"

    def test_missing_local(self):
        email, err = normalize_email("@example.com")
        assert email == ""
        assert err == "invalid_email"

    def test_double_at(self):
        email, err = normalize_email("a@b@c.com")
        assert email == ""
        assert err == "invalid_email"
