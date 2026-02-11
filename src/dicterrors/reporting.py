"""
Report formatting and presentation utilities.

This module provides shared functions for formatting error metrics
and alignment results for both CLI and web UI presentations.
"""
from typing import Dict, List, Tuple
from .constants import CAT_WORD, CAT_LEGAL, CAT_NUMERAL, CAT_PUNCT, CATEGORIES, format_table_header, TABLE_WIDTH


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


def extract_error_rates(report: Dict) -> Dict:
    """
    Extract WER/LER/NER/PER/Sandhi from report for display.

    Returns raw numeric values (not formatted strings) for use in UI components.

    Args:
        report: Dictionary containing error metrics for each category

    Returns:
        Dictionary with raw numeric error rates and sandhi hits
    """
    return {
        'wer': report[CAT_WORD]['error_rate'],
        'ler': report[CAT_LEGAL]['error_rate'],
        'ner': report[CAT_NUMERAL]['error_rate'],
        'per': report[CAT_PUNCT]['error_rate'],
        'sandhi': report[CAT_WORD]['sandhi_hits']
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
    for cat in CATEGORIES:
        counts.extend([
            {"Category": cat, "Type": "Substitutions", "Count": report[cat]["substitutions"]},
            {"Category": cat, "Type": "Insertions", "Count": report[cat]["insertions"]},
            {"Category": cat, "Type": "Deletions", "Count": report[cat]["deletions"]},
            {"Category": cat, "Type": "Correct", "Count": report[cat]["correct"]}
        ])
    return counts


def write_summary_to_file(agg_results: Dict, output_path: str) -> None:
    """
    Write evaluation summary to file safely.

    Args:
        agg_results: Dictionary with 'overall' and 'by_dataset' keys
        output_path: Path to output file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        table_data = format_dataset_table(agg_results)

        # Write formatted table with proper headers
        f.write("\n" + "=" * TABLE_WIDTH + "\n")
        f.write(format_table_header() + "\n")

        for row in table_data:
            is_overall = row['Dataset'] == 'OVERALL'
            if is_overall and table_data.index(row) > 0:
                # Add separator line before OVERALL row if it's not first
                f.write("-" * TABLE_WIDTH + "\n")

            f.write(
                f"{row['Dataset']:<25} | "
                f"{row['WER']:>8} | "
                f"{row['LER']:>8} | "
                f"{row['NER']:>8} | "
                f"{row['PER']:>8} | "
                f"{row['Sandhi']:>6}\n"
            )

        f.write("=" * TABLE_WIDTH + "\n")


def format_alignment_dict(aligned_ref: List[Tuple], aligned_hyp: List[Tuple]) -> List[Dict]:
    """
    Extract alignment data as structured dict for rendering.

    Provides shared error detection logic used by both CLI and UI.

    Args:
        aligned_ref: List of (text, tag) tuples for reference
        aligned_hyp: List of (text, tag) tuples for hypothesis

    Returns:
        List of dicts with ref_text, hyp_text, error_type, token_type
    """
    results = []
    for (ref_txt, ref_tag), (hyp_txt, hyp_tag) in zip(aligned_ref, aligned_hyp):
        # Determine error type (shared logic)
        if "MERGE:" in ref_txt or "SPLIT:" in hyp_txt:
            error_type = "sandhi"
        elif ref_txt == "**":
            error_type = "insertion"
        elif hyp_txt == "**":
            error_type = "deletion"
        elif ref_txt == hyp_txt:
            error_type = "correct"
        else:
            error_type = "substitution"

        # Clean display text - remove markers
        display_ref = ref_txt.replace("MERGE:", "").replace("SPLIT:", "") if ref_txt != "**" else "**"
        display_hyp = hyp_txt.replace("MERGE:", "").replace("SPLIT:", "") if hyp_txt != "**" else "**"
        token_type = ref_tag if ref_tag != "GAP" else hyp_tag

        results.append({
            'ref_text': display_ref,
            'hyp_text': display_hyp,
            'error_type': error_type,
            'token_type': token_type
        })

    return results


def format_alignment_table(aligned_ref: List[Tuple], aligned_hyp: List[Tuple]) -> List[Dict]:
    """
    Format aligned tokens for visualization table.

    Uses format_alignment_dict() internally for error detection logic.

    Args:
        aligned_ref: List of (text, tag) tuples for reference
        aligned_hyp: List of (text, tag) tuples for hypothesis

    Returns:
        List of dictionaries with Position, Reference, Hypothesis, Error Type, Token Type
    """
    # Use shared error detection logic
    alignment_data = format_alignment_dict(aligned_ref, aligned_hyp)

    # Add position and capitalize error types for table display
    rows = []
    for i, item in enumerate(alignment_data):
        rows.append({
            "Position": i + 1,
            "Reference": item['ref_text'],
            "Hypothesis": item['hyp_text'],
            "Error Type": item['error_type'].capitalize(),
            "Token Type": item['token_type']
        })

    return rows
