"""Tests for analysis.py — frequent error aggregation, contributions,
distributions, total error rate, and sandhi aggregation.

Sandhi merges/splits are emitted by token_error_details() as their own
record types and do not contribute to substitution/insertion/deletion
counts or to the error rate.
"""

import pytest

from scribe import (
    compute_category_contributions,
    compute_error_summary,
    compute_error_type_distribution,
    compute_frequent_deletions,
    compute_frequent_insertions,
    compute_frequent_sandhi_merges,
    compute_frequent_sandhi_splits,
    compute_frequent_substitutions,
    compute_total_error_rate,
    format_frequent_errors_table,
    text_error_details,
    text_error_rates,
)
from scribe.measure_batch import compute_aggregate_metrics

# Malayalam sandhi pair: "ഇന്ന് അല്ലെങ്കിൽ" merges to "ഇന്നല്ലെങ്കിൽ".
MERGE_REF = "ഇന്ന് അല്ലെങ്കിൽ"
MERGE_HYP = "ഇന്നല്ലെങ്കിൽ"


def _details_for(pairs):
    out = []
    for ref, hyp in pairs:
        out.extend(text_error_details(ref, hyp, None))
    return out


def test_token_error_details_emits_sandhi_merge_record():
    details = text_error_details(MERGE_REF, MERGE_HYP, None)
    merges = [d for d in details if d["error_type"] == "sandhi_merge"]
    assert len(merges) == 1
    rec = merges[0]
    assert rec["category"] == "WORD"
    assert rec["ref_token"] == MERGE_REF
    assert rec["hyp_token"] == MERGE_HYP


def test_token_error_details_emits_sandhi_split_record():
    details = text_error_details(MERGE_HYP, MERGE_REF, None)
    splits = [d for d in details if d["error_type"] == "sandhi_split"]
    assert len(splits) == 1
    rec = splits[0]
    assert rec["category"] == "WORD"
    assert rec["ref_token"] == MERGE_HYP
    assert rec["hyp_token"] == MERGE_REF


def test_sandhi_records_do_not_appear_in_substitution_deletion_insertion():
    """A pure sandhi event yields no sub/ins/del records."""
    details = text_error_details(MERGE_REF, MERGE_HYP, None)
    other_types = {"substitution", "insertion", "deletion"}
    assert not [d for d in details if d["error_type"] in other_types]


def test_sandhi_records_coexist_with_substitution_in_same_pair():
    ref = f"{MERGE_REF} നാളെ"
    hyp = f"{MERGE_HYP} മറ്റന്നാൾ"
    details = text_error_details(ref, hyp, None)
    types = sorted(d["error_type"] for d in details)
    assert types == ["sandhi_merge", "substitution"]


def test_compute_frequent_sandhi_merges_counts_repeats():
    pairs = [(MERGE_REF, MERGE_HYP)] * 3 + [(MERGE_HYP, MERGE_REF)]
    merges = compute_frequent_sandhi_merges(_details_for(pairs), top_n=10)
    assert merges["_all"] == [(MERGE_REF, MERGE_HYP, 3)]
    assert merges["WORD"] == [(MERGE_REF, MERGE_HYP, 3)]


def test_compute_frequent_sandhi_splits_counts_repeats():
    pairs = [(MERGE_HYP, MERGE_REF)] * 2 + [(MERGE_REF, MERGE_HYP)]
    splits = compute_frequent_sandhi_splits(_details_for(pairs), top_n=10)
    assert splits["_all"] == [(MERGE_HYP, MERGE_REF, 2)]
    assert splits["WORD"] == [(MERGE_HYP, MERGE_REF, 2)]


def test_compute_frequent_sandhi_returns_empty_when_no_sandhi_present():
    details = text_error_details("hello world", "hello world", None)
    assert compute_frequent_sandhi_merges(details, top_n=5) == {"_all": []}
    assert compute_frequent_sandhi_splits(details, top_n=5) == {"_all": []}


def test_compute_frequent_substitutions_unaffected_by_sandhi_records():
    """Sandhi records must not bleed into the substitution counter."""
    pairs = [(f"{MERGE_REF} a", f"{MERGE_HYP} b")] * 2
    details = _details_for(pairs)
    subs = compute_frequent_substitutions(details, top_n=10)
    assert subs["_all"] == [("a", "b", 2)]
    # Sentinel: deletions/insertions stay empty.
    assert compute_frequent_deletions(details, top_n=10)["_all"] == []
    assert compute_frequent_insertions(details, top_n=10)["_all"] == []


def test_compute_error_summary_includes_sandhi_keys():
    pairs = [(MERGE_REF, MERGE_HYP), (MERGE_HYP, MERGE_REF)]
    sample_results = [
        {"detailed_report": text_error_rates(r, h, None), "source_dataset": "t"} for r, h in pairs
    ]
    metrics = compute_aggregate_metrics(sample_results)
    summary = compute_error_summary(metrics["overall"], _details_for(pairs), top_n=5)

    assert "frequent_sandhi_merges" in summary
    assert "frequent_sandhi_splits" in summary
    assert summary["frequent_sandhi_merges"]["_all"] == [(MERGE_REF, MERGE_HYP, 1)]
    assert summary["frequent_sandhi_splits"]["_all"] == [(MERGE_HYP, MERGE_REF, 1)]


def test_format_frequent_errors_table_handles_sandhi_merge():
    merges = compute_frequent_sandhi_merges(_details_for([(MERGE_REF, MERGE_HYP)]), top_n=5)
    rows = format_frequent_errors_table(merges, "sandhi_merge", 5)
    assert rows == [
        {
            "Rank": 1,
            "Category": "WORD",
            "Reference": MERGE_REF,
            "Hypothesis": MERGE_HYP,
            "Count": 1,
        }
    ]


def test_format_frequent_errors_table_handles_sandhi_split():
    splits = compute_frequent_sandhi_splits(_details_for([(MERGE_HYP, MERGE_REF)]), top_n=5)
    rows = format_frequent_errors_table(splits, "sandhi_split", 5)
    assert rows == [
        {
            "Rank": 1,
            "Category": "WORD",
            "Reference": MERGE_HYP,
            "Hypothesis": MERGE_REF,
            "Count": 1,
        }
    ]


# ---------------------------------------------------------------------------
# Frequent substitutions / deletions / insertions — direct coverage.
# ---------------------------------------------------------------------------


def test_compute_frequent_substitutions_ranks_by_count():
    """The same substitution repeated more often must rank higher."""
    pairs = [
        ("मैंने आम खाया", "मैंने केला खाया"),  # आम -> केला
        ("मैंने आम खाया", "मैंने केला खाया"),  # आम -> केला (repeat)
        ("मैंने आम खाया", "मैंने सेब खाया"),  # आम -> सेब
    ]
    subs = compute_frequent_substitutions(_details_for(pairs), top_n=5)
    assert subs["_all"][0] == ("आम", "केला", 2)
    assert subs["_all"][1] == ("आम", "सेब", 1)
    assert subs["WORD"][0] == ("आम", "केला", 2)


def test_compute_frequent_substitutions_top_n_truncates():
    # Five distinct Hindi word substitutions in WORD category.
    refs = ["आम", "केला", "सेब", "अंगूर", "नारंगी"]
    hyps = ["कुत्ता", "बिल्ली", "गाय", "घोड़ा", "हाथी"]
    pairs = [(f"मैंने {r} खाया", f"मैंने {h} खाया") for r, h in zip(refs, hyps)]
    subs = compute_frequent_substitutions(_details_for(pairs), top_n=3)
    assert len(subs["_all"]) == 3
    assert len(subs["WORD"]) == 3


def test_compute_frequent_deletions_counts_repeats():
    """Deletions surface when ref tokens are dropped from the hypothesis."""
    pairs = [
        ("नमस्ते दुनिया", "नमस्ते"),
        ("नमस्ते दुनिया", "नमस्ते"),
        ("शुभ प्रभात", "शुभ"),
    ]
    dels = compute_frequent_deletions(_details_for(pairs), top_n=5)
    assert dels["_all"][0] == ("दुनिया", 2)
    assert ("प्रभात", 1) in dels["_all"]


def test_compute_frequent_insertions_counts_repeats():
    """Insertions surface when hyp produces extra tokens not in ref."""
    pairs = [
        ("नमस्ते", "नमस्ते दुनिया"),
        ("नमस्ते", "नमस्ते दुनिया"),
        ("शुभ", "शुभ प्रभात"),
    ]
    ins = compute_frequent_insertions(_details_for(pairs), top_n=5)
    assert ins["_all"][0] == ("दुनिया", 2)
    assert ("प्रभात", 1) in ins["_all"]


def test_compute_frequent_substitutions_returns_empty_for_perfect_match():
    details = text_error_details("नमस्ते दुनिया", "नमस्ते दुनिया", None)
    assert compute_frequent_substitutions(details, top_n=5) == {"_all": []}
    assert compute_frequent_deletions(details, top_n=5) == {"_all": []}
    assert compute_frequent_insertions(details, top_n=5) == {"_all": []}


# ---------------------------------------------------------------------------
# compute_total_error_rate
# ---------------------------------------------------------------------------


def test_compute_total_error_rate_zero_for_perfect_match():
    metrics = text_error_rates("नमस्ते दुनिया", "नमस्ते दुनिया", None)
    assert compute_total_error_rate(metrics) == 0.0


def test_compute_total_error_rate_matches_combined_denominator():
    """TER = total_errors / combined_total. One sub of three word tokens
    yields 1/3 regardless of how the categories slice the denominator.
    """
    metrics = text_error_rates("मैंने आम खाया", "मैंने केला खाया", None)
    assert compute_total_error_rate(metrics) == pytest.approx(1 / 3)


def test_compute_total_error_rate_can_exceed_one_with_insertions():
    """When the hyp has more tokens than the ref (lots of insertions),
    TER can exceed 1.0 since the denominator is ref-side."""
    metrics = text_error_rates("नमस्ते", "नमस्ते दुनिया शुभ प्रभात मित्र", None)
    assert compute_total_error_rate(metrics) > 1.0


# ---------------------------------------------------------------------------
# compute_category_contributions
# ---------------------------------------------------------------------------


def test_compute_category_contributions_counts_and_pct():
    """One sub in WORD: ref_tokens=3, correct=2, error_count=1, accuracy=2/3."""
    metrics = text_error_rates("मैंने आम खाया", "मैंने केला खाया", None)
    contribs = compute_category_contributions(metrics)

    word = contribs["WORD"]
    assert word["correct"] == 2
    assert word["substitutions"] == 1
    assert word["deletions"] == 0
    assert word["insertions"] == 0
    assert word["ref_tokens"] == 3
    assert word["error_count"] == 1
    assert word["correct_pct"] == pytest.approx(2 / 3 * 100)
    # WORD owns the only error, so its contribution is 100%.
    assert word["contribution_pct"] == 100.0


def test_compute_category_contributions_handles_empty_category():
    metrics = text_error_rates("नमस्ते दुनिया", "नमस्ते दुनिया", None)
    contribs = compute_category_contributions(metrics)
    # Empty category: no division-by-zero, percentages clamped to 0.
    assert contribs["PUNCT"]["ref_tokens"] == 0
    assert contribs["PUNCT"]["correct_pct"] == 0.0
    assert contribs["PUNCT"]["contribution_pct"] == 0.0


def test_compute_category_contributions_pct_sums_to_one_hundred():
    """Per-category contribution_pct values sum to 100 across categories
    that have errors (perfect-match categories contribute 0)."""
    metrics = text_error_rates("आम केला", "सेब अंगूर", None)
    contribs = compute_category_contributions(metrics)
    total_pct = sum(c["contribution_pct"] for c in contribs.values())
    assert total_pct == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# compute_error_type_distribution
# ---------------------------------------------------------------------------


def test_compute_error_type_distribution_pure_substitution():
    metrics = text_error_rates("मैंने आम खाया", "मैंने केला खाया", None)
    dist = compute_error_type_distribution(metrics)
    assert dist["WORD"]["substitution_pct"] == 100.0
    assert dist["WORD"]["insertion_pct"] == 0.0
    assert dist["WORD"]["deletion_pct"] == 0.0


def test_compute_error_type_distribution_mixed():
    """When all three error types occur, the distribution percentages
    must be nonzero and sum to 100."""
    # Aligner produces 1 sub + 2 ins + 1 del here.
    metrics = text_error_rates("आम केला सेब", "अंगूर सेब नया कुछ", None)
    dist = compute_error_type_distribution(metrics)
    assert dist["WORD"]["substitution_pct"] > 0
    assert dist["WORD"]["insertion_pct"] > 0
    assert dist["WORD"]["deletion_pct"] > 0
    total = (
        dist["WORD"]["substitution_pct"]
        + dist["WORD"]["insertion_pct"]
        + dist["WORD"]["deletion_pct"]
    )
    assert total == pytest.approx(100.0)


def test_compute_error_type_distribution_zero_when_no_errors():
    metrics = text_error_rates("नमस्ते दुनिया", "नमस्ते दुनिया", None)
    dist = compute_error_type_distribution(metrics)
    assert dist["WORD"]["substitution_pct"] == 0.0
    assert dist["WORD"]["insertion_pct"] == 0.0
    assert dist["WORD"]["deletion_pct"] == 0.0


# ---------------------------------------------------------------------------
# compute_error_summary — full structure
# ---------------------------------------------------------------------------


def test_compute_error_summary_has_all_expected_keys():
    metrics = text_error_rates("मैंने आम खाया", "मैंने केला खाया", None)
    details = text_error_details("मैंने आम खाया", "मैंने केला खाया", None)
    summary = compute_error_summary(metrics, details, top_n=5)

    expected = {
        "total_error_rate",
        "total_correct_pct",
        "contributions",
        "error_type_distribution",
        "frequent_substitutions",
        "frequent_deletions",
        "frequent_insertions",
        "frequent_sandhi_merges",
        "frequent_sandhi_splits",
    }
    assert set(summary.keys()) == expected


def test_compute_error_summary_total_correct_pct_matches_ratio():
    """One sub among three ref tokens → total_correct_pct = 2/3 * 100."""
    metrics = text_error_rates("मैंने आम खाया", "मैंने केला खाया", None)
    details = text_error_details("मैंने आम खाया", "मैंने केला खाया", None)
    summary = compute_error_summary(metrics, details, top_n=5)
    assert summary["total_correct_pct"] == pytest.approx(2 / 3 * 100)
    assert summary["total_error_rate"] == pytest.approx(1 / 3)


def test_compute_error_summary_top_n_applies_to_all_frequency_tables():
    """Generate 4 distinct Hindi subs and confirm top_n=2 truncates."""
    refs = ["आम", "केला", "सेब", "अंगूर"]
    hyps = ["कुत्ता", "बिल्ली", "गाय", "घोड़ा"]
    pairs = [(f"मैंने {r} खाया", f"मैंने {h} खाया") for r, h in zip(refs, hyps)]
    metrics = text_error_rates(" ".join(p[0] for p in pairs), " ".join(p[1] for p in pairs), None)
    details = _details_for(pairs)
    summary = compute_error_summary(metrics, details, top_n=2)
    assert len(summary["frequent_substitutions"]["_all"]) == 2
