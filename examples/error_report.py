#!/usr/bin/env python3
"""
Single-sample error report — the analog of `batch_evaluate.py --analysis`
for a single (reference, hypothesis) pair.

Shows the same "Token Breakdown by Category" table that the batch CLI
produces, with overall correct % and total error rate (TER) on top.

Usage:
    python error_report.py "First text" "Second text"

If no arguments are provided, uses a default Malayalam example.
"""

import sys

from tabulate import tabulate

# Reuse the alignment-printing helper from the alignment example.
from text_alignment import print_alignment

from scribe import (
    DomainConfig,
    align_arrays,
    compute_error_summary,
    domain_aware_tokenizer,
    text_error_rates,
)
from scribe.reporting import format_contribution_table


def generate_error_report(text1, text2, domain=None):
    """Print alignment + per-category breakdown for one (ref, hyp) pair."""
    domain = domain or DomainConfig.legal()

    # Run the full pipeline (tokenize → align → measure) in one call.
    report = text_error_rates(text1, text2, domain)
    summary = compute_error_summary(report, error_details=[])

    print("=" * 60)
    print("TEXT COMPARISON REPORT")
    print("=" * 60)

    # Token-by-token alignment (helper imported from text_alignment.py).
    t1, g1 = domain_aware_tokenizer(text1, domain)
    t2, g2 = domain_aware_tokenizer(text2, domain)
    aligned_ref, aligned_hyp, score = align_arrays(t1, g1, t2, g2)
    print_alignment(text1, text2, aligned_ref, aligned_hyp, score)

    # Headline metrics — same shape as `batch_evaluate.py --analysis`.
    print(
        f"Overall: {summary['total_correct_pct']:.1f}% correct "
        f"| {summary['total_error_rate']:.2%} TER\n"
    )

    print("--- Token Breakdown by Category ---")
    rows = format_contribution_table(summary["contributions"], domain)
    print(tabulate(rows, headers="keys", tablefmt="simple"))


def main():
    if len(sys.argv) >= 3:
        text1, text2 = sys.argv[1], sys.argv[2]
    else:
        print("No text arguments provided. Using default example...\n")
        text1 = "പണം അക്കൗണ്ടിൽ എത്തിയപ്പോൾ ആദ്യ, ഗഡുവായി 180000 രൂപയായി നൽകിയത്."
        text2 = "പണം അക്കൗണ്ടിൽ എത്തിയപ്പോൾ, ആദ്യ ഘടുവായി 180000 രൂപയാണ് നൽകിയത്:"

    generate_error_report(text1, text2)


if __name__ == "__main__":
    main()
