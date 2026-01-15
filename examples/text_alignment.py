#!/usr/bin/env python3
"""
Example script demonstrating text alignment using dicterrors package.

This example shows how to:
1. Import the necessary functions from the dicterrors package
2. Align two input texts 
3. Print the alignment results

Usage:
    python text_alignment.py "First text to align" "Second text to align"
    
If no arguments are provided, the script uses default example texts.
"""

import sys
from dicterrors import align_text

def print_alignment(text1, text2, aligned1, aligned2, score):
    """Pretty print the alignment results."""
    print("Original texts:")
    print(f"Text 1: {text1}")
    print(f"Text 2: {text2}")
    print(f"\nAlignment (score: {score}):")

    # Print aligned arrays with visual indicators
    from dicterrors.align import words_match  # Import for match checking
    
    print("Text 1:", " | ".join(f"{w:>10}" for w in aligned1))
    print("Match: ", " | ".join(f"{'✓' if w1 != '**' and w2 != '**' and words_match(w1, w2) else '✗' if w1 != '**' and w2 != '**' else ' ':>10}" 
                              for w1, w2 in zip(aligned1, aligned2)))
    print("Text 2:", " | ".join(f"{w:>10}" for w in aligned2))
    print("\n")

def main():
    # Use command line arguments if provided, otherwise use default examples
    if len(sys.argv) >= 3:
        text1 = sys.argv[1]
        text2 = sys.argv[2]
    else:
        # Default examples in multiple languages
        print("No text arguments provided. Using default examples...")
        
        # Malayalam example
        text1 = "പണം അക്കൗണ്ടിൽ എത്തിയപ്പോൾ ആദ്യ, ഗഡുവായി 180000 രൂപയായി നൽകിയത്."
        text2 = "പണം അക്കൗണ്ടിൽ എത്തിയപ്പോൾ, ആദ്യ ഘടുവായി 180000 രൂപയാണ് നൽകിയത്:"
        
        print("\n=== MALAYALAM EXAMPLE 1 ===")
        aligned1, aligned2, score = align_text(text1, text2)
        print_alignment(text1, text2, aligned1, aligned2, score)

        # Malayalam example
        text1 = "നിർദ്ദിഷ്ട ഭേദഗതി ഇരുസഭകളും 2011-ൽ തന്നെ പാസാക്കി."
        text2 = "നിർദ്ദിഷ്ട ട ഭേദഗതി ഇരുസഭകളും 201-ൽ തന്നെ പാസാക്കി."
        
        print("\n=== MALAYALAM EXAMPLE 2 ===")
        aligned1, aligned2, score = align_text(text1, text2)
        print_alignment(text1, text2, aligned1, aligned2, score)

        # Kannada example
        text1 = "10 ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ।"
        text2 = "ಹತ್ತು ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ."
        
        print("\n=== KANNADA EXAMPLE ===")
        aligned1, aligned2, score = align_text(text1, text2)
        print_alignment(text1, text2, aligned1, aligned2, score)
        
        # English example
        text1 = "The brown quick fox jumps over the lazy dogs."
        text2 = "The bron fox jumps over a lazy, dog"
        
        print("\n=== ENGLISH EXAMPLE ===")
        aligned1, aligned2, score = align_text(text1, text2)
        print_alignment(text1, text2, aligned1, aligned2, score)
        
                # English example
        text1 = "The quick brown fox jumps over the lazy dog."
        text2 = "The bron fox jumps over a lazy dog"
        
        print("\n=== ENGLISH EXAMPLE ===")
        aligned1, aligned2, score = align_text(text1, text2)
        print_alignment(text1, text2, aligned1, aligned2, score)
        
        return
    
    # Align the texts
    aligned1, aligned2, score = align_text(text1, text2)
    
    # Print the alignment
    print_alignment(text1, text2, aligned1, aligned2, score)

if __name__ == "__main__":
    main()

