import Levenshtein as levenshtein
from .constants import CAT_WORD, CAT_PUNCT, CAT_NUMERAL

def is_sandhi_eligible(tag) -> bool:
    """Check if a tag is eligible for Sandhi split/merge operations.

    Sandhi operations apply to all categories except PUNCT and NUMERAL.
    This includes WORD and all domain-specific categories (LEGAL, MEDICAL, etc.).
    """
    return tag not in (CAT_PUNCT, CAT_NUMERAL)

# --- SCORING CONFIGURATION ---
DEFAULT_WEIGHTS = {
    'gap_penalty': -2.5,              # Gap penalty for words, legal terms, numerals
    'gap_penalty_punct': -1.2,        # Gap penalty for punctuation (lighter penalty)
    'match_reward': 3.0,
    'mismatch_default_penalty': -1.5,
    'mismatch_cross_punct_penalty': -3.0, # High penalty for aligning e.g. a Law term with a Punctuation
    'split_merge_penalty': -0.5,     # Small penalty for Sandhi logic
    'sandhi_char_tolerence': 2            # Max character diff for Sandhi
}

def levenshtein_distance(s1, s2) -> int:
    return levenshtein.distance(s1, s2)

def get_gap_penalty(tag, weights=DEFAULT_WEIGHTS) -> float:
    """Returns the appropriate gap penalty based on token category."""
    if tag == CAT_PUNCT:
        return weights.get('gap_penalty_punct', weights['gap_penalty'])
    return weights['gap_penalty']

def get_match_score(w1, w2, weights=DEFAULT_WEIGHTS) -> float:
    # Normalized reward: Match base + character similarity
    dist = levenshtein_distance(w1, w2)
    length = max(len(w1), len(w2), 1)
    return weights['match_reward'] + (1.0 - dist*2/length)

def get_mismatch_penalty(w1, t1, w2, t2, weights=DEFAULT_WEIGHTS) -> float:
    # If categories are different, apply a heavy penalty
    if t1 != t2:
        if t1 == CAT_PUNCT or t2 == CAT_PUNCT:
            return weights['mismatch_cross_punct_penalty']
        return weights['mismatch_cross_punct_penalty']

    # For mismatch between other categories, penalty based on string distance
    dist = levenshtein_distance(w1, w2)
    return weights['mismatch_default_penalty'] - (dist * 0.2)

def check_sandhi_match(combined_words, single_text, weights) -> float:
    """Checks if two words (split) equal one word (merge) with Sandhi rules."""
    if len(combined_words) != 2: return -float('inf')

    w1, w2 = combined_words[0], combined_words[1]
    if len(w1) < 2 or len(w2) < 2: return -float('inf')

    # Boundary analysis
    s1, s2 = w1[:-1], w1[-1:]
    s3, s4 = w2[:1], w2[1:]

    if not single_text.startswith(s1) or not single_text.endswith(s4):
        return -float('inf')

    boundary_region = single_text[len(s1) : len(single_text)-len(s4)]
    split_boundary = s2 + s3

    dist = levenshtein_distance(split_boundary, boundary_region)
    if dist <= weights.get('sandhi_char_tolerence', 2):
        score = weights['match_reward'] + weights['split_merge_penalty']
        return score - (dist / len(single_text))

    return -float('inf')

def align_arrays(arr1, tags1, arr2, tags2, weights=None, use_sandhi: bool = True) -> tuple[list[tuple[str, str]], list[tuple[str, str]], float]:
    if weights is None: weights = DEFAULT_WEIGHTS

    m, n = len(arr1), len(arr2)
    dp = [[-float('inf') for _ in range(n + 1)] for _ in range(m + 1)]
    dp[0][0] = 0

    # Initialize gaps
    for i in range(1, m + 1):
        dp[i][0] = dp[i-1][0] + get_gap_penalty(tags1[i-1], weights)
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j-1] + get_gap_penalty(tags2[j-1], weights)

    # Fill DP
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            # 1. Standard Match/Mismatch (Category Aware)
            score = 0
            if arr1[i-1] == arr2[j-1]:
                score = get_match_score(arr1[i-1], arr2[j-1], weights)
            else:
                score = get_mismatch_penalty(arr1[i-1], tags1[i-1], arr2[j-1], tags2[j-1], weights)
            match_val = dp[i-1][j-1] + score

            # 2. Standard Indel (Category-aware gap penalties)
            del_val = dp[i-1][j] + get_gap_penalty(tags1[i-1], weights)
            ins_val = dp[i][j-1] + get_gap_penalty(tags2[j-1], weights)

            # 3. Sandhi Split/Merge (for all categories except PUNCT and NUMERAL)
            split_val = merge_val = -float('inf')

            if use_sandhi:
                # Split: 1 Ref matches 2 Hyp
                if (j >= 2 and is_sandhi_eligible(tags1[i-1]) and
                    is_sandhi_eligible(tags2[j-2]) and is_sandhi_eligible(tags2[j-1])):
                    score_split = check_sandhi_match([arr2[j-2], arr2[j-1]], arr1[i-1], weights)
                    split_val = dp[i-1][j-2] + score_split

                # Merge: 2 Ref match 1 Hyp
                if (i >= 2 and is_sandhi_eligible(tags1[i-2]) and
                    is_sandhi_eligible(tags1[i-1]) and is_sandhi_eligible(tags2[j-1])):
                    score_merge = check_sandhi_match([arr1[i-2], arr1[i-1]], arr2[j-1], weights)
                    merge_val = dp[i-2][j-1] + score_merge

            dp[i][j] = max(match_val, del_val, ins_val, split_val, merge_val)

    # Traceback
    aligned_ref = []
    aligned_hyp = []
    i, j = m, n

    while i > 0 or j > 0:
        curr = dp[i][j]
        def is_close(v): return abs(curr - v) < 1e-7

        # Trace Sandhi Split
        if use_sandhi and j >= 2 and i > 0 and is_sandhi_eligible(tags1[i-1]):
            score = check_sandhi_match([arr2[j-2], arr2[j-1]], arr1[i-1], weights)
            if is_close(dp[i-1][j-2] + score):
                aligned_ref.append((arr1[i-1], tags1[i-1]))
                aligned_hyp.append((f"SPLIT:{arr2[j-2]} {arr2[j-1]}", tags1[i-1]))
                i -= 1; j -= 2; continue

        # Trace Sandhi Merge
        if use_sandhi and i >= 2 and j > 0 and is_sandhi_eligible(tags2[j-1]):
            score = check_sandhi_match([arr1[i-2], arr1[i-1]], arr2[j-1], weights)
            if is_close(dp[i-2][j-1] + score):
                aligned_ref.append((f"MERGE:{arr1[i-2]} {arr1[i-1]}", tags2[j-1]))
                aligned_hyp.append((arr2[j-1], tags2[j-1]))
                i -= 2; j -= 1; continue

        # Trace Standard Match/Mismatch
        if i > 0 and j > 0:
            if arr1[i-1] == arr2[j-1]: score = get_match_score(arr1[i-1], arr2[j-1], weights)
            else: score = get_mismatch_penalty(arr1[i-1], tags1[i-1], arr2[j-1], tags2[j-1], weights)

            if is_close(dp[i-1][j-1] + score):
                aligned_ref.append((arr1[i-1], tags1[i-1]))
                aligned_hyp.append((arr2[j-1], tags2[j-1]))
                i -= 1; j -= 1; continue

        # Trace Gaps (Category-aware)
        if i > 0 and is_close(dp[i-1][j] + get_gap_penalty(tags1[i-1], weights)):
            aligned_ref.append((arr1[i-1], tags1[i-1]))
            aligned_hyp.append(("**", "GAP"))
            i -= 1
        else:
            aligned_ref.append(("**", "GAP"))
            aligned_hyp.append((arr2[j-1], tags2[j-1]))
            j -= 1

    return aligned_ref[::-1], aligned_hyp[::-1], dp[m][n]
