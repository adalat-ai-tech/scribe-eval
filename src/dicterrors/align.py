import Levenshtein as levenshtein
from .tokenize import tokenizer

# --- DEFAULT CONFIGURATION ---
DEFAULT_WEIGHTS = {
    'gap_punct_num': -1,
    'gap_word_base': -1,
    'gap_word_factor': 0.5, # Previously hardcoded as /2
    'mismatch_punct_cross': -6,
    'mismatch_word_num': -5,
    'mismatch_num_num': -2,
    'mismatch_punct_punct': -1,
    'mismatch_word_base': -1,
    'match_base': 3
}

def levenshtein_distance(s1, s2):
    """Calculate the Levenshtein distance between two strings."""
    return levenshtein.distance(s1, s2)

def is_punctuation(token):
    """Check if a token is a punctuation mark."""
    return len(token) == 1 and not token.isalnum()

def is_word(token):
    """Check if a token is a word (contains alphabetic characters)."""
    return any(c.isalpha() for c in token)

def is_number(token):
    """Check if a token is a number."""
    return token.isdigit()

def words_match(w1, w2, max_distance=0):
    """Check if two words are within a specified Levenshtein distance."""
    return levenshtein_distance(w1, w2) <= max_distance

def get_match_score(w1, w2, weights=DEFAULT_WEIGHTS):
    """Calculate dynamic match score based on Levenshtein distance."""
    return weights['match_base'] + (levenshtein_distance(w1, w2)/(len(w1)+len(w2)))

def get_gap_penalty(token, weights=DEFAULT_WEIGHTS):
    """Calculate dynamic gap penalty based on token type."""
    if token == '**':  # Handle the case when we're checking a gap
        return 0
    if is_punctuation(token) or is_number(token):
        return weights['gap_punct_num']
    else:  # Assuming it's a word with alphabet unicode
        return weights['gap_word_base'] - (levenshtein_distance(token, '') * weights['gap_word_factor'])

def get_mismatch_penalty(w1, w2, weights=DEFAULT_WEIGHTS):
    """Calculate dynamic mismatch penalty based on token types."""
    if (is_punctuation(w1) and (is_word(w2) or is_number(w2))) or \
       ((is_word(w1) or is_number(w1)) and is_punctuation(w2)):
        return weights['mismatch_punct_cross']
    elif (is_word(w1) and is_number(w2)) or (is_number(w1) and is_word(w2)):
        return weights['mismatch_word_num']
    elif is_number(w1) and is_number(w2):
        return weights['mismatch_num_num']
    elif is_punctuation(w1) and is_punctuation(w2):
        return weights['mismatch_punct_punct']
    else:  # Both are words
        return weights['mismatch_word_base'] - levenshtein_distance(w1, w2)

def align_arrays(arr1, arr2, max_distance=0, weights=None):
    """
    Align two arrays using dynamic programming with dynamic scoring based on token types.
    """
    # Use defaults if no weights provided
    if weights is None:
        weights = DEFAULT_WEIGHTS

    m, n = len(arr1), len(arr2)

    # Initialize DP table
    dp = [[0 for _ in range(n + 1)] for _ in range(m + 1)]

    # Initialize first row and column (gap penalties)
    for i in range(1, m + 1):
        dp[i][0] = dp[i-1][0] + get_gap_penalty(arr1[i-1], weights)
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j-1] + get_gap_penalty(arr2[j-1], weights)

    # Fill DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if words_match(arr1[i-1], arr2[j-1], max_distance):
                match_score = get_match_score(arr1[i-1], arr2[j-1], weights)
                match = dp[i-1][j-1] + match_score
            else:
                mismatch_penalty = get_mismatch_penalty(arr1[i-1], arr2[j-1], weights)
                match = dp[i-1][j-1] + mismatch_penalty

            delete = dp[i-1][j] + get_gap_penalty(arr1[i-1], weights)
            insert = dp[i][j-1] + get_gap_penalty(arr2[j-1], weights)

            dp[i][j] = max(match, delete, insert)

    # Traceback to find alignment
    aligned_arr1 = []
    aligned_arr2 = []
    i, j = m, n

    while i > 0 or j > 0:
        if i > 0 and j > 0:
            current_score = dp[i][j]
            diagonal_score = dp[i-1][j-1]

            # Calculate expected diagonal score
            if words_match(arr1[i-1], arr2[j-1], max_distance):
                match_score = get_match_score(arr1[i-1], arr2[j-1], weights)
                expected_diagonal = diagonal_score + match_score
            else:
                mismatch_penalty = get_mismatch_penalty(arr1[i-1], arr2[j-1], weights)
                expected_diagonal = diagonal_score + mismatch_penalty

            # Use small tolerance for float comparison
            if abs(current_score - expected_diagonal) < 1e-9:
                # Match or mismatch
                aligned_arr1.append(arr1[i-1])
                aligned_arr2.append(arr2[j-1])
                i -= 1
                j -= 1
            elif i > 0 and abs(current_score - (dp[i-1][j] + get_gap_penalty(arr1[i-1], weights))) < 1e-9:
                # Deletion from arr1
                aligned_arr1.append(arr1[i-1])
                aligned_arr2.append('**')
                i -= 1
            else:
                # Insertion to arr1
                aligned_arr1.append('**')
                aligned_arr2.append(arr2[j-1])
                j -= 1
        elif i > 0:
            # Remaining elements in arr1
            aligned_arr1.append(arr1[i-1])
            aligned_arr2.append('**')
            i -= 1
        else:
            # Remaining elements in arr2
            aligned_arr1.append('**')
            aligned_arr2.append(arr2[j-1])
            j -= 1

    # Reverse the alignments (we built them backwards)
    aligned_arr1.reverse()
    aligned_arr2.reverse()

    return aligned_arr1, aligned_arr2, dp[m][n]

def align_text(text1, text2, weights=None):
    arr1 = tokenizer(text1)
    arr2 = tokenizer(text2)
    aligned1, aligned2, score = align_arrays(arr1, arr2, weights=weights)
    return aligned1, aligned2, score