import json
import warnings
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from typing import Optional

from .constants import (
    calculate_combined_total,
    init_stat_dict,
)
from .domain_config import DomainConfig
from .measure import text_error_details, text_error_rates
from .reporting import format_summary_lines


def _validate_record(record, ref_field, hyp_field) -> Optional[str]:
    """Return the reason a record cannot be evaluated, or None if it can.

    A record must be a JSON object carrying both text fields as strings.
    None (JSON null) or non-string values would otherwise silently score
    as empty/garbage text instead of surfacing the data problem. An
    empty string is allowed — an empty reference is a legitimate
    transcript (e.g. silence), unlike a missing one.
    """
    if not isinstance(record, dict):
        return f"record is not a JSON object (got {type(record).__name__})"
    for field in (ref_field, hyp_field):
        if field not in record:
            return f"missing field {field!r}"
        value = record[field]
        if value is None:
            return f"field {field!r} is null"
        if not isinstance(value, str):
            return f"field {field!r} is not text (got {type(value).__name__})"
    return None


def _evaluate_one(
    record,
    ref_field,
    hyp_field,
    source_dataset_field,
    domain_config,
    normalize,
    use_sandhi,
    collect_error_details,
) -> dict:
    """Evaluate a single record. Module-level so worker processes can
    pickle it under the spawn start method."""
    # Shallow-copy so the caller's dicts are left untouched.
    data = dict(record)

    # Canonicalize the dataset id under "source_dataset" so
    # downstream aggregation works regardless of which field
    # name the caller configured. Non-string ids (numbers, JSON
    # arrays/objects) are stringified — aggregation uses the
    # value as a grouping key. Only a missing/null/empty field
    # falls back to "unknown"; falsy scalars like 0 or false
    # are real dataset ids.
    ds_value = data.get(source_dataset_field)
    if ds_value is None or ds_value == "":
        ds_value = "unknown"
    data["source_dataset"] = ds_value if isinstance(ds_value, str) else str(ds_value)

    ref = data[ref_field]
    hyp = data[hyp_field]

    report = text_error_rates(ref, hyp, domain_config, normalize, use_sandhi)
    data["detailed_report"] = report

    if collect_error_details:
        data["error_details"] = text_error_details(ref, hyp, domain_config, normalize, use_sandhi)

    return data


def evaluate_records(
    records,
    ref_field="transcript_cleaned",
    hyp_field="prediction",
    source_dataset_field="source_dataset",
    domain_config: Optional[DomainConfig] = None,
    normalize: bool = True,
    use_sandhi: bool = True,
    collect_error_details: bool = False,
    workers: Optional[int] = None,
    skip_bad_records: bool = False,
) -> list[dict]:
    """
    Compute error metrics for an in-memory iterable of sample records.

    This is the core batch-evaluation API: it takes plain dicts (from any
    source — a parsed JSONL file, a pandas DataFrame's to_dict records, a
    training loop's predictions) and returns one result dict per record.
    compute_sample_errors() is a thin JSONL file loader over this
    function.

    Records are validated before evaluation: each must be a dict with
    both text fields present as strings. A bad record raises ValueError
    naming the record number and the reason (fail fast, so a data
    problem cannot silently distort metrics); pass skip_bad_records=True
    to skip bad records with a warning instead.

    Args:
        records: Iterable of dicts, each holding at least the reference
            and hypothesis text fields. Input dicts are not mutated;
            each result is a shallow copy with the report keys added.
        ref_field: Field name for reference text
        hyp_field: Field name for hypothesis text
        source_dataset_field: Field name for dataset identifier; its value
            is copied to the canonical "source_dataset" key on each result
            ("unknown" when missing) so aggregation can group by dataset
            regardless of the configured field name
        domain_config: Domain configuration (None for no domain)
        normalize: If True, apply normalization for matching (default: True)
        use_sandhi: If True, detect sandhi splits/merges (default: True)
        collect_error_details: If True, also collect per-token error records
            for frequency analysis. Stored in each result's "error_details" key.
        workers: Number of worker processes for parallel evaluation.
            None or 1 evaluates sequentially (the default); larger values
            spread records over a process pool. Results are identical and
            in input order either way. Parallel mode materializes the
            records iterable into a list before dispatching.
        skip_bad_records: If True, skip records that fail validation
            (with a warning) instead of raising ValueError (default: False)

    Returns:
        List of result dictionaries with detailed reports
        (one per valid record)
    """
    valid_records = []
    for number, record in enumerate(records, start=1):
        reason = _validate_record(record, ref_field, hyp_field)
        if reason is None:
            valid_records.append(record)
        elif skip_bad_records:
            warnings.warn(f"Skipping record {number}: {reason}", stacklevel=2)
        else:
            raise ValueError(
                f"Record {number}: {reason}. "
                f"Pass skip_bad_records=True to skip such records instead."
            )
    records = valid_records

    evaluate = partial(
        _evaluate_one,
        ref_field=ref_field,
        hyp_field=hyp_field,
        source_dataset_field=source_dataset_field,
        domain_config=domain_config,
        normalize=normalize,
        use_sandhi=use_sandhi,
        collect_error_details=collect_error_details,
    )

    if workers is not None and workers > 1:
        # Per-sample cost varies by orders of magnitude (alignment is
        # quadratic in sample length), so small batches keep skewed
        # workloads balanced; ~32 chunks per worker amortizes IPC on
        # large record counts without starving anyone.
        chunksize = max(1, len(records) // (workers * 32))
        with ProcessPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(evaluate, records, chunksize=chunksize))

    return [evaluate(record) for record in records]


def compute_sample_errors(
    input_file,
    output_file=None,
    ref_field="transcript_cleaned",
    hyp_field="prediction",
    source_dataset_field="source_dataset",
    domain_config: Optional[DomainConfig] = None,
    normalize: bool = True,
    use_sandhi: bool = True,
    collect_error_details: bool = False,
    workers: Optional[int] = None,
    skip_bad_records: bool = False,
) -> list[dict]:
    """
    Compute error metrics for all samples in a JSONL file.

    Thin file-loading wrapper over evaluate_records(): parses one JSON
    record per line and evaluates them in memory.

    Bad input fails fast with the file name and line number — a line
    that is not valid JSON, or a record missing its text fields (or
    carrying them as null/non-string) raises ValueError so a data
    problem cannot silently distort metrics. Blank lines are not
    records and are always skipped. Pass skip_bad_records=True to skip
    bad lines/records with a warning instead.

    Args:
        input_file: Path to JSONL file
        output_file: Optional path to save detailed results
        ref_field: Field name for reference text
        hyp_field: Field name for hypothesis text
        source_dataset_field: Field name for dataset identifier; its value
            is copied to the canonical "source_dataset" key on each result
            ("unknown" when missing) so aggregation can group by dataset
            regardless of the configured field name
        domain_config: Domain configuration (None for no domain)
        normalize: If True, apply normalization for matching (default: True)
        use_sandhi: If True, detect sandhi splits/merges (default: True)
        collect_error_details: If True, also collect per-token error records
            for frequency analysis. Stored in each result's "error_details" key.
        workers: Number of worker processes for parallel evaluation
            (None or 1 = sequential; see evaluate_records)
        skip_bad_records: If True, skip unparseable lines and invalid
            records (with a warning) instead of raising ValueError

    Returns:
        List of result dictionaries with detailed reports
        (one per valid record)
    """
    # Parse and validate here, where line numbers exist — an error that
    # says "line 1042" is actionable; "record 1037" (after blank lines)
    # is not.
    records = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                if skip_bad_records:
                    warnings.warn(
                        f"{input_file}, line {line_number}: skipping invalid JSON: {e}",
                        stacklevel=2,
                    )
                    continue
                raise ValueError(
                    f"{input_file}, line {line_number}: invalid JSON: {e}. "
                    f"Pass skip_bad_records=True to skip such lines instead."
                ) from e

            reason = _validate_record(record, ref_field, hyp_field)
            if reason is None:
                records.append(record)
            elif skip_bad_records:
                warnings.warn(
                    f"{input_file}, line {line_number}: skipping record: {reason}",
                    stacklevel=2,
                )
            else:
                raise ValueError(
                    f"{input_file}, line {line_number}: {reason}. "
                    f"Pass skip_bad_records=True to skip such records instead."
                )

    results = evaluate_records(
        records,
        ref_field=ref_field,
        hyp_field=hyp_field,
        source_dataset_field=source_dataset_field,
        domain_config=domain_config,
        normalize=normalize,
        use_sandhi=use_sandhi,
        collect_error_details=collect_error_details,
        workers=workers,
    )

    # Save detailed results if output file is specified
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            for result in results:
                # Don't persist error_details to JSONL (large, used only in-memory)
                out = {k: v for k, v in result.items() if k != "error_details"}
                f.write(json.dumps(out, ensure_ascii=False) + "\n")

    return results


def aggregate_error_details(sample_results: list[dict]) -> list[dict]:
    """
    Concatenate all error_details from sample results into one flat list.

    Args:
        sample_results: from compute_sample_errors(collect_error_details=True)

    Returns:
        Flat list of all error record dicts across all samples.
    """
    all_details = []
    for result in sample_results:
        all_details.extend(result.get("error_details", []))
    return all_details


def compute_aggregate_metrics(
    sample_results,
) -> dict[str, dict[str, dict[str, dict[str, float | int]]]]:
    """
    Aggregate metrics across all samples.

    Categories are derived entirely from the sample reports: whatever
    compute_sample_errors measured (including domain categories) is
    aggregated. No domain configuration is needed here — it was already
    applied at measurement time.

    Args:
        sample_results: List of result dictionaries from compute_sample_errors

    Returns:
        Dictionary with 'overall' and 'by_dataset' aggregated metrics
    """
    overall_agg = init_stat_dict()
    dataset_aggs = defaultdict(init_stat_dict)

    for res in sample_results:
        ds = res.get("source_dataset", "unknown")
        report = res["detailed_report"]

        # Aggregate every category present in the data. Dropping an
        # unexpected category would also shrink the combined denominator
        # and silently deflate every other category's rate.
        for cat, counts in report.items():
            for agg in (overall_agg, dataset_aggs[ds]):
                if cat not in agg:
                    agg.update(init_stat_dict([cat]))
                agg[cat]["substitutions"] += counts["substitutions"]
                agg[cat]["insertions"] += counts["insertions"]
                agg[cat]["deletions"] += counts["deletions"]
                agg[cat]["correct"] += counts["correct"]
                agg[cat]["total"] += counts["total_ref"]
                agg[cat]["sandhi_hits"] += counts["sandhi_hits"]

    def calculate_rates(agg):
        # Calculate combined denominator across ALL categories
        combined_total = calculate_combined_total(agg)

        metrics = {}
        for cat in agg:
            a = agg[cat]
            errs = a["substitutions"] + a["insertions"] + a["deletions"]
            metrics[cat] = {
                "error_rate": errs / max(1, combined_total),  # Combined denominator
                "substitutions": a["substitutions"],
                "insertions": a["insertions"],
                "deletions": a["deletions"],
                "correct": a["correct"],
                "sandhi_hits": a["sandhi_hits"],
                "total": a["total"],
                "combined_total": combined_total,  # Store for reference
            }
        return metrics

    return {
        "overall": calculate_rates(overall_agg),
        "by_dataset": {ds: calculate_rates(stats) for ds, stats in dataset_aggs.items()},
    }


def print_evaluation_summary(agg_results) -> None:
    """
    Print evaluation summary table.

    Columns are derived from the categories present in the aggregated
    data; the domain category (if any) is shown as ER_DOMAIN.

    Args:
        agg_results: Aggregated results from compute_aggregate_metrics
    """
    print()
    for line in format_summary_lines(agg_results):
        print(line)
    print()
