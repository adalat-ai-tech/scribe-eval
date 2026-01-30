from collections import defaultdict
from .measure import text_error_rates
from .reporting import format_dataset_table
import json

def compute_sample_errors(input_file, ref_field="transcript_cleaned", hyp_field="prediction", source_dataset_field="source_dataset") -> list[dict]:
    results = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            # Ensure we have a source_dataset field
            if source_dataset_field not in data:
                data[source_dataset_field] = "unknown"
                
            report = text_error_rates(data[ref_field], data[hyp_field])
            data["detailed_report"] = report
            results.append(data)
    return results

def _init_stat_dict() -> dict[str, dict[str, int]]:
    # Helper to create the structure for categories
    categories = ["WORD", "PUNCT", "NUMERAL", "LEGAL"]
    return {cat: {"sub": 0, "ins": 0, "del": 0, "total": 0, "sandhi": 0} for cat in categories}

def compute_aggregate_metrics(sample_results) -> dict[str, dict[str, dict[str, dict[str, float | int]]]]:
    overall_agg = _init_stat_dict()
    dataset_aggs = defaultdict(_init_stat_dict)

    for res in sample_results:
        ds = res.get("source_dataset", "unknown")
        report = res["detailed_report"]
        
        for cat in ["WORD", "PUNCT", "NUMERAL", "LEGAL"]:
            # Update overall
            overall_agg[cat]["sub"] += report[cat]["substitutions"]
            overall_agg[cat]["ins"] += report[cat]["insertions"]
            overall_agg[cat]["del"] += report[cat]["deletions"]
            overall_agg[cat]["total"] += report[cat]["total_ref"]
            overall_agg[cat]["sandhi"] += report[cat]["sandhi_hits"]
            
            # Update per-dataset
            dataset_aggs[ds][cat]["sub"] += report[cat]["substitutions"]
            dataset_aggs[ds][cat]["ins"] += report[cat]["insertions"]
            dataset_aggs[ds][cat]["del"] += report[cat]["deletions"]
            dataset_aggs[ds][cat]["total"] += report[cat]["total_ref"]
            dataset_aggs[ds][cat]["sandhi"] += report[cat]["sandhi_hits"]

    def calculate_rates(agg):
        # Calculate combined denominator across ALL categories
        combined_total = (agg["WORD"]["total"] + agg["LEGAL"]["total"] +
                          agg["NUMERAL"]["total"] + agg["PUNCT"]["total"])

        metrics = {}
        for cat in agg:
            a = agg[cat]
            errs = a["sub"] + a["ins"] + a["del"]
            metrics[cat] = {
                "error_rate": errs / max(1, combined_total),  # Combined denominator
                "sandhi_hits": a["sandhi"],
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

    print("\n" + "="*85)
    print(f"{'DATASET':<25} | {'WER':>8} | {'LER':>8} | {'NER':>8} | {'PER':>8} | {'SANDHI'}")
    print("-" * 85)

    for row in table_data:
        is_overall = row['Dataset'] == 'OVERALL'
        print(f"{row['Dataset']:<25} | {row['WER']:>8} | {row['LER']:>8} | {row['NER']:>8} | {row['PER']:>8} | {row['Sandhi']:>6}")
        if is_overall:
            print("-" * 85)

    print("="*85 + "\n")