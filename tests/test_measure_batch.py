"""Tests for the batch-evaluation pipeline."""

import json

import pytest

from scribe import compute_aggregate_metrics, compute_sample_errors


@pytest.fixture
def sample_jsonl(tmp_path):
    """Write a tiny JSONL file with two datasets of two samples each."""
    records = [
        {
            "transcript_cleaned": "the case is closed.",
            "prediction": "the case is closed.",
            "source_dataset": "dataset-a",
        },
        {
            "transcript_cleaned": "charged u/s 302 IPC",
            "prediction": "charged u/s 303 IPC",
            "source_dataset": "dataset-a",
        },
        {
            "transcript_cleaned": "amount paid was Rs. 10,500",
            "prediction": "amount paid was Rs. 10,500",
            "source_dataset": "dataset-b",
        },
        {
            "transcript_cleaned": "hearing on 22.05.2023",
            "prediction": "hearing on 23.05.2023",
            "source_dataset": "dataset-b",
        },
    ]
    path = tmp_path / "predictions.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def test_compute_sample_errors_returns_one_entry_per_record(sample_jsonl, legal_domain):
    results = compute_sample_errors(str(sample_jsonl), domain_config=legal_domain)
    assert len(results) == 4


def test_compute_sample_errors_writes_detailed_output(tmp_path, sample_jsonl, legal_domain):
    out = tmp_path / "detailed.jsonl"
    compute_sample_errors(str(sample_jsonl), output_file=str(out), domain_config=legal_domain)
    assert out.exists()
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4
    # Each line must be valid JSON. The detailed per-category breakdown
    # is nested under the "detailed_report" key.
    parsed = [json.loads(line) for line in lines]
    assert all("detailed_report" in p for p in parsed)
    assert all("WORD" in p["detailed_report"] for p in parsed)


def test_aggregate_metrics_has_overall_and_by_dataset(sample_jsonl, legal_domain):
    results = compute_sample_errors(str(sample_jsonl), domain_config=legal_domain)
    agg = compute_aggregate_metrics(results)
    assert "overall" in agg
    assert "by_dataset" in agg
    assert set(agg["by_dataset"].keys()) == {"dataset-a", "dataset-b"}


def test_aggregate_overall_metrics_have_required_categories(sample_jsonl, legal_domain):
    results = compute_sample_errors(str(sample_jsonl), domain_config=legal_domain)
    agg = compute_aggregate_metrics(results)
    overall = agg["overall"]
    for cat in ("WORD", "NUMERAL", "PUNCT", "LEGAL"):
        assert cat in overall
        assert "error_rate" in overall[cat]


def test_per_dataset_totals_reflect_per_dataset_records(sample_jsonl, legal_domain):
    """The dataset-a aggregate must reflect the two dataset-a samples,
    independent of dataset-b's samples."""
    results = compute_sample_errors(str(sample_jsonl), domain_config=legal_domain)
    agg = compute_aggregate_metrics(results)
    # dataset-a has one perfect sample and one with a numeral substitution
    # ("302" -> "303"). So its NUMERAL substitutions should be exactly 1.
    assert agg["by_dataset"]["dataset-a"]["NUMERAL"]["substitutions"] == 1
    # dataset-b has one perfect sample and one with a date substitution.
    # Its NUMERAL category should also report at least one error.
    assert agg["by_dataset"]["dataset-b"]["NUMERAL"]["substitutions"] >= 1


def test_print_evaluation_summary_without_domain_config(sample_jsonl, capsys):
    """print_evaluation_summary must work on a batch measured without
    any domain (regression: it raised KeyError 'DER'). No domain
    category in the data means no domain column at all."""
    from scribe import print_evaluation_summary

    results = compute_sample_errors(str(sample_jsonl), domain_config=None)
    agg = compute_aggregate_metrics(results)
    print_evaluation_summary(agg)
    out = capsys.readouterr().out
    assert "OVERALL" in out
    assert "dataset-a" in out
    assert "dataset-b" in out
    # No domain category in the data -> no domain column at all.
    assert "DER" not in out
    assert "N/A" not in out


def test_field_name_overrides(tmp_path, legal_domain):
    """compute_sample_errors honours custom ref/hyp field names."""
    records = [
        {"reference": "hello", "hypothesis": "hello", "source_dataset": "x"},
    ]
    path = tmp_path / "custom.jsonl"
    path.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
    results = compute_sample_errors(
        str(path), ref_field="reference", hyp_field="hypothesis", domain_config=legal_domain
    )
    assert len(results) == 1


def test_custom_dataset_field_propagates_to_by_dataset(tmp_path):
    """A custom source_dataset_field must still group by_dataset
    (regression: all datasets collapsed into 'unknown')."""
    records = [
        {"transcript_cleaned": "one two", "prediction": "one two", "ds": "set-a"},
        {"transcript_cleaned": "three four", "prediction": "three four", "ds": "set-b"},
    ]
    path = tmp_path / "custom_ds.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    results = compute_sample_errors(str(path), source_dataset_field="ds")
    agg = compute_aggregate_metrics(results)
    assert set(agg["by_dataset"].keys()) == {"set-a", "set-b"}


def test_aggregation_includes_domain_categories_from_data(tmp_path, legal_domain):
    """Aggregation counts every category present in the sample reports.
    A batch measured with the legal domain has its LEGAL error counted
    and its LEGAL tokens in the combined denominator (regression: the
    category was silently dropped, reporting 0 errors and deflating
    every other category's rate)."""
    records = [
        {"transcript_cleaned": "charged u/s 302", "prediction": "charged us 302"},
    ]
    path = tmp_path / "legal.jsonl"
    path.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")

    results = compute_sample_errors(str(path), domain_config=legal_domain)
    overall = compute_aggregate_metrics(results)["overall"]

    # Ground truth: 3 ref tokens (charged/WORD, u/s/LEGAL, 302/NUMERAL),
    # exactly one error — the LEGAL substitution u/s -> us.
    assert "LEGAL" in overall
    assert overall["LEGAL"]["substitutions"] == 1
    assert overall["LEGAL"]["combined_total"] == 3
    total_errors = sum(
        c["substitutions"] + c["insertions"] + c["deletions"] for c in overall.values()
    )
    assert total_errors == 1


def test_aggregate_error_rate_recomputed_from_summed_counts(tmp_path):
    """Aggregate rates must be recomputed from summed counts over the
    combined denominator — never averaged per-sample rates. Two samples,
    8 WORD tokens total, exactly 1 substitution => WER 1/8."""
    records = [
        {"transcript_cleaned": "one two three four", "prediction": "one two three four"},
        {"transcript_cleaned": "one two three four", "prediction": "one two tree four"},
    ]
    path = tmp_path / "rates.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    agg = compute_aggregate_metrics(compute_sample_errors(str(path)))
    word = agg["overall"]["WORD"]
    assert word["substitutions"] == 1
    assert word["total"] == 8
    assert word["combined_total"] == 8
    assert word["error_rate"] == 1 / 8


def test_sandhi_hits_summed_across_samples_and_datasets(tmp_path):
    """sandhi_hits must sum across samples in both overall and
    by_dataset aggregates (paper Fig. 2 pair has 2 hits per sample)."""
    ref = "ഇന്ന് അല്ലെങ്കിൽ നാളെയാകട്ടെ"
    hyp = "ഇന്നല്ലെങ്കിൽ നാളെ ആകട്ടെ"
    records = [
        {"transcript_cleaned": ref, "prediction": hyp, "source_dataset": "d1"},
        {"transcript_cleaned": ref, "prediction": hyp, "source_dataset": "d1"},
        {"transcript_cleaned": ref, "prediction": hyp, "source_dataset": "d2"},
    ]
    path = tmp_path / "sandhi.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    agg = compute_aggregate_metrics(compute_sample_errors(str(path)))
    assert agg["overall"]["WORD"]["sandhi_hits"] == 6
    assert agg["by_dataset"]["d1"]["WORD"]["sandhi_hits"] == 4
    assert agg["by_dataset"]["d2"]["WORD"]["sandhi_hits"] == 2


def test_non_string_dataset_ids_do_not_break_aggregation(tmp_path):
    """A numeric or JSON-array dataset id must not crash aggregation
    with an unhashable-type TypeError (PR review issue); non-string ids
    are stringified for grouping."""
    records = [
        {"transcript_cleaned": "one two", "prediction": "one two", "ds": 7},
        {"transcript_cleaned": "three four", "prediction": "three four", "ds": ["a", "b"]},
        {"transcript_cleaned": "five six", "prediction": "five six", "ds": {"k": "v"}},
    ]
    path = tmp_path / "odd_ids.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    results = compute_sample_errors(str(path), source_dataset_field="ds")
    agg = compute_aggregate_metrics(results)
    keys = agg["by_dataset"].keys()
    assert all(isinstance(k, str) for k in keys)
    assert "7" in keys
    assert len(keys) == 3


def test_falsy_dataset_ids_are_real_values(tmp_path):
    """Falsy scalars like 0 or false are legitimate dataset ids and must
    not collapse into 'unknown' (PR review issue); only a missing, null,
    or empty field falls back to 'unknown'."""
    records = [
        {"transcript_cleaned": "a b", "prediction": "a b", "ds": 0},
        {"transcript_cleaned": "c d", "prediction": "c d", "ds": False},
        {"transcript_cleaned": "e f", "prediction": "e f", "ds": ""},
        {"transcript_cleaned": "g h", "prediction": "g h", "ds": None},
        {"transcript_cleaned": "i j", "prediction": "i j"},
    ]
    path = tmp_path / "falsy_ids.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    results = compute_sample_errors(str(path), source_dataset_field="ds")
    agg = compute_aggregate_metrics(results)
    assert set(agg["by_dataset"].keys()) == {"0", "False", "unknown"}
