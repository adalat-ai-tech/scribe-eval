import json
from collections import defaultdict
from typing import Optional

from .constants import (
    TABLE_WIDTH,
    calculate_combined_total,
    format_table_header,
    get_categories,
    init_stat_dict,
)
from .domain_config import DomainConfig
from .measure import text_error_details, text_error_rates
from .reporting import format_dataset_table


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
) -> list[dict]:
    """
    Compute error metrics for all samples in a JSONL file.

    Args:
        input_file: Path to JSONL file
        output_file: Optional path to save detailed results
        ref_field: Field name for reference text
        hyp_field: Field name for hypothesis text
        source_dataset_field: Field name for dataset identifier
        domain_config: Domain configuration (None for no domain)
        normalize: If True, apply normalization for matching (default: True)
        collect_error_details: If True, also collect per-token error records
            for frequency analysis. Stored in each result's "error_details" key.

    Returns:
        List of result dictionaries with detailed reports
    """
    results = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            # Ensure we have a source_dataset field
            if source_dataset_field not in data or data[source_dataset_field] is None:
                data[source_dataset_field] = "unknown"

            ref = data[ref_field]
            hyp = data[hyp_field]

            # Pass domain_config, normalize and use_sandhi to text_error_rates
            report = text_error_rates(ref, hyp, domain_config, normalize, use_sandhi)
            data["detailed_report"] = report

            if collect_error_details:
                data["error_details"] = text_error_details(
                    ref, hyp, domain_config, normalize, use_sandhi
                )

            results.append(data)

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
    sample_results, domain_config: Optional[DomainConfig] = None
) -> dict[str, dict[str, dict[str, dict[str, float | int]]]]:
    """
    Aggregate metrics across all samples.

    Args:
        sample_results: List of result dictionaries from compute_sample_errors
        domain_config: Domain configuration (None for no domain)

    Returns:
        Dictionary with 'overall' and 'by_dataset' aggregated metrics
    """
    categories = get_categories(domain_config)
    overall_agg = init_stat_dict(categories)
    dataset_aggs = defaultdict(lambda: init_stat_dict(categories))

    for res in sample_results:
        ds = res.get("source_dataset", "unknown")
        report = res["detailed_report"]

        for cat in categories:
            if cat not in report:
                continue

            # Update overall
            overall_agg[cat]["substitutions"] += report[cat]["substitutions"]
            overall_agg[cat]["insertions"] += report[cat]["insertions"]
            overall_agg[cat]["deletions"] += report[cat]["deletions"]
            overall_agg[cat]["correct"] += report[cat]["correct"]
            overall_agg[cat]["total"] += report[cat]["total_ref"]
            overall_agg[cat]["sandhi_hits"] += report[cat]["sandhi_hits"]

            # Update per-dataset
            dataset_aggs[ds][cat]["substitutions"] += report[cat]["substitutions"]
            dataset_aggs[ds][cat]["insertions"] += report[cat]["insertions"]
            dataset_aggs[ds][cat]["deletions"] += report[cat]["deletions"]
            dataset_aggs[ds][cat]["correct"] += report[cat]["correct"]
            dataset_aggs[ds][cat]["total"] += report[cat]["total_ref"]
            dataset_aggs[ds][cat]["sandhi_hits"] += report[cat]["sandhi_hits"]

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


def print_evaluation_summary(agg_results, domain_config: Optional[DomainConfig] = None) -> None:
    """
    Print evaluation summary table.

    Args:
        agg_results: Aggregated results from compute_aggregate_metrics
        domain_config: Domain configuration for label formatting
    """
    table_data = format_dataset_table(agg_results, domain_config)

    domain_label = domain_config.label if domain_config else "DER"
    print("\n" + "=" * TABLE_WIDTH)
    print(format_table_header(domain_label))

    for row in table_data:
        is_overall = row["Dataset"] == "OVERALL"
        print(
            f"{row['Dataset']:<25} | {row['WER']:>8} | {row[domain_label]:>8}"
            f" | {row['NER']:>8} | {row['PER']:>8} | {row['Sandhi']:>6}"
        )
        if is_overall:
            print("-" * TABLE_WIDTH)

    print("=" * TABLE_WIDTH + "\n")
