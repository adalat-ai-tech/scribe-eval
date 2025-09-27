from .align import is_punctuation, is_number, is_word
from .tokenize import malayalam_tokenizer

def token_error_rates(aligned_ref, aligned_hyp):
    """
    Calculate Word Error Rate (WER), Punctuation Error Rate (PER), and Numeral Error Rate (NER)
    from aligned arrays.

    Parameters:
    - aligned_ref: Reference array with gaps (-)
    - aligned_hyp: Hypothesis array with gaps (-)

    Returns:
    - wer: Word Error Rate
    - per: Punctuation Error Rate
    - ner: Numeral Error Rate
    """

    # Initialize counters for each category
    word_sub = word_ins = word_del = word_correct = word_total = 0
    punct_sub = punct_ins = punct_del = punct_correct = punct_total = 0
    num_sub = num_ins = num_del = num_correct = num_total = 0

    # Count errors by comparing aligned tokens
    for ref_token, hyp_token in zip(aligned_ref, aligned_hyp):
        # Skip if both are gaps (shouldn't happen in proper alignment)
        if ref_token == '**' and hyp_token == '**':
            continue

        # Insertion (gap in reference)
        elif ref_token == '**':
            if is_word(hyp_token):
                word_ins += 1
            elif is_punctuation(hyp_token):
                punct_ins += 1
            elif is_number(hyp_token):
                num_ins += 1

        # Deletion (gap in hypothesis)
        elif hyp_token == '**':
            if is_word(ref_token):
                word_del += 1
                word_total += 1
            elif is_punctuation(ref_token):
                punct_del += 1
                punct_total += 1
            elif is_number(ref_token):
                num_del += 1
                num_total += 1

        # Substitution or correct
        else:
            if is_word(ref_token):
                word_total += 1
                if ref_token == hyp_token:
                    word_correct += 1
                else:
                    word_sub += 1
            elif is_punctuation(ref_token):
                punct_total += 1
                if ref_token == hyp_token:
                    punct_correct += 1
                else:
                    punct_sub += 1
            elif is_number(ref_token):
                num_total += 1
                if ref_token == hyp_token:
                    num_correct += 1
                else:
                    num_sub += 1

    # Calculate error rates
    wer = (word_sub + word_ins + word_del) / max(1, word_total) if word_total > 0 else 0
    per = (punct_sub + punct_ins + punct_del) / max(1, punct_total) if punct_total > 0 else 0
    ner = (num_sub + num_ins + num_del) / max(1, num_total) if num_total > 0 else 0

      
    report = {
        "word": {
            "substitutions": word_sub,
            "insertions": word_ins,
            "deletions": word_del,
            "correct": word_correct,
            "total_reference": word_total,
            "error_rate": wer
        },
        "punctuation": {
            "substitutions": punct_sub,
            "insertions": punct_ins,
            "deletions": punct_del,
            "correct": punct_correct,
            "total_reference": punct_total,
            "error_rate": per
        },
        "numeral": {
            "substitutions": num_sub,
            "insertions": num_ins,
            "deletions": num_del,
            "correct": num_correct,
            "total_reference": num_total,
            "error_rate": ner
        }
    }
    return wer, per, ner, report

def text_error_rates(ref_text, hyp_text):
    """Calculate error rates between two text strings."""
    # Tokenize both reference and hypothesis texts
    ref_tokens = malayalam_tokenizer(ref_text)
    hyp_tokens = malayalam_tokenizer(hyp_text)
    
    # Import align_arrays here to avoid circular imports
    from .align import align_arrays
    
    # Align the token arrays
    aligned_ref, aligned_hyp, align_score = align_arrays(ref_tokens, hyp_tokens)
    
    # Calculate error rates based on aligned tokens
    return token_error_rates(aligned_ref, aligned_hyp)

def main():
    aligned_ref = ['**', '**', '2026', 'ಮಾರ್ಚ್', '19-ರಂದು', 'ಸಾಕ್ಷಿ', 'ಸಲೀಂ', 'ತಮ್ಮ', 'ಹೇಳಿಕೆಯನ್ನು', 'ನ್ಯಾಯಾಲಯದಲ್ಲಿ', 'ನೀಡಲಿದ್ದಾರೆ', '.']
    aligned_hyp = ['ಎರಡು', 'ಸಾವಿರದ', 'ಇಪ್ಪತ್ತಾರು', 'ಮಾರ್ಚ್', '19ರಂದು', 'ಸಾಕ್ಷಿ', 'ಸಲೀಂ', 'ತಮ್ಮ', 'ಹೇಳಿಕೆಯನ್ನು', 'ನ್ಯಾಯಾಲಯದಲ್ಲಿ', 'ನೀಡಲಿದ್ದಾರೆ', '.']
    wer, per, ner, report = token_error_rates(aligned_ref, aligned_hyp)

    # Print the results
    print(f"Word Error Rate (WER): {wer:.4f}")
    print(f"Punctuation Error Rate (PER): {per:.4f}")
    print(f"Numeral Error Rate (NER): {ner:.4f}")

    # Print detailed report
    print("\nDetailed Error Report:")
    for category, stats in report.items():
        print(f"\n{category.upper()} STATISTICS:")
        print(f"  Substitutions: {stats['substitutions']}")
        print(f"  Insertions: {stats['insertions']}")
        print(f"  Deletions: {stats['deletions']}")
        print(f"  Correct: {stats['correct']}")
        print(f"  Total in reference: {stats['total_reference']}")
        print(f"  Error rate: {stats['error_rate']:.4f}")

if __name__ == "__main__":
    main()
    