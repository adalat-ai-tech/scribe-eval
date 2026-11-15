"""Token normalization for semantic matching.

This module provides normalization functions to convert tokens to canonical forms
for comparison purposes while preserving original formatting for display.
"""

import re
import unicodedata

from .constants import CAT_NUMERAL, CAT_PUNCT


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
    pattern = r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})"
    match = re.match(pattern, text)
    if match:
        day, month, year = match.groups()
        return f"{day}-{month}-{year}"
    return text


def normalize_subsection(text: str) -> str:
    """Normalize statute references by removing a space before a bracket.

    Converts spaced sub-clause references (34 (2), 5 (1)(a)) to the glued
    form (34(2), 5(1)(a)) for comparison. Badly spaced forms such as
    34  ( 2 ) are left as they are.

    Args:
        text: Token text that may contain a statute reference

    Returns:
        Reference with spaces removed if pattern matches, otherwise original text

    Examples:
        >>> normalize_subsection("34 (2)")
        '34(2)'
        >>> normalize_subsection("34  ( 2 )")
        '34  ( 2 )'
        >>> normalize_subsection("5 (1) (a)")
        '5(1)(a)'
        >>> normalize_subsection("34(2)")
        '34(2)'
    """
    pattern = r"\d+[A-Za-z]?(?: ?\(\w{1,5}\))+"
    if re.fullmatch(pattern, text):
        return text.replace(" ", "")
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
    if "," in text and any(c.isdigit() for c in text):
        return text.replace(",", "")
    return text


def normalize_indic_numerals(text: str) -> str:
    """Normalize Indic and other Unicode decimal numerals to Arabic numerals.

    Converts Unicode decimal digits (Kannada, Malayalam, Devanagari, Bengali,
    Telugu, Tamil, etc.) to standard Arabic numerals (0-9). Non-numeral and
    ASCII characters are preserved as is.

    Args:
        text: Token text that may contain Indic numerals

    Returns:
        Text with Indic numerals converted to Arabic numerals (0-9)

    Examples:
        >>> normalize_indic_numerals("೧೮೩")
        '183'
        >>> normalize_indic_numerals("൧൫.൦൫.൨൦൨൩")
        '15.05.2023'
        >>> normalize_indic_numerals("१५,५००")
        '15,500'
    """
    if text.isascii():
        return text
    return "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)


def normalize_kannada_numerals(text: str) -> str:
    """Normalize Kannada numerals to Arabic numerals.

    Converts Kannada digits (೦-೯) to their Arabic numeral equivalents (0-9).
    Handles full strings containing Kannada numerals.
    Kept for backward compatibility; delegates to normalize_indic_numerals.

    Args:
        text: Token text that may contain Kannada numerals

    Returns:
        Text with Kannada numerals replaced by Arabic numerals

    Examples:
        >>> normalize_kannada_numerals("೧೮೩")
        '183'
        >>> normalize_kannada_numerals("೧೫.೦೫.೨೦೨೩")
        '15.05.2023'
        >>> normalize_kannada_numerals("೧,೫೦೦")
        '1,500'
    """
    return normalize_indic_numerals(text)


def normalize_numeral(text: str) -> str:
    """Apply all numeral normalization rules.

    Normalizes Indic numerals to Arabic numerals first, then tries date
    normalization, statute reference normalization, and currency normalization.
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
        >>> normalize_numeral("34 (2)")
        '34(2)'
        >>> normalize_numeral("೧೫.೦೫.೨೦೨೩")
        '15-05-2023'
        >>> normalize_numeral("൧൫.൦൫.൨൦൨൩")
        '15-05-2023'
    """
    # First, normalize Indic numerals to Arabic numerals
    text = normalize_indic_numerals(text)

    # Try date normalization first
    normalized = normalize_date(text)
    if normalized != text:
        return normalized

    # Try statute reference normalization
    normalized = normalize_subsection(text)
    if normalized != text:
        return normalized

    # Try currency/number normalization
    normalized = normalize_currency(text)
    if normalized != text:
        return normalized

    # Time formats (HH:MM) already canonical
    return text


def normalize_word(text: str) -> str:
    """Normalize word by removing hyphen within word"""
    return text.replace("-", "")


def normalize_token(text: str, category: str) -> str:
    """Apply category-specific normalization.

    Dispatches to appropriate normalization function based on token category.
    Only NUMERAL category has normalization rules currently; other categories
    return original text unchanged.

    Args:
        text: Original token text
        category: Token category (LEXICAL, NUMERAL, PUNCT, LEGAL, etc.)

    Returns:
        Normalized token text

    Examples:
        >>> normalize_token("22.05.2023", "NUMERAL")
        '22-05-2023'
        >>> normalize_token("hello", "LEXICAL")
        'hello'
        >>> normalize_token(".", "PUNCT")
        '.'
    """
    if category == CAT_NUMERAL:
        return normalize_numeral(text)

    if category != CAT_PUNCT:
        return normalize_word(text)

    # No normalization for PUNCT, etc.
    return text
