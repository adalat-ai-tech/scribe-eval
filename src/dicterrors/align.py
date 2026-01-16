import Levenshtein as levenshtein
from .tokenize import tokenizer

# --- DEFAULT CONFIGURATION ---
DEFAULT_WEIGHTS = {
    'gap_punct_num': -1.0,
    'gap_word_base': -1.0,
    'gap_word_factor': 0.5,
    'mismatch_punct_cross': -6.0,
    'mismatch_word_num': -5.0,
    'mismatch_num_num': -2.0,
    'mismatch_punct_punct': -1.0,
    'mismatch_word_base': -1.0,
    'match_base': 3.0,
    # NEW WEIGHTS FOR AGGLUTINATION
    'split_merge_penalty': -0.5, # Small penalty for splitting/merging valid words
    'sandhi_threshold': 2        # Max char diff allowed when combining words (e.g. Mazha+Kalathu vs Mazhakkalathu)
}

def levenshtein_distance(s1, s2):
    return levenshtein.distance(s1, s2)

def is_punctuation(token):
    return len(token) == 1 and not token.isalnum()

def is_word(token):
    return any(c.isalpha() for c in token)

def is_number(token):
    return token.isdigit()

def words_match(w1, w2, max_distance=0):
    return levenshtein_distance(w1, w2) <= max_distance

def get_match_score(w1, w2, weights=DEFAULT_WEIGHTS):
    return weights['match_base'] + (levenshtein_distance(w1, w2)/(len(w1)+len(w2)))

def get_gap_penalty(token, weights=DEFAULT_WEIGHTS):
    if token == '**': return 0
    if is_punctuation(token) or is_number(token):
        return weights['gap_punct_num']
    else:
        return weights['gap_word_base'] - (levenshtein_distance(token, '') * weights['gap_word_factor'])

def get_mismatch_penalty(w1, w2, weights=DEFAULT_WEIGHTS):
    if (is_punctuation(w1) and (is_word(w2) or is_number(w2))) or \
       ((is_word(w1) or is_number(w1)) and is_punctuation(w2)):
        return weights['mismatch_punct_cross']
    elif (is_word(w1) and is_number(w2)) or (is_number(w1) and is_word(w2)):
        return weights['mismatch_word_num']
    elif is_number(w1) and is_number(w2):
        return weights['mismatch_num_num']
    elif is_punctuation(w1) and is_punctuation(w2):
        return weights['mismatch_punct_punct']
    else:
        return weights['mismatch_word_base'] - levenshtein_distance(w1, w2)

# --- NEW HELPER FOR SANDHI ---
def check_sandhi_match(combined_text, single_text, weights):
    """
    Checks if 'combined_text' (e.g., "മഴ" + "കാലത്ത്") is roughly equivalent 
    to 'single_text' (e.g., "മഴക്കാലത്ത്").
    """
    # Simple concatenation often misses Sandhi chars (like double k).
    # We check Levenshtein distance.
    dist = levenshtein_distance(combined_text, single_text)
    
    # If distance is small enough, we consider it a valid split/merge
    if dist <= weights.get('sandhi_threshold'):
        # Score: Base match reward - small penalty for the split - character error penalty
        return weights['match_base'] + weights['split_merge_penalty'] - (dist / len(single_text))
    return -float('inf')

def align_arrays(arr1, arr2, max_distance=0, weights=None):
    if weights is None: weights = DEFAULT_WEIGHTS

    m, n = len(arr1), len(arr2)
    dp = [[-float('inf') for _ in range(n + 1)] for _ in range(m + 1)]
    dp[0][0] = 0

    # Initialize gaps
    for i in range(1, m + 1):
        dp[i][0] = dp[i-1][0] + get_gap_penalty(arr1[i-1], weights)
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j-1] + get_gap_penalty(arr2[j-1], weights)

    # Fill DP
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            
            # 1. Standard Match/Mismatch
            if words_match(arr1[i-1], arr2[j-1], max_distance):
                score = get_match_score(arr1[i-1], arr2[j-1], weights)
            else:
                score = get_mismatch_penalty(arr1[i-1], arr2[j-1], weights)
            match_val = dp[i-1][j-1] + score

            # 2. Standard Indel
            del_val = dp[i-1][j] + get_gap_penalty(arr1[i-1], weights)
            ins_val = dp[i][j-1] + get_gap_penalty(arr2[j-1], weights)

            # 3. NEW: SPLIT CHECK (1 Ref matches 2 Hyp) -> Ref[i] vs Hyp[j-1]+Hyp[j]
            split_val = -float('inf')
            if j >= 2:
                # Only apply split check if all tokens involved are words (not numbers or punctuations)
                if is_word(arr1[i-1]) and is_word(arr2[j-2]) and is_word(arr2[j-1]):
                    # Combine current and previous hypothesis tokens
                    combined_hyp = arr2[j-2] + arr2[j-1] 
                    score_split = check_sandhi_match(combined_hyp, arr1[i-1], weights)
                    split_val = dp[i-1][j-2] + score_split

            # 4. NEW: MERGE CHECK (2 Ref match 1 Hyp) -> Ref[i-1]+Ref[i] vs Hyp[j]
            merge_val = -float('inf')
            if i >= 2:
                # Only apply merge check if all tokens involved are words (not numbers or punctuations)
                if is_word(arr1[i-2]) and is_word(arr1[i-1]) and is_word(arr2[j-1]):
                    combined_ref = arr1[i-2] + arr1[i-1]
                    score_merge = check_sandhi_match(combined_ref, arr2[j-1], weights)
                    merge_val = dp[i-2][j-1] + score_merge

            dp[i][j] = max(match_val, del_val, ins_val, split_val, merge_val)

    # Traceback
    aligned_arr1 = []
    aligned_arr2 = []
    i, j = m, n

    while i > 0 or j > 0:
        current = dp[i][j]
        
        # Helper to avoid repetitive float comparison
        def is_close(val): return abs(current - val) < 1e-9

        # Check SPLIT (1 Ref -> 2 Hyp), only for word tokens
        if j >= 2 and i > 0:
            # Only check split for word tokens (not numbers or punctuations)
            if is_word(arr1[i-1]) and is_word(arr2[j-2]) and is_word(arr2[j-1]):
                combined_hyp = arr2[j-2] + arr2[j-1]
                score_split = check_sandhi_match(combined_hyp, arr1[i-1], weights)
                if is_close(dp[i-1][j-2] + score_split):
                    # We align 1 Ref with 2 Hyps
                    aligned_arr1.append(arr1[i-1])
                    aligned_arr2.append(f"SPLIT:{arr2[j-2]} {arr2[j-1]}") 
                    i -= 1; j -= 2
                    continue

        # Check MERGE (2 Ref -> 1 Hyp), only for word tokens
        if i >= 2 and j > 0:
            # Only check merge for word tokens (not numbers or punctuations)
            if is_word(arr1[i-2]) and is_word(arr1[i-1]) and is_word(arr2[j-1]):
                combined_ref = arr1[i-2] + arr1[i-1]
                score_merge = check_sandhi_match(combined_ref, arr2[j-1], weights)
                if is_close(dp[i-2][j-1] + score_merge):
                    aligned_arr1.append(f"MERGE:{arr1[i-2]} {arr1[i-1]}")
                    aligned_arr2.append(arr2[j-1])
                    i -= 2; j -= 1
                    continue

        # Standard checks
        if i > 0 and j > 0:
            if words_match(arr1[i-1], arr2[j-1], max_distance):
                step = get_match_score(arr1[i-1], arr2[j-1], weights)
            else:
                step = get_mismatch_penalty(arr1[i-1], arr2[j-1], weights)
            
            if is_close(dp[i-1][j-1] + step):
                aligned_arr1.append(arr1[i-1])
                aligned_arr2.append(arr2[j-1])
                i -= 1; j -= 1
                continue

        if i > 0 and is_close(dp[i-1][j] + get_gap_penalty(arr1[i-1], weights)):
            aligned_arr1.append(arr1[i-1])
            aligned_arr2.append('**')
            i -= 1
        elif j > 0:
            aligned_arr1.append('**')
            aligned_arr2.append(arr2[j-1])
            j -= 1
        else:
            # Should not happen if logic is correct
            break

    return aligned_arr1[::-1], aligned_arr2[::-1], dp[m][n]

def align_text(text1, text2, weights=None):
    arr1 = tokenizer(text1)
    arr2 = tokenizer(text2)
    aligned1, aligned2, score = align_arrays(arr1, arr2, weights=weights)
    return aligned1, aligned2, score