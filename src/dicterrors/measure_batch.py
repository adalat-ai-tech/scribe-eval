from collections import defaultdict
from typing import Optional
from .measure import text_error_rates
from .reporting import format_dataset_table
from .constants import get_categories, init_stat_dict, calculate_combined_total, format_table_header, TABLE_WIDTH
from .domain_config import DomainConfig
import json

def compute_sample_errors(input_file, output_file=None, ref_field="transcript_cleaned", hyp_field="prediction", source_dataset_field="source_dataset", domain_config: Optional[DomainConfig] = None) -> list[dict]:
    """
    Compute error metrics for all samples in a JSONL file.

    Args:
        input_file: Path to JSONL file
        output_file: Optional path to save detailed results
        ref_field: Field name for reference text
        hyp_field: Field name for hypothesis text
        source_dataset_field: Field name for dataset identifier
        domain_config: Domain configuration (None for no domain)

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

            # Pass domain_config to text_error_rates
            report = text_error_rates(data[ref_field], data[hyp_field], domain_config)
            data["detailed_report"] = report
            results.append(data)

    # Save detailed results if output file is specified
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

    return results

def compute_aggregate_metrics(sample_results, domain_config: Optional[DomainConfig] = None) -> dict[str, dict[str, dict[str, dict[str, float | int]]]]:
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
            overall_agg[cat]["total"] += report[cat]["total_ref"]
            overall_agg[cat]["sandhi_hits"] += report[cat]["sandhi_hits"]

            # Update per-dataset
            dataset_aggs[ds][cat]["substitutions"] += report[cat]["substitutions"]
            dataset_aggs[ds][cat]["insertions"] += report[cat]["insertions"]
            dataset_aggs[ds][cat]["deletions"] += report[cat]["deletions"]
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
                "correct": a["total"] - errs,
                "sandhi_hits": a["sandhi_hits"],
                "total": a["total"],
                "combined_total": combined_total  # Store for reference
            }
        return metrics

    return {
        "overall": calculate_rates(overall_agg),
        "by_dataset": {ds: calculate_rates(stats) for ds, stats in dataset_aggs.items()}
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
        is_overall = row['Dataset'] == 'OVERALL'
        print(f"{row['Dataset']:<25} | {row['WER']:>8} | {row[domain_label]:>8} | {row['NER']:>8} | {row['PER']:>8} | {row['Sandhi']:>6}")
        if is_overall:
            print("-" * TABLE_WIDTH)

    print("=" * TABLE_WIDTH + "\n")