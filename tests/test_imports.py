"""Public API surface tests.

Every symbol re-exported from `scribe.__init__` is covered here. If the
public API changes, this test catches it; if a release accidentally drops
or renames a public symbol, downstream users will break, so we make that
intent explicit and version-controlled.
"""

import re

import scribe


def test_version_is_populated():
    assert hasattr(scribe, "__version__")
    assert isinstance(scribe.__version__, str)
    # Either a real PEP 440 version (e.g. "0.1.0") or the editable-install
    # fallback ("0.0.0+unknown").
    assert re.match(r"^\d+\.\d+\.\d+", scribe.__version__)


# Symbols grouped by module of origin. Update when the public API changes.
PUBLIC_API = {
    # align
    "DEFAULT_WEIGHTS": dict,
    "align_arrays": "callable",
    # analysis
    "compute_category_contributions": "callable",
    "compute_error_summary": "callable",
    "compute_error_type_distribution": "callable",
    "compute_frequent_deletions": "callable",
    "compute_frequent_insertions": "callable",
    "compute_frequent_substitutions": "callable",
    "compute_total_error_rate": "callable",
    # constants
    "CAT_NUMERAL": str,
    "CAT_PUNCT": str,
    "CAT_WORD": str,
    "CATEGORIES": (list, tuple),
    "get_categories": "callable",
    # domain_config
    "DomainConfig": type,
    # measure
    "text_error_details": "callable",
    "text_error_rates": "callable",
    "token_error_details": "callable",
    "token_error_rates": "callable",
    # measure_batch
    "aggregate_error_details": "callable",
    "compute_aggregate_metrics": "callable",
    "compute_sample_errors": "callable",
    "print_evaluation_summary": "callable",
    # normalize
    "normalize_currency": "callable",
    "normalize_date": "callable",
    "normalize_numeral": "callable",
    "normalize_token": "callable",
    # reporting
    "extract_error_rates": "callable",
    "format_alignment_dict": "callable",
    "format_alignment_table": "callable",
    "format_contribution_table": "callable",
    "format_dataset_table": "callable",
    "format_error_counts_table": "callable",
    "format_frequent_errors_table": "callable",
    "format_metrics_dict": "callable",
    "write_summary_to_file": "callable",
    # tokenize
    "domain_aware_tokenizer": "callable",
}


def test_every_public_symbol_is_exported():
    """Every name in PUBLIC_API must be importable from `scribe`."""
    missing = [name for name in PUBLIC_API if not hasattr(scribe, name)]
    assert not missing, f"Missing from scribe.__init__: {missing}"


def test_every_public_symbol_has_expected_kind():
    """Each exported symbol is the expected kind (callable / type / instance)."""
    mismatches = []
    for name, expected in PUBLIC_API.items():
        obj = getattr(scribe, name)
        if expected == "callable":
            ok = callable(obj)
        elif isinstance(expected, type):
            ok = isinstance(obj, expected)
        elif isinstance(expected, tuple):
            ok = isinstance(obj, expected)
        else:
            ok = False
        if not ok:
            mismatches.append((name, type(obj).__name__, expected))
    assert not mismatches, f"Kind mismatches: {mismatches}"


def test_categories_constants_are_consistent():
    """CAT_* constants appear in CATEGORIES, and get_categories() returns them."""
    assert scribe.CAT_WORD in scribe.CATEGORIES
    assert scribe.CAT_NUMERAL in scribe.CATEGORIES
    assert scribe.CAT_PUNCT in scribe.CATEGORIES

    cats = scribe.get_categories()
    assert scribe.CAT_WORD in cats
    assert scribe.CAT_NUMERAL in cats
    assert scribe.CAT_PUNCT in cats
