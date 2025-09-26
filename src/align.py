import Levenshtein as levenshtein
from tokenize import malayalam_tokenizer

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

def get_match_score(w1, w2):
    """Calculate dynamic match score based on Levenshtein distance."""
    return 3 + (levenshtein_distance(w1, w2)/(len(w1)+len(w2)))

def get_gap_penalty(token):
    """Calculate dynamic gap penalty based on token type."""
    if token == '**':  # Handle the case when we're checking a gap
        return 0
    if is_punctuation(token):
        return -1
    else:  # Assuming it's a word with alphabet unicode
        return -1-levenshtein_distance(token, '')/2

def get_mismatch_penalty(w1, w2):
    """Calculate dynamic mismatch penalty based on token types."""
    if is_punctuation(w1) and (is_word(w2) or is_number(w2)) or (is_word(w1) or is_number(w1) ) and is_punctuation(w2):
        return -6
    elif (is_word(w1) and is_number(w2)) or (is_number(w1) and is_word(w2)):
        return -5
    elif is_number(w1) and is_number(w2):
        return -2
    elif is_punctuation(w1) and is_punctuation(w2):
        return -1
    else:  # Both are words
        return  -1-levenshtein_distance(w1, w2)
def align_arrays(arr1, arr2, max_distance=0):
    """
    Align two arrays using dynamic programming with dynamic scoring based on token types.

    Parameters:
    - arr1, arr2: arrays to align
    - max_distance: maximum Levenshtein distance to consider as a match

    Returns:
    - aligned_arr1: first array with gaps ('-') inserted
    - aligned_arr2: second array with gaps ('-') inserted
    - score: alignment score
    """
    m, n = len(arr1), len(arr2)

    # Initialize DP table
    dp = [[0 for _ in range(n + 1)] for _ in range(m + 1)]

    # Initialize first row and column (gap penalties)
    for i in range(1, m + 1):
        dp[i][0] = dp[i-1][0] + get_gap_penalty(arr1[i-1])
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j-1] + get_gap_penalty(arr2[j-1])

    # Fill DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if words_match(arr1[i-1], arr2[j-1], max_distance):
                match_score = get_match_score(arr1[i-1], arr2[j-1])
                match = dp[i-1][j-1] + match_score
            else:
                mismatch_penalty = get_mismatch_penalty(arr1[i-1], arr2[j-1])
                match = dp[i-1][j-1] + mismatch_penalty

            delete = dp[i-1][j] + get_gap_penalty(arr1[i-1])
            insert = dp[i][j-1] + get_gap_penalty(arr2[j-1])

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
                match_score = get_match_score(arr1[i-1], arr2[j-1])
                expected_diagonal = diagonal_score + match_score
            else:
                mismatch_penalty = get_mismatch_penalty(arr1[i-1], arr2[j-1])
                expected_diagonal = diagonal_score + mismatch_penalty

            if current_score == expected_diagonal:
                # Match or mismatch
                aligned_arr1.append(arr1[i-1])
                aligned_arr2.append(arr2[j-1])
                i -= 1
                j -= 1
            elif i > 0 and current_score == dp[i-1][j] + get_gap_penalty(arr1[i-1]):
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

def main():
    def print_alignment(arr1, arr2, aligned1, aligned2, score):
        """Pretty print the alignment results."""
        print("Original arrays:")
        print(f"Array 1: {arr1}")
        print(f"Array 2: {arr2}")
        print(f"\nAlignment (score: {score}):")

        # Print aligned arrays with visual indicators
        print("Array 1:", " | ".join(f"{w:>10}" for w in aligned1))
        print("Match:  ", " | ".join(f"{'✓' if w1 != '-' and w2 != '-' and words_match(w1, w2) else '✗' if w1 != '-' and w2 != '-' else ' ':>10}" for w1, w2 in zip(aligned1, aligned2)))
        print("Array 2:", " | ".join(f"{w:>10}" for w in aligned2))
        print("\n")

    text1 = "10 ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ।"
    text2 = "ಹತ್ತು ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ."
    # arr1 = ['ഇന്ന്', '9', 'ാം', 'തീയതിയാണ്', ',', 'സമയം', '9', ':', '60',  'വന്നു', 'ഞാ','പോയി']
    # arr2 = ['ഇന്ന്', '9', 'ആം', 'തീയതിയാണ്', 'സമയം', ',', '9', '30', 'ഞാൻ', 'ഞാങ്ങോട്ട്', 'പോയി']

    arr1 = malayalam_tokenizer(text1)
    arr2 = malayalam_tokenizer(text2)
    aligned1, aligned2, score = align_arrays(arr1, arr2)
    print_alignment(arr1, arr2, aligned1, aligned2, score)
    
if __name__ == "__main__":
    main()