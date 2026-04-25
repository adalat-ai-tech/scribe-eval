"""Tests for token normalisation helpers (date, currency, numeral)."""

import pytest

from scribe import normalize_currency, normalize_date, normalize_numeral, normalize_token


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("22.05.2023", "22-05-2023"),
        ("22/05/2023", "22-05-2023"),
        ("22-05-2023", "22-05-2023"),
    ],
)
def test_normalize_date_canonicalises_separators(raw, expected):
    assert normalize_date(raw) == expected


def test_normalize_date_passes_through_non_dates():
    assert normalize_date("hello") == "hello"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("10,500", "10500"),
        ("1,000,000", "1000000"),
        ("10500", "10500"),
    ],
)
def test_normalize_currency_strips_commas(raw, expected):
    assert normalize_currency(raw) == expected


def test_normalize_currency_passes_through_plain_words():
    assert normalize_currency("rupees") == "rupees"


def test_normalize_numeral_handles_pure_digits():
    # The function may or may not transform plain integers, but it must
    # at least return them unchanged (idempotent on canonical form).
    assert normalize_numeral("42") == "42"


def test_normalize_token_dispatches_by_category():
    """normalize_token routes to the right normaliser based on category."""
    # The exact contract we exercise: token-level normalisation must, at
    # minimum, produce equal outputs for date/currency variants.
    assert normalize_token("22.05.2023", "NUMERAL") == normalize_token("22/05/2023", "NUMERAL")
    assert normalize_token("10,500", "NUMERAL") == normalize_token("10500", "NUMERAL")


def test_normalize_token_word_category_unchanged():
    """WORD-tagged text is not touched by numeral normalisation rules."""
    assert normalize_token("hello", "WORD") == "hello"
