#!/usr/bin/env python3
"""
Example script demonstrating text alignment using the scribe package.

This example shows how to:
1. Import the necessary functions from the scribe package
2. Tokenize and align two input texts
3. Print the alignment results

Usage:
    python text_alignment.py "First text to align" "Second text to align"

If no arguments are provided, the script runs a small multilingual demo
covering Malayalam, Kannada, and English with a mix of error patterns
(sandhi, numeral truncation, spelled-out numerals, word reorder).
"""

import sys

from scribe import DomainConfig, align_arrays, domain_aware_tokenizer

# Each entry: (label, reference, hypothesis)
# Designed to surface a specific alignment behaviour.
DEFAULT_EXAMPLES = [
    (
        "MALAYALAM — sandhi merge / split",
        "ആദ്യഗഡുവായി 180000 രൂപയായി നൽകിയത്.",
        "ആദ്യ ഗഡുവായി 180000 രൂപയായി നൽകിയത്:",
    ),
    (
        "MALAYALAM — token insertion + numeral truncation",
        "നിർദ്ദിഷ്ട ഭേദഗതി ഇരുസഭകളും 2011-ൽ തന്നെ പാസാക്കി.",
        "നിർദ്ദിഷ്ട ട ഭേദഗതി ഇരുസഭകളും 201-ൽ തന്നെ പാസാക്കി.",
    ),
    (
        "KANNADA — numeral spelled out",
        "10 ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ।",
        "ಹತ್ತು ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ.",
    ),
    (
        "ENGLISH — word reorder + punctuation",
        "The brown quick fox jumps over the lazy dogs.",
        "The bron fox jumps over a lazy, dog",
    ),
]


def print_alignment(text1, text2, aligned1, aligned2, score):
    """Pretty print the alignment results."""
    print("Original texts:")
    print(f"Text 1: {text1}")
    print(f"Text 2: {text2}")
    print(f"\nAlignment (score: {score}):")

    text1_tokens = [t[0] for t in aligned1]
    text2_tokens = [t[0] for t in aligned2]

    print("Text 1:", " | ".join(f"{w:>15}" for w in text1_tokens))
    print("Text 2:", " | ".join(f"{w:>15}" for w in text2_tokens))
    print("\n")


def run_example(label, text1, text2, domain):
    print(f"\n=== {label} ===")
    t1, g1 = domain_aware_tokenizer(text1, domain)
    t2, g2 = domain_aware_tokenizer(text2, domain)
    aligned1, aligned2, score = align_arrays(t1, g1, t2, g2)
    print_alignment(text1, text2, aligned1, aligned2, score)


def main():
    domain = DomainConfig.legal()

    if len(sys.argv) >= 3:
        run_example("CUSTOM", sys.argv[1], sys.argv[2], domain)
        return

    print("No text arguments provided. Running multilingual demo...")
    for label, ref, hyp in DEFAULT_EXAMPLES:
        run_example(label, ref, hyp, domain)


if __name__ == "__main__":
    main()
