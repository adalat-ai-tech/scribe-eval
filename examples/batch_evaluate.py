from dicterrors import  compute_sample_errors, compute_aggregate_metrics, print_evaluation_summary
import json
from collections import defaultdict
from tabulate import tabulate
import sys
import argparse

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Load your sample results (mocking loading from the function you wrote)
    results = compute_sample_errors("./dictation-eval/predictions.jsonl", output_file = "./dictation-eval/evaluation-detailed.jsonl", ref_field = "transcript_cleaned", hyp_field = "prediction", source_dataset_field = "source_dataset", audio_path_field = "file_path") 
    
    # # Mock data for demonstration
    # results = [
    #     {"source_dataset": "None", "detailed_report": {"word": {"substitutions": 1, "insertions": 0, "deletions": 0, "total_reference": 10}, "punctuation": {"substitutions":0, "insertions":0, "deletions":0, "total_reference":2}, "numeral": {"substitutions":0, "insertions":0, "deletions":0, "total_reference":0}}},
    #     {"source_dataset": "court_A", "detailed_report": {"word": {"substitutions": 2, "insertions": 1, "deletions": 0, "total_reference": 20}, "punctuation": {"substitutions":1, "insertions":0, "deletions":0, "total_reference":5}, "numeral": {"substitutions":0, "insertions":0, "deletions":0, "total_reference":0}}},
    #     {"source_dataset": "court_B", "detailed_report": {"word": {"substitutions": 0, "insertions": 0, "deletions": 0, "total_reference": 5}, "punctuation": {"substitutions":0, "insertions":0, "deletions":0, "total_reference":1}, "numeral": {"substitutions":0, "insertions":0, "deletions":0, "total_reference":0}}}
    # ]

    # 2. Compute Aggregates
    agg_stats = compute_aggregate_metrics(results)
    
    # 3. Print
    with open("./dictation-eval/evaluation-summary.txt", "w") as f:
        import sys
        old_stdout = sys.stdout
        sys.stdout = f
        print_evaluation_summary(agg_stats)
        sys.stdout = old_stdout
