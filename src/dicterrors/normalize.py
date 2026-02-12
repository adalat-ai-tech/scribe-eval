"""Token normalization for semantic matching.

This module provides normalization functions to convert tokens to canonical forms
for comparison purposes while preserving original formatting for display.
"""
import re
from .constants import CAT_NUMERAL


def normalize_date(text: str) -> str:
    """Normalize date formats to canonical dd-mm-yyyy.

    Converts various date separator formats (dd.mm.yyyy, dd/mm/yyyy, dd-mm-yyyy)
    to a canonical form for comparison.

    Args:
        text: Token text that may contain a date

    Returns:
        Normalized date string if pattern matches, otherwise original text

    Examples:
        >>> normalize_date("22.05.2023")
        '22-05-2023'
        >>> normalize_date("22/05/2023")
        '22-05-2023'
        >>> normalize_date("22-05-2023")
        '22-05-2023'
    """
    # Match dates with any separator (. / -)
    pattern = r'(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})'
    match = re.match(pattern, text)
    if match:
        day, month, year = match.groups()
        return f"{day}-{month}-{year}"
    return text


def normalize_currency(text: str) -> str:
    """Normalize currency by removing comma separators.

    Converts numbers with comma separators (10,500 or 1,00,000) to
    continuous digit strings (10500 and 100000) for comparison.

    Args:
        text: Token text that may contain currency or large numbers

    Returns:
        Text with commas removed if text contains digits, otherwise original

    Examples:
        >>> normalize_currency("10,500")
        '10500'
        >>> normalize_currency("1,00,000")
        '100000'
        >>> normalize_currency("123")
        '123'
    """
    if ',' in text and any(c.isdigit() for c in text):
        return text.replace(',', '')
    return text


def normalize_numeral(text: str) -> str:
    """Apply all numeral normalization rules.

    Tries date normalization first, then currency normalization.
    Time formats (HH:MM) are already in canonical form and unchanged.

    Args:
        text: Token text with NUMERAL category

    Returns:
        Normalized text after applying applicable rules

    Examples:
        >>> normalize_numeral("22.05.2023")
        '22-05-2023'
        >>> normalize_numeral("10,500")
        '10500'
        >>> normalize_numeral("10:30")
        '10:30'
    """
    # Try date normalization first
    normalized = normalize_date(text)
    if normalized != text:
        return normalized

    # Try currency/number normalization
    normalized = normalize_currency(text)
    if normalized != text:
        return normalized

    # Time formats (HH:MM) already canonical
    return text


def normalize_token(text: str, category: str) -> str:
    """Apply category-specific normalization.

    Dispatches to appropriate normalization function based on token category.
    Only NUMERAL category has normalization rules currently; other categories
    return original text unchanged.

    Args:
        text: Original token text
        category: Token category (WORD, NUMERAL, PUNCT, LEGAL, etc.)

    Returns:
        Normalized token text

    Examples:
        >>> normalize_token("22.05.2023", "NUMERAL")
        '22-05-2023'
        >>> normalize_token("hello", "WORD")
        'hello'
        >>> normalize_token(".", "PUNCT")
        '.'
    """
    if category == CAT_NUMERAL:
        return normalize_numeral(text)

    # No normalization for WORD, PUNCT, LEGAL, etc.
    return text
