"""Tests for token normalisation helpers (date, currency, numeral)."""

import pytest

from scribe import (
    normalize_currency,
    normalize_date,
    normalize_indic_numerals,
    normalize_kannada_numerals,
    normalize_numeral,
    normalize_subsection,
    normalize_token,
)


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


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("34 (2)", "34(2)"),
        ("5 (1)(a)", "5(1)(a)"),
        ("34(2)(a)(iii)", "34(2)(a)(iii)"),
        ("304A (1)", "304A(1)"),
        ("120-B", "120-B"),
    ],
)
def test_normalize_subsection_removes_spaces(raw, expected):
    assert normalize_subsection(raw) == expected
    assert normalize_numeral(raw) == expected


@pytest.mark.parametrize("raw", ["34  (2)", "34 ( 2 )", "34 (2 ) (a)"])
def test_normalize_subsection_leaves_bad_spacing(raw):
    assert normalize_subsection(raw) == raw


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
    """LEXICAL-tagged text is not touched by numeral normalisation rules."""
    assert normalize_token("hello", "LEXICAL") == "hello"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("೧೮೩", "183"),
        ("೧೫.೦೫.೨೦೨೩", "15.05.2023"),
        ("೧,೫೦೦", "1,500"),
        ("൧൮൩", "183"),
        ("൧൫.൦൫.൨൦൨൩", "15.05.2023"),
        ("൧,൫൦൦", "1,500"),
        ("१८३", "183"),
        ("१५.०५.२०२३", "15.05.2023"),
        ("१,५००", "1,500"),
        ("42", "42"),
        ("Section 302", "Section 302"),
    ],
)
def test_normalize_indic_numerals(raw, expected):
    assert normalize_indic_numerals(raw) == expected


def test_normalize_kannada_numerals_backward_compatibility():
    assert normalize_kannada_numerals("೧೮೩") == "183"
    assert normalize_kannada_numerals("೧೫.೦೫.೨೦೨೩") == "15.05.2023"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("೧೫.೦೫.೨೦೨೩", "15-05-2023"),
        ("൧൫.൦൫.൨൦൨൩", "15-05-2023"),
        ("१५.०५.२०२३", "15-05-2023"),
        ("೧,೫೦೦", "1500"),
        ("൧,൫൦൦", "1500"),
        ("१,५००", "1500"),
        ("೩೪ (೨)", "34(2)"),
        ("൩൪ (൨)", "34(2)"),
        ("३४ (२)", "34(2)"),
    ],
)
def test_normalize_numeral_handles_indic_scripts(raw, expected):
    assert normalize_numeral(raw) == expected


def test_normalize_token_indic_numerals():
    assert normalize_token("൧൫.൦൫.൨൦൨൩", "NUMERAL") == "15-05-2023"
    assert normalize_token("೧೫.೦೫.೨೦೨೩", "NUMERAL") == "15-05-2023"
    assert normalize_token("१५.०५.२०२३", "NUMERAL") == "15-05-2023"
    assert normalize_token("൧,൫൦൦", "NUMERAL") == "1500"
    assert normalize_token("೧,೫೦೦", "NUMERAL") == "1500"
    assert normalize_token("१,५००", "NUMERAL") == "1500"
