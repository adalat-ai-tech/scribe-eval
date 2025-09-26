import json
import os
from src.measure import text_error_rates

def evaluate_predictions(input_file, output_file):
    """Evaluate predictions and save results to a JSON file."""
    results = []

    with open(input_file, "r") as f:
        lines = f.readlines()

        for line in lines:
            data = json.loads(line)
            file_path = data["file_path"]
            ref_text = data["transcript_cleaned"]
            hyp_text = data["prediction"]
            
            # Calculate error rates
            wer, per, ner, report = text_error_rates(ref_text, hyp_text)
            
            # Store results
            result = {
                "file_path": file_path,
                "ref_text": ref_text,
                "hyp_text": hyp_text,
                "WER": wer*100,
                "PER": per*100,
                "NER": ner*100,
                "detailed_report": report
            }
            
            results.append(result)
    
    # Write results to JSON file
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Evaluation complete. Results saved to {output_file}")
    return results

def main():
    # Default paths
    input_file = "predictions.jsonl"  # Updated to correct path
    output_file = "evaluation_results.json"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Cannot find {input_file}")
        return
    
    results = evaluate_predictions(input_file, output_file)
    
    # Print summary statistics
    total_files = len(results)
    avg_wer = sum(r["WER"] for r in results) / total_files if total_files > 0 else 0
    avg_per = sum(r["PER"] for r in results) / total_files if total_files > 0 else 0
    avg_ner = sum(r["NER"] for r in results) / total_files if total_files > 0 else 0
    
    print(f"\nSummary Statistics ({total_files} files):")
    print(f"Average WER: {avg_wer:.4f}")
    print(f"Average PER: {avg_per:.4f}")
    print(f"Average NER: {avg_ner:.4f}")

if __name__ == "__main__":
    main()
