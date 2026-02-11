"""
Constants and shared definitions for the DictErrors package.

This module serves as the single source of truth for all package-wide constants
including token categories, formatting parameters, and utility functions.
"""

# Token category constants
CAT_WORD = "WORD"
CAT_PUNCT = "PUNCT"
CAT_NUMERAL = "NUMERAL"
CAT_LEGAL = "LEGAL"

# Category list (maintain order: WORD, PUNCT, NUMERAL, LEGAL)
CATEGORIES = [CAT_WORD, CAT_PUNCT, CAT_NUMERAL, CAT_LEGAL]

# Table formatting constants
TABLE_WIDTH = 85
COLUMN_WIDTHS = {
    'dataset': 25,
    'metric': 8,
    'sandhi': 6
}


# Utility Functions

def calculate_combined_total(stats_dict: dict) -> int:
    """
    Calculate total tokens across all categories.

    Args:
        stats_dict: Dictionary mapping category names to stat dicts with 'total' field

    Returns:
        Sum of 'total' field across all categories

    Example:
        >>> stats = {"WORD": {"total": 100}, "LEGAL": {"total": 5}}
        >>> calculate_combined_total(stats)
        105
    """
    return sum(stats_dict[cat]["total"] for cat in CATEGORIES)


def init_stat_dict() -> dict:
    """
    Initialize empty statistics dictionary for all categories.

    Uses consistent full field names throughout:
    - substitutions, insertions, deletions (not sub, ins, del)
    - correct (not cor)
    - sandhi_hits (not sandhi)

    Returns:
        Dict mapping category names to stat dicts with zeroed counts

    Example:
        >>> stats = init_stat_dict()
        >>> stats["WORD"]
        {'substitutions': 0, 'insertions': 0, 'deletions': 0, 'correct': 0, 'total': 0, 'sandhi_hits': 0}
    """
    return {
        cat: {
            "substitutions": 0,
            "insertions": 0,
            "deletions": 0,
            "correct": 0,
            "total": 0,
            "sandhi_hits": 0
        }
        for cat in CATEGORIES
    }


def format_table_header() -> str:
    """
    Generate formatted table header for evaluation results.

    Returns:
        Multi-line string with header row and separator line

    Example:
        >>> print(format_table_header())
        DATASET                   |      WER |      LER |      NER |      PER | SANDHI
        -------------------------------------------------------------------------------------
    """
    dw = COLUMN_WIDTHS['dataset']
    mw = COLUMN_WIDTHS['metric']
    sw = COLUMN_WIDTHS['sandhi']

    header = f"{'DATASET':<{dw}} | {'WER':>{mw}} | {'LER':>{mw}} | {'NER':>{mw}} | {'PER':>{mw}} | {'SANDHI':>{sw}}"
    separator = "-" * TABLE_WIDTH
    return f"{header}\n{separator}"
