from .align import is_punctuation, is_number, is_word, align_text
from .tokenize import tokenizer

def token_error_rates(aligned_ref, aligned_hyp):
    """
    Calculate Word Error Rate (WER), Punctuation Error Rate (PER), and Numeral Error Rate (NER)
    from aligned arrays.
    
    Handles special alignment tags:
    - SPLIT:word1 word2 (Ref has 1 token, Hyp has 2) -> Counts as Correct Match (if semantically valid)
    - MERGE:word1 word2 (Ref has 2 tokens, Hyp has 1) -> Counts as Correct Match
    """

    # Initialize counters for each category
    word_sub = word_ins = word_del = word_correct = word_total = 0
    punct_sub = punct_ins = punct_del = punct_correct = punct_total = 0
    num_sub = num_ins = num_del = num_correct = num_total = 0
    
    # New counters for Sandhi/Agglutination stats (Optional, but useful for your paper)
    sandhi_splits = 0
    sandhi_merges = 0

    # Count errors by comparing aligned tokens
    for ref_token, hyp_token in zip(aligned_ref, aligned_hyp):
        
        # --- 1. HANDLE SPECIAL SANDHI TAGS ---
        is_split = hyp_token.startswith("SPLIT:")
        is_merge = ref_token.startswith("MERGE:")
        
        if is_split:
            # Scenario: Ref="mazhakkalathu", Hyp="SPLIT:mazha kalathu"
            # We treat this as a semantic match (Correct)
            sandhi_splits += 1
            word_total += 1
            word_correct += 1
            continue
            
        if is_merge:
            # Scenario: Ref="MERGE:mazha kalathu", Hyp="mazhakkalathu"
            # We treat this as a semantic match (Correct)
            # Note: Ref technically had 2 tokens, but we aligned them to 1.
            # For WER standard, we count "Total Ref Words".
            # If Ref was "mazha" "kalathu", that's 2 words.
            # But our alignment collapsed them. 
            # To be mathematically rigorous for WER:
            # We should count this as 2 Reference Words and 2 Correct Matches 
            # (effectively saying both words were successfully captured, just merged).
            
            sandhi_merges += 1
            word_total += 2 # We count the original 2 words
            word_correct += 2
            continue

        # --- 2. STANDARD LOGIC ---
        
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
    wer = (word_sub + word_ins + word_del) / max(1, word_total) 
    per = (punct_sub + punct_ins + punct_del) / max(1, punct_total) 
    ner = (num_sub + num_ins + num_del) / max(1, num_total) 

      
    report = {
        "word": {
            "substitutions": word_sub,
            "insertions": word_ins,
            "deletions": word_del,
            "correct": word_correct,
            "sandhi_splits": sandhi_splits,
            "sandhi_merges": sandhi_merges,
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
    # Align the token arrays
    aligned_ref, aligned_hyp, _ = align_text(ref_text, hyp_text)
    # Calculate error rates based on aligned tokens
    return token_error_rates(aligned_ref, aligned_hyp)