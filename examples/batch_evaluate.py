import os
import sys
from dicterrors import (
    compute_sample_errors, 
    compute_aggregate_metrics, 
    print_evaluation_summary
)

def main():
    input_file = "./dictation-eval/predictions.jsonl"
    output_dir = "./dictation-eval"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Run analysis
    results = compute_sample_errors(
        input_file,
        output_file=f"{output_dir}/evaluation-detailed.jsonl"
    )
    
    # 2. Aggregate with dataset splits
    metrics = compute_aggregate_metrics(results)
    
    # 3. Output to console
    print_evaluation_summary(metrics)
    
    # 4. Save to file for the paper appendix
    with open(f"{output_dir}/summary_report.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        print_evaluation_summary(metrics)
        sys.stdout = sys.__stdout__ # Reset

if __name__ == "__main__":
    main()