"""Tests for the domain-aware tokenizer."""

import pytest

from scribe import CAT_LEXICAL, CAT_NUMERAL, CAT_PUNCT, DomainConfig, domain_aware_tokenizer


def test_empty_string_returns_empty_token_list():
    tokens, tags = domain_aware_tokenizer("")
    assert tokens == []
    assert tags == []


def test_whitespace_only_returns_empty_token_list():
    tokens, tags = domain_aware_tokenizer("   \n\t  ")
    assert tokens == []
    assert tags == []


def test_words_are_tagged_WORD():
    tokens, tags = domain_aware_tokenizer("hello world")
    assert tokens == ["hello", "world"]
    assert tags == [CAT_LEXICAL, CAT_LEXICAL]


def test_punctuation_is_separate_tokens():
    tokens, tags = domain_aware_tokenizer("hello, world.")
    # The exact comma/period split is implementation detail, but each
    # punctuation character should be tagged PUNCT.
    assert "," in tokens or "." in tokens
    for tok, tag in zip(tokens, tags):
        if tok in {",", "."}:
            assert tag == CAT_PUNCT


def test_integer_numerals_are_tagged_NUMERAL():
    tokens, tags = domain_aware_tokenizer("section 302 of IPC")
    assert "302" in tokens
    idx = tokens.index("302")
    assert tags[idx] == CAT_NUMERAL


def test_dates_are_kept_as_one_numeral_token():
    """Dates like 22.05.2023 must NOT be split on the dots."""
    tokens, tags = domain_aware_tokenizer("on 22.05.2023")
    assert "22.05.2023" in tokens
    idx = tokens.index("22.05.2023")
    assert tags[idx] == CAT_NUMERAL


def test_times_are_kept_as_one_numeral_token():
    tokens, tags = domain_aware_tokenizer("at 10:30 sharp")
    assert "10:30" in tokens
    idx = tokens.index("10:30")
    assert tags[idx] == CAT_NUMERAL


def test_currency_with_commas_kept_as_one_numeral_token():
    tokens, tags = domain_aware_tokenizer("Rs. 10,500 paid")
    assert "10,500" in tokens
    idx = tokens.index("10,500")
    assert tags[idx] == CAT_NUMERAL


def test_legal_domain_shields_us_slash_token(legal_domain):
    """`u/s` is one LEGAL token, not split into `u`, `/`, `s`."""
    tokens, tags = domain_aware_tokenizer("charged u/s 302", legal_domain)
    assert "u/s" in tokens
    idx = tokens.index("u/s")
    assert tags[idx] == "LEGAL"


def test_legal_domain_shields_pw_witness_patterns(legal_domain):
    """PW1, PW 1, PW-1 should all be LEGAL tokens (regex-based shielding)."""
    for ref in ["witness PW1", "witness PW-1"]:
        tokens, tags = domain_aware_tokenizer(ref, legal_domain)
        legal_tokens = [t for t, tag in zip(tokens, tags) if tag == "LEGAL"]
        assert legal_tokens, f"No LEGAL token found in {ref!r}"


def test_no_domain_leaves_legal_terms_as_WORD():
    """Without a domain config, `u/s` is a regular LEXICAL token."""
    tokens, tags = domain_aware_tokenizer("charged u/s 302")
    assert "u/s" in tokens
    idx = tokens.index("u/s")
    # The point: not LEGAL. (Could be LEXICAL or a combination — we just
    # assert it isn't tagged with the domain category.)
    assert tags[idx] != "LEGAL"


def test_medical_domain_shields_dosage_units(medical_domain):
    """`mg`, `ml`, etc. are MEDICAL tokens with the medical config."""
    tokens, tags = domain_aware_tokenizer("administer 5 mg twice", medical_domain)
    medical_tokens = [t for t, tag in zip(tokens, tags) if tag == "MEDICAL"]
    assert medical_tokens, "Expected at least one MEDICAL token"


def test_indic_text_tokenizes_per_whitespace():
    """Malayalam words separated by spaces tokenize as individual WORDs."""
    text = "ഇന്ന് നാളെ"
    tokens, tags = domain_aware_tokenizer(text)
    assert len(tokens) == 2
    assert all(tag == CAT_LEXICAL for tag in tags)


@pytest.mark.parametrize(
    "domain_factory",
    [DomainConfig.legal, DomainConfig.medical, DomainConfig.technical],
)
def test_factory_methods_produce_usable_configs(domain_factory):
    config = domain_factory()
    # The tokenizer must accept it without error.
    tokens, tags = domain_aware_tokenizer("test 123 abc.", config)
    assert len(tokens) == len(tags)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("PW1 deposed", ["PW", "1", "deposed"]),  # digit glued to a letter end
        ("Cr.No.353", ["Cr.No.", "353"]),  # anything after a final dot
        ("Ex.P1", ["Ex.", "P", "1"]),  # no exhibit numeral format here
    ],
)
def test_domain_term_splits_from_glued_reference(text, expected):
    config = DomainConfig("legal", r"PW|Cr\.No\.|Ex\.", category="LEGAL")
    tokens, tags = domain_aware_tokenizer(text, config)
    assert tokens == expected
    assert tags[0] == "LEGAL"


def test_domain_term_not_matched_inside_a_word():
    config = DomainConfig("legal", ["PW"], category="LEGAL")
    tokens, tags = domain_aware_tokenizer("PWD office", config)
    assert "LEGAL" not in tags


# Bundled legal rules: anchors and legal names are LEGAL, the reference
# after an anchor is one NUMERAL token, a leading place name stays LEXICAL.
@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "under Section 5(1)(a)",
            [("under", "LEXICAL"), ("Section", "LEGAL"), ("5(1)(a)", "NUMERAL")],
        ),
        ("under Cr.P.C.", [("under", "LEXICAL"), ("Cr.P.C.", "LEGAL")]),
        ("Kerala High Court", [("Kerala", "LEXICAL"), ("High Court", "LEGAL")]),
        ("Kerala Abkari Act", [("Kerala", "LEXICAL"), ("Abkari Act", "LEGAL")]),
        ("PW1 stated", [("PW", "LEGAL"), ("1", "NUMERAL"), ("stated", "LEXICAL")]),
        ("Exhibit A1", [("Exhibit", "LEGAL"), ("A1", "NUMERAL")]),
        ("Cr.No.353/2019", [("Cr.No.", "LEGAL"), ("353/2019", "NUMERAL")]),
        (
            "Order XXXIX Rule 1",
            [("Order", "LEGAL"), ("XXXIX", "NUMERAL"), ("Rule", "LEGAL"), ("1", "NUMERAL")],
        ),
        # Verb "act" and "in order to" are not legal terms.
        (
            "in order to act",
            [("in", "LEXICAL"), ("order", "LEXICAL"), ("to", "LEXICAL"), ("act", "LEXICAL")],
        ),
        # A case number format must not split a date.
        ("dated 22/05/2023", [("dated", "LEXICAL"), ("22/05/2023", "NUMERAL")]),
    ],
)
def test_bundled_legal_rules(legal_domain, text, expected):
    tokens, tags = domain_aware_tokenizer(text, legal_domain)
    assert list(zip(tokens, tags)) == expected
