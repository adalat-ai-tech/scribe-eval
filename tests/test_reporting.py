"""Tests for reporting / formatting helpers."""

from scribe import (
    align_arrays,
    compute_aggregate_metrics,
    compute_sample_errors,
    domain_aware_tokenizer,
    extract_error_rates,
    format_alignment_dict,
    format_alignment_table,
    format_dataset_table,
    format_error_counts_table,
    format_metrics_dict,
    text_error_rates,
    write_summary_to_file,
)


def _basic_report(legal_domain):
    return text_error_rates("charged u/s 302 IPC", "charged us 302 IPC", legal_domain)


def test_format_metrics_dict_returns_expected_keys(legal_domain):
    """format_metrics_dict pulls the headline metrics into a flat dict.

    The domain category present in the data is reported under the
    fixed DER label, plus Sandhi and Total counts.
    """
    report = _basic_report(legal_domain)
    formatted = format_metrics_dict(report)
    assert isinstance(formatted, dict)
    # Headline rate keys are formatted as percent strings.
    for key in ("WER", "NER", "PER", "DER"):
        assert key in formatted
        assert isinstance(formatted[key], str)
        assert formatted[key].endswith("%")
    assert "Sandhi" in formatted
    assert "Total" in formatted


def test_format_metrics_dict_without_domain_config():
    """Without a domain config there is no domain-label key, but Sandhi
    and Total are still reported (they do not depend on any domain)."""
    report = text_error_rates("the case is closed", "the case was closed", None)
    formatted = format_metrics_dict(report)
    for key in ("WER", "NER", "PER", "Sandhi", "Total"):
        assert key in formatted
    assert "DER" not in formatted
    assert "LER" not in formatted


def test_write_summary_to_file_without_domain_config(tmp_path):
    """write_summary_to_file must produce a complete table when called
    with domain_config=None (regression: it raised KeyError 'DER').
    With no domain category in the data there is no domain column."""
    report = text_error_rates("the case is closed", "the case was closed", None)
    agg = {"overall": report, "by_dataset": {"test-set": report}}
    out = tmp_path / "summary.txt"
    write_summary_to_file(agg, str(out))
    content = out.read_text(encoding="utf-8")
    assert "OVERALL" in content
    assert "test-set" in content
    assert "WER" in content
    # No domain data -> no domain column, no filler values.
    assert "DER" not in content
    assert "N/A" not in content


def test_summary_domain_column_inferred_from_data(tmp_path, legal_domain):
    """The domain column comes from the data and is always labelled DER:
    a batch measured with any domain shows a DER column with no
    reporting-time configuration."""
    report = text_error_rates("charged u/s 302 IPC", "charged us 302 IPC", legal_domain)
    agg = {"overall": report, "by_dataset": {"court": report}}

    out = tmp_path / "summary.txt"
    write_summary_to_file(agg, str(out))
    content = out.read_text(encoding="utf-8")
    assert "DER" in content
    # The fixed DER label is used, not the category name or config label.
    assert "LEGAL" not in content
    assert "LER" not in content


def test_extract_error_rates_returns_floats_and_sandhi_count(legal_domain):
    """extract_error_rates returns the raw numeric rates (floats) plus
    sandhi count (int)."""
    report = _basic_report(legal_domain)
    rates = extract_error_rates(report)
    assert isinstance(rates, dict)
    for key in ("wer", "ner", "per", "der"):
        assert key in rates
        assert isinstance(rates[key], (int, float))
        assert 0.0 <= rates[key] <= 1.0
    assert "sandhi" in rates
    assert isinstance(rates["sandhi"], int)


def test_format_alignment_table_returns_rows_for_aligned_tokens(legal_domain):
    """format_alignment_table consumes aligned token streams (the output
    of align_arrays) and returns a row per aligned position.
    """
    ref_toks, ref_tags = domain_aware_tokenizer("charged u/s 302", legal_domain)
    hyp_toks, hyp_tags = domain_aware_tokenizer("charged us 302", legal_domain)
    aligned_ref, aligned_hyp, _ = align_arrays(ref_toks, ref_tags, hyp_toks, hyp_tags)
    rows = format_alignment_table(aligned_ref, aligned_hyp)
    assert isinstance(rows, list)
    assert rows, "Expected at least one alignment row"
    # Each row is a dict (column -> value).
    assert all(isinstance(row, dict) for row in rows)


def test_format_dataset_table_takes_aggregate_shape(tmp_path, legal_domain):
    """format_dataset_table consumes the dict returned by
    compute_aggregate_metrics, which has the shape
    {"overall": ..., "by_dataset": {dataset: report, ...}}.
    """
    # Build a tiny aggregate from two synthetic samples spanning two datasets.
    import json

    inp = tmp_path / "predictions.jsonl"
    inp.write_text(
        "\n".join(
            [
                json.dumps(
                    {"transcript_cleaned": "a b", "prediction": "a b", "source_dataset": "ds1"}
                ),
                json.dumps(
                    {"transcript_cleaned": "x y", "prediction": "x z", "source_dataset": "ds2"}
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    results = compute_sample_errors(str(inp), domain_config=legal_domain)
    agg = compute_aggregate_metrics(results)
    rows = format_dataset_table(agg)
    assert isinstance(rows, list)
    assert rows, "Expected at least the OVERALL row"
    # An OVERALL row plus one per dataset.
    dataset_names = {row.get("Dataset") for row in rows}
    assert "OVERALL" in dataset_names
    assert "ds1" in dataset_names
    assert "ds2" in dataset_names


def test_write_summary_to_file_creates_a_readable_file(tmp_path, legal_domain):
    """write_summary_to_file persists a formatted aggregate summary."""
    import json

    inp = tmp_path / "predictions.jsonl"
    inp.write_text(
        json.dumps({"transcript_cleaned": "a b", "prediction": "a b", "source_dataset": "ds1"})
        + "\n",
        encoding="utf-8",
    )
    results = compute_sample_errors(str(inp), domain_config=legal_domain)
    agg = compute_aggregate_metrics(results)

    target = tmp_path / "summary.txt"
    write_summary_to_file(agg, str(target))
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert content.strip(), "Summary file is empty"
    assert "OVERALL" in content


def test_format_error_counts_table_emits_four_rows_per_category(legal_domain):
    """For each category in the report, format_error_counts_table emits
    four rows (Substitutions, Insertions, Deletions, Correct) with counts
    that mirror the underlying report.
    """
    report = _basic_report(legal_domain)
    rows = format_error_counts_table(report)
    assert isinstance(rows, list)
    assert all(isinstance(row, dict) for row in rows)
    by_cat: dict = {}
    for row in rows:
        by_cat.setdefault(row["Category"], {})[row["Type"]] = row["Count"]
    assert by_cat, "Expected at least one category in the counts table"
    for cat, types in by_cat.items():
        assert set(types) == {"Substitutions", "Insertions", "Deletions", "Correct"}
        assert types["Substitutions"] == report[cat]["substitutions"]
        assert types["Insertions"] == report[cat]["insertions"]
        assert types["Deletions"] == report[cat]["deletions"]
        assert types["Correct"] == report[cat]["correct"]


def test_format_alignment_dict_classifies_each_position(legal_domain):
    """format_alignment_dict labels each aligned position with one of
    correct / substitution / insertion / deletion / sandhi, and exposes
    ref_text, hyp_text, and token_type fields.
    """
    ref_toks, ref_tags = domain_aware_tokenizer("charged u/s 302", legal_domain)
    hyp_toks, hyp_tags = domain_aware_tokenizer("charged us 302", legal_domain)
    aligned_ref, aligned_hyp, _ = align_arrays(ref_toks, ref_tags, hyp_toks, hyp_tags)
    rows = format_alignment_dict(aligned_ref, aligned_hyp)
    assert rows, "Expected at least one alignment row"
    valid_types = {"correct", "substitution", "insertion", "deletion", "sandhi"}
    for row in rows:
        assert row["error_type"] in valid_types
        assert "ref_text" in row
        assert "hyp_text" in row
        assert "token_type" in row
    # The u/s -> us substitution should land as a substitution row.
    error_types = [row["error_type"] for row in rows]
    assert "substitution" in error_types
