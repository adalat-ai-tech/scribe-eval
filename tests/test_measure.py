"""End-to-end tests for measure (text_error_rates / token_error_rates).

The combined-denominator math is the central correctness contract here:
ER_t = (sub + ins + del) / N_comb where N_comb sums ref tokens across
ALL categories, not just category t.
"""

import pytest

from scribe import text_error_rates, token_error_rates


def test_perfect_match_reports_zero_errors():
    ref = "the case is closed."
    report = text_error_rates(ref, ref, None)
    for cat in ("WORD", "NUMERAL", "PUNCT"):
        assert report[cat]["error_rate"] == 0.0
        assert report[cat]["substitutions"] == 0
        assert report[cat]["insertions"] == 0
        assert report[cat]["deletions"] == 0


def test_base_categories_are_always_present():
    """Even when a category has zero tokens, its key must exist."""
    report = text_error_rates("just words here", "just words here", None)
    assert "WORD" in report
    assert "NUMERAL" in report
    assert "PUNCT" in report


def test_domain_category_appears_when_domain_supplied(legal_domain):
    report = text_error_rates("charged u/s 302", "charged u/s 302", legal_domain)
    assert "LEGAL" in report


def test_domain_category_absent_without_domain():
    report = text_error_rates("charged u/s 302", "charged u/s 302", None)
    assert "LEGAL" not in report


def test_single_word_substitution_counted_once():
    report = text_error_rates("the case is closed", "the case is open", None)
    assert report["WORD"]["substitutions"] == 1
    assert report["WORD"]["insertions"] == 0
    assert report["WORD"]["deletions"] == 0


def test_combined_denominator_yields_low_rate_for_sparse_category(legal_domain):
    """Paper §3.3: 1 LEGAL error against a 4-token ref must report 25% LER,
    not the misleading 100% you would get with a per-category denominator.
    """
    report = text_error_rates("charged u/s 302 IPC", "charged us 302 IPC", legal_domain)
    assert report["LEGAL"]["substitutions"] == 1
    assert report["LEGAL"]["error_rate"] == pytest.approx(0.25)


def test_normalize_flag_collapses_date_format_variants(legal_domain):
    """22.05.2023 vs 22/05/2023 are equivalent under normalize=True."""
    ref = "case dated 22.05.2023"
    hyp = "case dated 22/05/2023"
    norm = text_error_rates(ref, hyp, legal_domain, normalize=True)
    raw = text_error_rates(ref, hyp, legal_domain, normalize=False)
    # Normalised: zero numeral error. Raw: at least one substitution.
    assert norm["NUMERAL"]["error_rate"] == 0.0
    assert raw["NUMERAL"]["substitutions"] + raw["NUMERAL"]["error_rate"] > 0


def test_normalize_flag_collapses_currency_comma_variants(legal_domain):
    ref = "amount Rs. 10,500"
    hyp = "amount Rs. 10500"
    norm = text_error_rates(ref, hyp, legal_domain, normalize=True)
    raw = text_error_rates(ref, hyp, legal_domain, normalize=False)
    assert norm["NUMERAL"]["error_rate"] == 0.0
    assert raw["NUMERAL"]["substitutions"] + raw["NUMERAL"]["error_rate"] > 0


def test_token_error_rates_accepts_aligned_input():
    """token_error_rates is the lower-level entry that takes already-aligned
    token streams (as the alignment engine produces).
    """
    aligned_ref = [("a", "WORD"), ("b", "WORD"), ("c", "WORD")]
    aligned_hyp = [("a", "WORD"), ("b", "WORD"), ("c", "WORD")]
    report = token_error_rates(aligned_ref, aligned_hyp)
    assert report["WORD"]["error_rate"] == 0.0
    assert report["WORD"]["substitutions"] == 0


def test_token_error_rates_reports_substitution_count():
    aligned_ref = [("a", "WORD"), ("b", "WORD"), ("c", "WORD")]
    aligned_hyp = [("a", "WORD"), ("x", "WORD"), ("c", "WORD")]
    report = token_error_rates(aligned_ref, aligned_hyp)
    assert report["WORD"]["substitutions"] == 1


def test_category_with_zero_ref_tokens_has_zero_error_rate():
    """A category with no reference tokens reports error_rate=0 (no
    division-by-zero) and combined_total reflects only populated
    categories.
    """
    aligned_ref = [("hello", "WORD"), ("world", "WORD")]
    aligned_hyp = [("hello", "WORD"), ("world", "WORD")]
    report = token_error_rates(aligned_ref, aligned_hyp)
    assert report["PUNCT"]["total_ref"] == 0
    assert report["PUNCT"]["error_rate"] == 0.0
    assert report["NUMERAL"]["total_ref"] == 0
    assert report["NUMERAL"]["error_rate"] == 0.0
    assert report["WORD"]["combined_total"] == 2
    assert report["PUNCT"]["combined_total"] == 2
    assert report["NUMERAL"]["combined_total"] == 2
