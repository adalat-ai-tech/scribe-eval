"""
Report formatting and presentation utilities.

This module provides shared functions for formatting error metrics
and alignment results for both CLI and web UI presentations.
"""
from typing import Dict, List, Tuple
from .tokenize import CAT_WORD, CAT_LEGAL, CAT_NUMERAL, CAT_PUNCT


def format_metrics_dict(metrics: Dict) -> Dict[str, str]:
    """
    Extract WER/LER/NER/PER/Sandhi from aggregate metrics.

    Args:
        metrics: Dictionary containing error metrics for each category

    Returns:
        Dictionary with formatted metric strings ready for table display
    """
    return {
        "WER": f"{metrics[CAT_WORD]['error_rate']:.2%}",
        "LER": f"{metrics[CAT_LEGAL]['error_rate']:.2%}",
        "NER": f"{metrics[CAT_NUMERAL]['error_rate']:.2%}",
        "PER": f"{metrics[CAT_PUNCT]['error_rate']:.2%}",
        "Sandhi": metrics[CAT_WORD]['sandhi_hits'],
        "Total": metrics[CAT_WORD].get('combined_total', 0)
    }


def format_dataset_table(agg_results: Dict) -> List[Dict]:
    """
    Format aggregate results as list of dicts for table display.

    Used by both CLI (print_evaluation_summary) and UI (visualizer).

    Args:
        agg_results: Dictionary with 'overall' and 'by_dataset' keys

    Returns:
        List of dictionaries, each containing Dataset name and error metrics
    """
    table_data = []

    # Overall row
    overall = format_metrics_dict(agg_results['overall'])
    overall['Dataset'] = 'OVERALL'
    table_data.append(overall)

    # Per-dataset rows
    for ds, metrics in agg_results['by_dataset'].items():
        row = format_metrics_dict(metrics)
        row['Dataset'] = ds
        table_data.append(row)

    return table_data


def format_error_counts_table(report: Dict) -> List[Dict]:
    """
    Format error counts by category for detailed inspection.

    Args:
        report: Token error rates report from token_error_rates()

    Returns:
        List of dictionaries with Category, Type, and Count
    """
    counts = []
    for cat in [CAT_WORD, CAT_LEGAL, CAT_NUMERAL, CAT_PUNCT]:
        counts.extend([
            {"Category": cat, "Type": "Substitutions", "Count": report[cat]["substitutions"]},
            {"Category": cat, "Type": "Insertions", "Count": report[cat]["insertions"]},
            {"Category": cat, "Type": "Deletions", "Count": report[cat]["deletions"]},
            {"Category": cat, "Type": "Correct", "Count": report[cat]["correct"]}
        ])
    return counts


def format_alignment_table(aligned_ref: List[Tuple], aligned_hyp: List[Tuple]) -> List[Dict]:
    """
    Format aligned tokens for visualization table.

    Args:
        aligned_ref: List of (text, tag) tuples for reference
        aligned_hyp: List of (text, tag) tuples for hypothesis

    Returns:
        List of dictionaries with Position, Reference, Hypothesis, Error Type, Token Type
    """
    rows = []
    for i, ((ref_txt, ref_tag), (hyp_txt, hyp_tag)) in enumerate(zip(aligned_ref, aligned_hyp)):
        # Determine error type
        if "MERGE:" in ref_txt or "SPLIT:" in hyp_txt:
            error_type = "Sandhi"
        elif ref_txt == "**":
            error_type = "Insertion"
        elif hyp_txt == "**":
            error_type = "Deletion"
        elif ref_txt == hyp_txt:
            error_type = "Correct"
        else:
            error_type = "Substitution"

        # Clean display - remove markers
        display_ref = ref_txt.replace("MERGE:", "").replace("SPLIT:", "") if ref_txt != "**" else "**"
        display_hyp = hyp_txt.replace("MERGE:", "").replace("SPLIT:", "") if hyp_txt != "**" else "**"
        token_type = ref_tag if ref_tag != "GAP" else hyp_tag

        rows.append({
            "Position": i + 1,
            "Reference": display_ref,
            "Hypothesis": display_hyp,
            "Error Type": error_type,
            "Token Type": token_type
        })

    return rows
