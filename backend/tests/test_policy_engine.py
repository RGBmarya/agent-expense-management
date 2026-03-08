"""Tests for the policy evaluation engine."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest
from app.policy_engine import _check_mcc_lists, _check_merchant_lists


class TestCheckMccLists:
    def test_allowed_mcc_passes(self):
        assert _check_mcc_lists("5411", ["5411", "5812"], None) is None

    def test_mcc_not_in_allowed_list(self):
        result = _check_mcc_lists("9999", ["5411", "5812"], None)
        assert result is not None
        assert "not in allowed list" in result

    def test_blocked_mcc(self):
        result = _check_mcc_lists("7995", None, ["7995"])
        assert result is not None
        assert "is blocked" in result

    def test_mcc_not_blocked(self):
        assert _check_mcc_lists("5411", None, ["7995"]) is None

    def test_no_restrictions(self):
        assert _check_mcc_lists("5411", None, None) is None

    def test_empty_lists_treated_as_no_restriction(self):
        assert _check_mcc_lists("5411", [], []) is None


class TestCheckMerchantLists:
    def test_allowed_merchant_passes(self):
        assert _check_merchant_lists("AWS", ["AWS", "GCP"], None) is None

    def test_merchant_not_in_allowed_list(self):
        result = _check_merchant_lists("Azure", ["AWS", "GCP"], None)
        assert result is not None
        assert "not in allowed list" in result

    def test_blocked_merchant_exact(self):
        result = _check_merchant_lists("Casino", None, ["Casino"])
        assert result is not None
        assert "is blocked" in result

    def test_blocked_merchant_no_substring_match(self):
        # Exact match only — "Casino Royale" should NOT match blocklist entry "Casino"
        result = _check_merchant_lists("Casino Royale", None, ["Casino"])
        assert result is None

    def test_case_insensitive_match(self):
        result = _check_merchant_lists("aws", ["AWS"], None)
        assert result is None  # case-insensitive exact match

    def test_case_insensitive_no_partial(self):
        # "aws services" is not an exact match for "AWS"
        result = _check_merchant_lists("aws services", ["AWS"], None)
        assert result is not None

    def test_blocked_case_insensitive(self):
        result = _check_merchant_lists("CASINO", None, ["casino"])
        assert result is not None

    def test_no_restrictions(self):
        assert _check_merchant_lists("Any Merchant", None, None) is None

    def test_no_substring_match_in_allowed(self):
        # Exact match only — "Amazon AWS Services" should NOT match allowlist entry "AWS"
        result = _check_merchant_lists("Amazon AWS Services", ["AWS"], None)
        assert result is not None

    def test_no_substring_match_in_blocked(self):
        # Exact match only — "Big Casino Resort" should NOT match blocklist entry "Casino"
        result = _check_merchant_lists("Big Casino Resort", None, ["Casino"])
        assert result is None

    def test_whitespace_trimming(self):
        assert _check_merchant_lists("  AWS  ", ["AWS"], None) is None
        assert _check_merchant_lists("AWS", ["  AWS  "], None) is None
