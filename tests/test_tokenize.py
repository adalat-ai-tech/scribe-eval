"""Tests for the domain-aware tokenizer."""

import pytest

from scribe import CAT_NUMERAL, CAT_PUNCT, CAT_WORD, DomainConfig, domain_aware_tokenizer


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
    assert tags == [CAT_WORD, CAT_WORD]


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
    """Without a domain config, `u/s` is a regular WORD token."""
    tokens, tags = domain_aware_tokenizer("charged u/s 302")
    assert "u/s" in tokens
    idx = tokens.index("u/s")
    # The point: not LEGAL. (Could be WORD or a combination — we just
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
    assert all(tag == CAT_WORD for tag in tags)


@pytest.mark.parametrize(
    "domain_factory",
    [DomainConfig.legal, DomainConfig.medical, DomainConfig.technical],
)
def test_factory_methods_produce_usable_configs(domain_factory):
    config = domain_factory()
    # The tokenizer must accept it without error.
    tokens, tags = domain_aware_tokenizer("test 123 abc.", config)
    assert len(tokens) == len(tags)
