import re
def tokenizer(text: str) -> list[str]:
    """
    General-purpose tokenizer that:
    - Normalizes whitespace
    - Separates punctuation as standalone tokens
    - Separates any characters attached to numbers (both directions)

    Examples:
      "abc123def" -> ["abc", "123", "def"]
      "9ാം" -> ["9", "ാം"]
      "3-ഓ" -> ["3", "-", "ഓ"]
      "₹100,000" -> ["₹", "100", ",", "000"]

    Args:
        text (str): The input string.

    Returns:
        list[str]: A list of tokens.
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string.")

    # 1) Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # 2) Separate punctuation by surrounding with spaces
    #    Include common ASCII punctuation, dashes, currency, and symbols frequently seen around numbers
    #    Note: the hyphen, en dash, em dash are handled; colon/slash are useful for times and dates
    punctuation_chars = r"[.,?!;:\-\/\"'()\[\]{}—–+*=<>|@#%^&₹$]"
    text = re.sub(f"({punctuation_chars})", r" \1 ", text)

    # 3) Ensure boundaries between digits and non-digits are spaced (both directions)
    #    \d in Python re matches Unicode digits as well.
    #    We avoid splitting spaces themselves by requiring non-space on the other side.
    text = re.sub(r"(\d)([^\d\s])", "\g<1> \g<2>", text)
    text = re.sub(r"([^\d\s])(\d)", "\g<1> \g<2>", text)

    # 4) Normalize whitespace again after insertions
    text = re.sub(r"\s+", " ", text).strip()

    tokens = [t for t in text.split(" ") if t]
    return tokens


def main():
    text = "ഈ 3-ഓ 4-ഓ വയസ്സുള്ള കുട്ടിക്ക് 9ാം തീയതി, 9:30-ന് ഫോൺ കിട്ടിയോ? abc123def. 19-ರಂದು & 19ರಂದು"
    tokens = tokenizer(text)
    print(tokens)

if __name__ == "__main__":
    main()