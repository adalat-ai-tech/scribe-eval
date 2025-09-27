import re
def malayalam_tokenizer(text: str) -> list[str]:
    """
    Tokenizes Malayalam text, separating words, numbers, punctuation,
    and handling specific cases like digits followed by suffixes (e.g., "9ാം").

    Args:
        text (str): The input Malayalam string.

    Returns:
        list[str]: A list of tokens.
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string.")

    # 1. Normalize whitespace: replace multiple spaces with single, trim leading/trailing
    text = re.sub(r'\s+', ' ', text).strip()

    # 2. Separate punctuation: Add spaces around common punctuation marks.
    #    This ensures punctuation always becomes a distinct token.
    #    Using a regex that captures the punctuation and replaces it with ' <PUNC> '
    punctuation_pattern = r'([.,?!;:"\'()\[\]{}—–])' # Includes common Malayalam punctuation, em-dash, en-dash
    text = re.sub(punctuation_pattern, r' \1 ', text)

    # 3. Handle specific number suffixes (like 'ാം', 'ആം') when attached to digits.
    #    This regex looks for a sequence of digits followed immediately by 'ാം' or 'ആം'.
    #    It inserts a space between them, ensuring they are tokenized separately.
    number_suffix_pattern = r'(\d+)(ാം|ആം|ൽ|ലെ|ന്|ഓ)'
    text = re.sub(number_suffix_pattern, r'\1 \2', text)
    
    # 3.1 Handle hyphenated numbers like '3-ഓ' to tokenize as [3, -, ഓ]
    hyphenated_pattern = r'(\d+)(-)(ാം|ആം|ൽ|ലെ|ന്|ഓ)'
    text = re.sub(hyphenated_pattern, r'\1 \2 \3', text)

    # 4. Tokenize by splitting on any whitespace.
    tokens = text.split()

    # 5. Filter out any empty strings that might result from multiple spaces or edge cases.
    tokens = [token for token in tokens if token]

    return tokens

def main():
    text = "ഈ 3-ഓ 4-ഓ വയസ്സുള്ള കുട്ടിക്ക് ഈ മൊബൈൽ ഫോൺ എവിടുന്ന് കിട്ടി?"
    tokens = malayalam_tokenizer(text)
    print(tokens)

if __name__ == "__main__":
    main()