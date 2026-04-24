#!/usr/bin/env python3
"""
Example script demonstrating detailed error reporting using the scribe package.

This example shows how to:
1. Import the necessary functions from the scribe package
2. Tokenize and align two input texts
3. Generate a comprehensive error report with various error metrics
4. Visualize the alignment with error details

Usage:
    python error_report.py "First text to compare" "Second text to compare"

If no arguments are provided, the script uses default example texts.
"""

import sys

from tabulate import tabulate

from scribe import (
    CAT_NUMERAL,
    CAT_PUNCT,
    CAT_WORD,
    DomainConfig,
    align_arrays,
    domain_aware_tokenizer,
    token_error_rates,
)
from scribe.reporting import format_alignment_table, format_error_counts_table, format_metrics_dict


def generate_error_report(text1, text2):
    """Generate a detailed error report for two texts."""

    # Using bundled legal domain. For custom domains, see custom_domain_file.py
    domain_config = DomainConfig.legal()

    # Header
    print("=" * 50)
    print("TEXT COMPARISON REPORT")
    print("=" * 50)
    print(f"Reference text: {text1}")
    print(f"Hypothesis text: {text2}")

    # Step 1: Tokenize
    t1, g1 = domain_aware_tokenizer(text1, domain_config)
    t2, g2 = domain_aware_tokenizer(text2, domain_config)

    # Step 2: Align
    aligned_ref, aligned_hyp, align_score = align_arrays(t1, g1, t2, g2)

    # Step 3: Calculate error rates
    report = token_error_rates(aligned_ref, aligned_hyp, domain_config)

    # Step 4: Format using shared functions
    metrics = format_metrics_dict(report, domain_config)
    error_counts = format_error_counts_table(report, domain_config)
    alignment_vis = format_alignment_table(aligned_ref, aligned_hyp)

    # Display metrics table
    print("\n" + "=" * 50)
    print("ERROR METRICS:")
    print("=" * 50)
    metrics_table = [
        ["Word Error Rate (WER)", metrics["WER"]],
        [
            f"{domain_config.name.title()} Error Rate ({domain_config.label})",
            metrics[domain_config.label],
        ],
        ["Numeral Error Rate (NER)", metrics["NER"]],
        ["Punctuation Error Rate (PER)", metrics["PER"]],
        ["Word Correct", report[CAT_WORD]["correct"]],
        [f"{domain_config.name.title()} Correct", report[domain_config.category]["correct"]],
        ["Numeral Correct", report[CAT_NUMERAL]["correct"]],
        ["Punctuation Correct", report[CAT_PUNCT]["correct"]],
        ["Combined Total Tokens", report[CAT_WORD]["combined_total"]],
        ["Sandhi Corrections", metrics["Sandhi"]],
    ]
    print(tabulate(metrics_table, headers=["Metric", "Value"], tablefmt="grid"))

    # Display error counts
    print("\n" + "=" * 50)
    print("ERROR COUNTS BY CATEGORY:")
    print("=" * 50)
    print(tabulate(error_counts, headers="keys", tablefmt="grid"))

    # Display alignment visualization
    print("\n" + "=" * 50)
    print("ALIGNMENT VISUALIZATION:")
    print("=" * 50)
    print(tabulate(alignment_vis, headers="keys", tablefmt="grid"))

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("=" * 50)
    print(f"Alignment Score: {align_score}")
    print(f"Overall WER: {metrics['WER']}")
    print(f"Overall {domain_config.label}: {metrics[domain_config.label]}")
    print(f"Overall NER: {metrics['NER']}")
    print(f"Overall PER: {metrics['PER']}")
    print(f"Sandhi corrections: {metrics['Sandhi']}")

    return report


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
