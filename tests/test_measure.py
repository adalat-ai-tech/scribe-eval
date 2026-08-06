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
    for cat in ("LEXICAL", "NUMERAL", "PUNCT"):
        assert report[cat]["error_rate"] == 0.0
        assert report[cat]["substitutions"] == 0
        assert report[cat]["insertions"] == 0
        assert report[cat]["deletions"] == 0


def test_base_categories_are_always_present():
    """Even when a category has zero tokens, its key must exist."""
    report = text_error_rates("just words here", "just words here", None)
    assert "LEXICAL" in report
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
    assert report["LEXICAL"]["substitutions"] == 1
    assert report["LEXICAL"]["insertions"] == 0
    assert report["LEXICAL"]["deletions"] == 0


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
    aligned_ref = [("a", "LEXICAL"), ("b", "LEXICAL"), ("c", "LEXICAL")]
    aligned_hyp = [("a", "LEXICAL"), ("b", "LEXICAL"), ("c", "LEXICAL")]
    report = token_error_rates(aligned_ref, aligned_hyp)
    assert report["LEXICAL"]["error_rate"] == 0.0
    assert report["LEXICAL"]["substitutions"] == 0


def test_token_error_rates_reports_substitution_count():
    aligned_ref = [("a", "LEXICAL"), ("b", "LEXICAL"), ("c", "LEXICAL")]
    aligned_hyp = [("a", "LEXICAL"), ("x", "LEXICAL"), ("c", "LEXICAL")]
    report = token_error_rates(aligned_ref, aligned_hyp)
    assert report["LEXICAL"]["substitutions"] == 1


def test_category_with_zero_ref_tokens_has_zero_error_rate():
    """A category with no reference tokens reports error_rate=0 (no
    division-by-zero) and combined_total reflects only populated
    categories.
    """
    aligned_ref = [("hello", "LEXICAL"), ("world", "LEXICAL")]
    aligned_hyp = [("hello", "LEXICAL"), ("world", "LEXICAL")]
    report = token_error_rates(aligned_ref, aligned_hyp)
    assert report["PUNCT"]["total_ref"] == 0
    assert report["PUNCT"]["error_rate"] == 0.0
    assert report["NUMERAL"]["total_ref"] == 0
    assert report["NUMERAL"]["error_rate"] == 0.0
    assert report["LEXICAL"]["combined_total"] == 2
    assert report["PUNCT"]["combined_total"] == 2
    assert report["NUMERAL"]["combined_total"] == 2


def test_pure_sandhi_event_does_not_affect_error_rate_or_counts():
    """Sandhi merge corrections are tracked separately from sub/ins/del
    and contribute zero to the error rate. Regression for the change
    that added sandhi_merge / sandhi_split records to token_error_details.
    """
    ref = "ഇന്ന് അല്ലെങ്കിൽ"
    hyp = "ഇന്നല്ലെങ്കിൽ"
    report = text_error_rates(ref, hyp, None)

    assert report["LEXICAL"]["error_rate"] == 0.0
    assert report["LEXICAL"]["substitutions"] == 0
    assert report["LEXICAL"]["insertions"] == 0
    assert report["LEXICAL"]["deletions"] == 0
    assert report["LEXICAL"]["sandhi_hits"] == 1


def test_token_error_rates_has_no_sandhi_parameter():
    """Sandhi is decided at alignment time; token_error_rates counts the
    MERGE:/SPLIT: markers it receives. It must not advertise a use_sandhi
    flag it cannot honor (regression: dead parameter)."""
    import inspect

    params = inspect.signature(token_error_rates).parameters
    assert "use_sandhi" not in params


def test_unknown_ref_tags_are_counted_not_dropped(legal_domain):
    """Tokens whose tags are outside the configured category set must
    still be counted — under their own tag — in both the error counts
    and the combined denominator (regression: they were silently
    dropped from both, deflating every other category's rate).

    Ground truth: tokens tagged with the legal domain (charged/LEXICAL,
    u/s/LEGAL, 302/NUMERAL), then measured with domain_config=None."""
    from scribe import align_arrays, domain_aware_tokenizer

    ref_toks, ref_tags = domain_aware_tokenizer("charged u/s 302", legal_domain)
    hyp_toks, hyp_tags = domain_aware_tokenizer("charged us 302", legal_domain)
    aligned_ref, aligned_hyp, _ = align_arrays(ref_toks, ref_tags, hyp_toks, hyp_tags)

    report = token_error_rates(aligned_ref, aligned_hyp, domain_config=None)

    assert "LEGAL" in report
    assert report["LEGAL"]["substitutions"] == 1
    assert report["LEGAL"]["combined_total"] == 3
    # The LEGAL token counts in every category's shared denominator.
    assert report["LEXICAL"]["combined_total"] == 3


def test_unknown_insertion_tags_are_counted(legal_domain):
    """An inserted token with an out-of-set tag is counted under its
    own tag instead of vanishing."""
    from scribe import align_arrays, domain_aware_tokenizer

    ref_toks, ref_tags = domain_aware_tokenizer("charged 302", legal_domain)
    hyp_toks, hyp_tags = domain_aware_tokenizer("charged u/s 302", legal_domain)
    aligned_ref, aligned_hyp, _ = align_arrays(ref_toks, ref_tags, hyp_toks, hyp_tags)

    report = token_error_rates(aligned_ref, aligned_hyp, domain_config=None)

    assert report["LEGAL"]["insertions"] == 1


def test_error_details_record_all_tags_from_data(legal_domain):
    """token_error_details records every error under its token's own
    tag — it takes no domain configuration; categories come from the
    aligned tags."""
    import inspect

    from scribe import align_arrays, domain_aware_tokenizer, token_error_details

    assert "domain_config" not in inspect.signature(token_error_details).parameters

    ref_toks, ref_tags = domain_aware_tokenizer("charged u/s 302", legal_domain)
    hyp_toks, hyp_tags = domain_aware_tokenizer("charged us 302", legal_domain)
    aligned_ref, aligned_hyp, _ = align_arrays(ref_toks, ref_tags, hyp_toks, hyp_tags)

    details = token_error_details(aligned_ref, aligned_hyp)
    categories = {d["category"] for d in details}
    assert "LEGAL" in categories
