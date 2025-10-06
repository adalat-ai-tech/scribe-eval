#!/usr/bin/env python3
"""
Example script demonstrating detailed error reporting using dicterrors package.

This example shows how to:
1. Import the necessary functions from the dicterrors package
2. Align two input texts
3. Generate a comprehensive error report with various error metrics
4. Visualize the alignment with error details

Usage:
    python error_report.py "First text to compare" "Second text to compare"
    
If no arguments are provided, the script uses default example texts.
"""

import sys
from tabulate import tabulate
from dicterrors import align_text, text_error_rates
from dicterrors.align import words_match, is_punctuation, is_number, is_word

def generate_error_report(text1, text2):
    """Generate a detailed error report for two texts."""
    # Step 1: Align the texts
    aligned_ref, aligned_hyp, align_score = align_text(text1, text2)
    
    # Step 2: Calculate error rates
    wer, per, ner, error_report = text_error_rates(text1, text2)
    
    # Step 3: Generate a detailed report
    print("=" * 50)
    print(f"TEXT COMPARISON REPORT")
    print("=" * 50)
    print(f"Reference text: {text1}")
    print(f"Hypothesis text: {text2}")
    print("\n" + "=" * 50)
    print("ERROR METRICS:")
    print("=" * 50)
    
    # Create a table of error metrics
    metrics_table = [
        ["Word Error Rate (WER)", f"{wer*100:.2f}%"],
        ["Punctuation Error Rate (PER)", f"{per*100:.2f}%"],
        ["Number Error Rate (NER)", f"{ner*100:.2f}%"],
        ["Word Correct Rate", f"{error_report['word']['correct']/max(1, error_report['word']['total_reference'])*100:.2f}%"],
        ["Punctuation Correct Rate", f"{error_report['punctuation']['correct']/max(1, error_report['punctuation']['total_reference'])*100:.2f}%"],
        ["Number Correct Rate", f"{error_report['numeral']['correct']/max(1, error_report['numeral']['total_reference'])*100:.2f}%"]
    ]
    
    print(tabulate(metrics_table, headers=["Metric", "Value"], tablefmt="grid"))
    
    # Error counts
    print("\n" + "=" * 50)
    print("ERROR COUNTS:")
    print("=" * 50)
    
    counts_table = [
        ["Word Substitutions", error_report["word"]["substitutions"]],
        ["Word Insertions", error_report["word"]["insertions"]],
        ["Word Deletions", error_report["word"]["deletions"]],
        ["Word Correct", error_report["word"]["correct"]],
        ["Punctuation Substitutions", error_report["punctuation"]["substitutions"]],
        ["Punctuation Insertions", error_report["punctuation"]["insertions"]],
        ["Punctuation Deletions", error_report["punctuation"]["deletions"]],
        ["Punctuation Correct", error_report["punctuation"]["correct"]],
        ["Number Substitutions", error_report["numeral"]["substitutions"]],
        ["Number Insertions", error_report["numeral"]["insertions"]],
        ["Number Deletions", error_report["numeral"]["deletions"]],
        ["Number Correct", error_report["numeral"]["correct"]]
    ]
    
    print(tabulate(counts_table, headers=["Error Type", "Count"], tablefmt="grid"))
    
    # Alignment visualization
    print("\n" + "=" * 50)
    print("ALIGNMENT VISUALIZATION:")
    print("=" * 50)
    
    # Create a list to store alignment details
    alignment_rows = []
    
    for i, (ref, hyp) in enumerate(zip(aligned_ref, aligned_hyp)):
        # Determine token type
        if ref == "**":
            error_type = "Insertion"
            token_type = "Word" if is_word(hyp) else "Number" if is_number(hyp) else "Punctuation"
        elif hyp == "**":
            error_type = "Deletion"
            token_type = "Word" if is_word(ref) else "Number" if is_number(ref) else "Punctuation"
        elif words_match(ref, hyp):
            error_type = "Correct"
            token_type = "Word" if is_word(ref) else "Number" if is_number(ref) else "Punctuation"
        else:
            error_type = "Substitution"
            token_type = "Word" if (is_word(ref) and is_word(hyp)) else "Number" if (is_number(ref) and is_number(hyp)) else "Mixed"
        
        alignment_rows.append([i+1, ref, hyp, error_type, token_type])
    
    print(tabulate(alignment_rows, headers=["Position", "Reference", "Hypothesis", "Error Type", "Token Type"], tablefmt="grid"))
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("=" * 50)
    print(f"Alignment Score: {align_score}")
    print(f"Overall WER: {wer*100:.2f}%")
    print(f"Overall PER: {per*100:.2f}%")
    print(f"Overall NER: {ner*100:.2f}%")
    
    return wer, per, ner, error_report

def main():
    # Use command line arguments if provided, otherwise use default examples
    if len(sys.argv) >= 3:
        text1 = sys.argv[1]
        text2 = sys.argv[2]
    else:
        # Default examples in multiple languages
        print("No text arguments provided. Using default example...")
        
        # Malayalam example
        text1 = "പണം അക്കൗണ്ടിൽ എത്തിയപ്പോൾ ആദ്യ, ഗഡുവായി 180000 രൂപയായി നൽകിയത്."
        text2 = "പണം അക്കൗണ്ടിൽ എത്തിയപ്പോൾ, ആദ്യ ഘടുവായി 180000 രൂപയാണ് നൽകിയത്:"
    
    # Generate the error report
    generate_error_report(text1, text2)

if __name__ == "__main__":
    main()
