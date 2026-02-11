from collections import defaultdict
from .measure import text_error_rates
from .reporting import format_dataset_table
from .constants import CATEGORIES, init_stat_dict, calculate_combined_total, format_table_header, TABLE_WIDTH
import json

def compute_sample_errors(input_file, output_file=None, ref_field="transcript_cleaned", hyp_field="prediction", source_dataset_field="source_dataset") -> list[dict]:
    results = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            # Ensure we have a source_dataset field
            if source_dataset_field not in data or data[source_dataset_field] is None:
                data[source_dataset_field] = "unknown"

            report = text_error_rates(data[ref_field], data[hyp_field])
            data["detailed_report"] = report
            results.append(data)

    # Save detailed results if output file is specified
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

    return results

def compute_aggregate_metrics(sample_results) -> dict[str, dict[str, dict[str, dict[str, float | int]]]]:
    overall_agg = init_stat_dict()
    dataset_aggs = defaultdict(init_stat_dict)

    for res in sample_results:
        ds = res.get("source_dataset", "unknown")
        report = res["detailed_report"]

        for cat in CATEGORIES:
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

def print_evaluation_summary(agg_results) -> None:
    table_data = format_dataset_table(agg_results)

    print("\n" + "=" * TABLE_WIDTH)
    print(format_table_header())

    for row in table_data:
        is_overall = row['Dataset'] == 'OVERALL'
        print(f"{row['Dataset']:<25} | {row['WER']:>8} | {row['LER']:>8} | {row['NER']:>8} | {row['PER']:>8} | {row['Sandhi']:>6}")
        if is_overall:
            print("-" * TABLE_WIDTH)

    print("=" * TABLE_WIDTH + "\n")