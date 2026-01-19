from .measure import text_error_rates
import json
from typing import List, Dict, Any
from collections import defaultdict


def compute_sample_errors(
    input_file: str, 
    output_file: str = None, 
    ref_field: str = "transcript_cleaned", 
    hyp_field: str = "prediction", 
    source_dataset_field: str = "source_dataset", 
    audio_path_field: str = "file_path"
) -> List[Dict[str, Any]]:
    """
    Evaluate predictions and save results to a JSON file.
    
    Args:
        input_file: Path to input JSONL file with predictions
        output_file: Path to output JSON file for evaluation results
        ref_field: Field name for reference text in input file. default: transcript_cleaned
        hyp_field: Field name for hypothesis/prediction text in input file. default: prediction
        source_dataset_field: Field name for source dataset in input file. default: source_dataset
        audio_path_field: Field name for audio file path in input file. default: file_path
    
    Returns:
        List of evaluation results as a list of dictionaries
    """
    results = []

    print(f"Loading data from {input_file}")

    with open(input_file, "r") as f:
        lines = f.readlines()

        for line in lines:
            data = json.loads(line)
            file_path = data[audio_path_field]
            ref_text = data[ref_field]
            if source_dataset_field in data:
                source_dataset = data[source_dataset_field]
            else:
                source_dataset = None
            hyp_text = data[hyp_field]
            
            # Calculate error rates
            wer, per, ner, report = text_error_rates(ref_text, hyp_text)
            
            # Store results
            result = {
                "file_path": file_path,
                "ref_text": ref_text,
                "hyp_text": hyp_text,
                "source_dataset": source_dataset,
                "WER": wer,
                "PER": per,
                "NER": ner,
                "detailed_report": report
            }
            
            results.append(result)
    
    # Write results to JSON file
    if output_file:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Results saved to {output_file}")
    
    print("Evaluation complete.")
    return results



def _init_stats():
    """Helper to initialize zeroed stats for a category."""
    return {
        "substitutions": 0, "insertions": 0, "deletions": 0, 
        "correct": 0, "total_reference": 0,
        "sandhi_splits": 0, "sandhi_merges": 0
    }

def _init_accumulator():
    """Helper to initialize accumulators for all token types."""
    return {
        "word": _init_stats(),
        "punctuation": _init_stats(),
        "numeral": _init_stats()
    }

def _update_stats(accumulator: Dict, sample_report: Dict):
    """
    In-place update of the accumulator with values from a single sample report.
    """
    for category in ["word", "punctuation", "numeral"]:
        acc_cat = accumulator[category]
        src_cat = sample_report[category]
        
        acc_cat["substitutions"] += src_cat.get("substitutions", 0)
        acc_cat["insertions"]    += src_cat.get("insertions", 0)
        acc_cat["deletions"]     += src_cat.get("deletions", 0)
        acc_cat["correct"]       += src_cat.get("correct", 0)
        acc_cat["total_reference"] += src_cat.get("total_reference", 0)
        
        # Add Sandhi stats if they exist
        acc_cat["sandhi_splits"] += src_cat.get("sandhi_splits", 0)
        acc_cat["sandhi_merges"] += src_cat.get("sandhi_merges", 0)

def _calculate_final_metrics(accumulator: Dict) -> Dict:
    """
    Converts raw counts in an accumulator to WER/PER/NER percentages.
    """
    final_metrics = {}
    
    # Map internal category names to output metric names
    metric_map = {"word": "WER", "punctuation": "PER", "numeral": "NER"}
    
    for category, metric_name in metric_map.items():
        stats = accumulator[category]
        
        # Calculate Error Rate: (S + I + D) / max(1, N)
        errors = stats["substitutions"] + stats["insertions"] + stats["deletions"]
        total = stats["total_reference"]
        
        rate = errors / max(1, total)
        
        # Copy counts and add the calculated rate
        final_metrics[category] = stats.copy()
        final_metrics[category]["error_rate"] = rate
        final_metrics[category]["metric_name"] = metric_name # e.g. WER
        
    return final_metrics

def compute_aggregate_metrics(sample_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates error rates over the entire dataset and per-source-dataset.
    
    Args:
        sample_results: List of dicts returned by compute_sample_errors
        
    Returns:
        Dict containing 'overall' and 'by_dataset' metrics.
    """
    
    # 1. Initialize Accumulators
    overall_acc = _init_accumulator()
    dataset_accs = defaultdict(_init_accumulator)
    
    # 2. Iterate and Accumulate (The "Micro-Average" Logic)
    for result in sample_results:
        report = result["detailed_report"]
        source = result.get("source_dataset", "unknown")
        
        # Update Global
        _update_stats(overall_acc, report)
        
        # Update Specific Dataset
        _update_stats(dataset_accs[source], report)
        
    # 3. Calculate Final Rates
    output = {
        "overall": _calculate_final_metrics(overall_acc),
        "by_dataset": {}
    }
    
    for source, acc in dataset_accs.items():
        output["by_dataset"][source] = _calculate_final_metrics(acc)
        
    return output

def print_evaluation_summary(aggregated_results: Dict[str, Any]):
    """
    Pretty prints the aggregated results for console viewing.
    """
    def _print_row(name, metrics):
        wer = metrics['word']['error_rate']
        per = metrics['punctuation']['error_rate']
        ner = metrics['numeral']['error_rate']
        splits = metrics['word']['sandhi_splits']
        merges = metrics['word']['sandhi_merges']

        if name:
            print(f"{name:<20} | {wer:8.2%} | {per:8.2%} | {ner:8.2%} | {splits+merges:<4}")

    print("\n" + "="*65)
    print(f"{'DATASET':<20} | {'WER':<8} | {'PER':<8} | {'NER':<8} | {'SANDHI'}")
    print("-" * 65)
    
    # Print Overall
    _print_row("OVERALL", aggregated_results["overall"])
    print("-" * 65)
    
    # Print per dataset
    for source, metrics in aggregated_results["by_dataset"].items():
        _print_row(source, metrics)
    print("="*65 + "\n")

