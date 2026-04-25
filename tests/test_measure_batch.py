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
    agg = compute_aggregate_metrics(results, domain_config=legal_domain)
    assert "overall" in agg
    assert "by_dataset" in agg
    assert set(agg["by_dataset"].keys()) == {"dataset-a", "dataset-b"}


def test_aggregate_overall_metrics_have_required_categories(sample_jsonl, legal_domain):
    results = compute_sample_errors(str(sample_jsonl), domain_config=legal_domain)
    agg = compute_aggregate_metrics(results, domain_config=legal_domain)
    overall = agg["overall"]
    for cat in ("WORD", "NUMERAL", "PUNCT", "LEGAL"):
        assert cat in overall
        assert "error_rate" in overall[cat]


def test_per_dataset_totals_reflect_per_dataset_records(sample_jsonl, legal_domain):
    """The dataset-a aggregate must reflect the two dataset-a samples,
    independent of dataset-b's samples."""
    results = compute_sample_errors(str(sample_jsonl), domain_config=legal_domain)
    agg = compute_aggregate_metrics(results, domain_config=legal_domain)
    # dataset-a has one perfect sample and one with a numeral substitution
    # ("302" -> "303"). So its NUMERAL substitutions should be exactly 1.
    assert agg["by_dataset"]["dataset-a"]["NUMERAL"]["substitutions"] == 1
    # dataset-b has one perfect sample and one with a date substitution.
    # Its NUMERAL category should also report at least one error.
    assert agg["by_dataset"]["dataset-b"]["NUMERAL"]["substitutions"] >= 1


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
