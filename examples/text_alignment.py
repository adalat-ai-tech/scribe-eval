#!/usr/bin/env python3
"""
Example script demonstrating text alignment using the scribe package.

This example shows how to:
1. Import the necessary functions from the scribe package
2. Tokenize and align two input texts
3. Print the alignment results

Usage:
    python text_alignment.py "First text to align" "Second text to align"

If no arguments are provided, the script uses default example texts.
"""

import sys

from scribe import DomainConfig, align_arrays, domain_aware_tokenizer


def print_alignment(text1, text2, aligned1, aligned2, score):
    """Pretty print the alignment results."""
    print("Original texts:")
    print(f"Text 1: {text1}")
    print(f"Text 2: {text2}")
    print(f"\nAlignment (score: {score}):")

    # Extract text from (text, tag) tuples
    text1_tokens = [t[0] for t in aligned1]
    text2_tokens = [t[0] for t in aligned2]

    print("Text 1:", " | ".join(f"{w:>15}" for w in text1_tokens))
    print("Text 2:", " | ".join(f"{w:>15}" for w in text2_tokens))
    print("\n")


def main():
    # Use command line arguments if provided, otherwise use default examples
    if len(sys.argv) >= 3:
        text1 = sys.argv[1]
        text2 = sys.argv[2]
    else:
        # Default examples in multiple languages
        print("No text arguments provided. Using default examples...")

        # Using bundled legal domain. For custom domains, see custom_domain_file.py
        domain = DomainConfig.legal()

        # Malayalam example — demonstrates Sandhi-aware alignment:
        # text1 has "ആദ്യഗഡുവായി" (sandhi-merged), text2 has "ആദ്യ ഗഡുവായി" (split).
        text1 = "ആദ്യഗഡുവായി 180000 രൂപയായി നൽകിയത്."
        text2 = "ആദ്യ ഗഡുവായി 180000 രൂപയായി നൽകിയത്:"

        print("\n=== MALAYALAM EXAMPLE ===")
        t1, g1 = domain_aware_tokenizer(text1, domain)
        t2, g2 = domain_aware_tokenizer(text2, domain)
        aligned1, aligned2, score = align_arrays(t1, g1, t2, g2)
        print_alignment(text1, text2, aligned1, aligned2, score)
        return

    # Align the texts
    domain = DomainConfig.legal()
    t1, g1 = domain_aware_tokenizer(text1, domain)
    t2, g2 = domain_aware_tokenizer(text2, domain)
    aligned1, aligned2, score = align_arrays(t1, g1, t2, g2)

    # Print the alignment
    print_alignment(text1, text2, aligned1, aligned2, score)


if __name__ == "__main__":
    main()
