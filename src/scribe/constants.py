"""
Constants and shared definitions for the scribe package.

This module serves as the single source of truth for all package-wide constants
including token categories, formatting parameters, and utility functions.
"""

# Base token category constants (always present)
CAT_LEXICAL = "LEXICAL"
CAT_PUNCT = "PUNCT"
CAT_NUMERAL = "NUMERAL"

# Base categories - domain categories are added dynamically
CATEGORIES = [CAT_LEXICAL, CAT_PUNCT, CAT_NUMERAL]


def get_categories(domain_config=None):
    """
    Get category list including domain category if configured.

    Args:
        domain_config: DomainConfig instance or None

    Returns:
        List of category names

    Examples:
        >>> from domain_config import MEDICAL_DOMAIN
        >>> cats = get_categories(MEDICAL_DOMAIN)
        >>> # ['LEXICAL', 'PUNCT', 'NUMERAL', 'MEDICAL']

        >>> cats = get_categories(None)
        >>> # ['LEXICAL', 'PUNCT', 'NUMERAL']
    """
    if domain_config is None:
        return CATEGORIES.copy()
    return CATEGORIES + [domain_config.category]


# Table formatting constants
TABLE_WIDTH = 85
COLUMN_WIDTHS = {"dataset": 25, "metric": 8, "sandhi": 6}


# Utility Functions


def calculate_combined_total(stats_dict: dict) -> int:
    """
    Calculate total tokens across all categories.

    Args:
        stats_dict: Dictionary mapping category names to stat dicts with 'total' field

    Returns:
        Sum of 'total' field across all categories

    Example:
        >>> stats = {"LEXICAL": {"total": 100}, "LEGAL": {"total": 5}}
        >>> calculate_combined_total(stats)
        105
    """
    return sum(stats_dict[cat]["total"] for cat in stats_dict)


def init_stat_dict(categories=None) -> dict:
    """
    Initialize empty statistics dictionary for categories.

    Uses consistent full field names throughout:
    - substitutions, insertions, deletions (not sub, ins, del)
    - correct (not cor)
    - sandhi_hits (not sandhi)

    Args:
        categories: List of category names (defaults to CATEGORIES)

    Returns:
        Dict mapping category names to stat dicts with zeroed counts

    Example:
        >>> stats = init_stat_dict()
        >>> "substitutions" in stats["LEXICAL"] and stats["LEXICAL"]["substitutions"] == 0
        True

        >>> from domain_config import MEDICAL_DOMAIN
        >>> stats = init_stat_dict(get_categories(MEDICAL_DOMAIN))
        >>> "MEDICAL" in stats
        True
    """
    if categories is None:
        categories = CATEGORIES

    return {
        cat: {
            "substitutions": 0,
            "insertions": 0,
            "deletions": 0,
            "correct": 0,
            "total": 0,
            "sandhi_hits": 0,
        }
        for cat in categories
    }


def format_table_header(domain_labels=None) -> str:
    """
    Generate formatted table header for evaluation results.

    Args:
        domain_labels: Labels for domain error-rate columns, one per
            domain category present in the data (empty/None for none)

    Returns:
        Multi-line string with header row and separator line

    Example:
        >>> print(format_table_header(["LER"]))
        DATASET                   |      WER |      LER |      NER |      PER | SANDHI
        -------------------------------------------------------------------------------------

        >>> print(format_table_header())
        DATASET                   |      WER |      NER |      PER | SANDHI
        --------------------------------------------------------------------------
    """
    dw = COLUMN_WIDTHS["dataset"]
    mw = COLUMN_WIDTHS["metric"]
    sw = COLUMN_WIDTHS["sandhi"]

    columns = ["WER"] + list(domain_labels or []) + ["NER", "PER"]
    header = f"{'DATASET':<{dw}} | " + " | ".join(f"{c:>{mw}}" for c in columns)
    header += f" | {'SANDHI':>{sw}}"
    separator = "-" * len(header)
    return f"{header}\n{separator}"
