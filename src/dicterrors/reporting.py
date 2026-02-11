"""
Report formatting and presentation utilities.

This module provides shared functions for formatting error metrics
and alignment results for both CLI and web UI presentations.
"""
from typing import Dict, List, Tuple, Optional
from .constants import CAT_WORD, CAT_NUMERAL, CAT_PUNCT, get_categories, format_table_header, TABLE_WIDTH
from .domain_config import DomainConfig


def format_metrics_dict(metrics: Dict, domain_config: Optional[DomainConfig] = None) -> Dict[str, str]:
    """
    Extract WER/DER/NER/PER from aggregate metrics.

    Args:
        metrics: Dictionary containing error metrics for each category
        domain_config: Domain configuration (None to skip domain metrics)

    Returns:
        Dictionary with formatted metric strings ready for table display
    """
    result = {
        "WER": f"{metrics[CAT_WORD]['error_rate']:.2%}",
        "NER": f"{metrics[CAT_NUMERAL]['error_rate']:.2%}",
        "PER": f"{metrics[CAT_PUNCT]['error_rate']:.2%}",
    }

    if domain_config:
        result[domain_config.label] = f"{metrics[domain_config.category]['error_rate']:.2%}"
        result["Sandhi"] = metrics[CAT_WORD]['sandhi_hits']
        result["Total"] = metrics[CAT_WORD].get('combined_total', 0)

    return result


def extract_error_rates(report: Dict, domain_config: Optional[DomainConfig] = None) -> Dict:
    """
    Extract error rates from report for display.

    Args:
        report: Dictionary containing error metrics for each category
        domain_config: Domain configuration (None to skip domain metrics)

    Returns:
        Dictionary with raw numeric error rates
    """
    result = {
        'wer': report[CAT_WORD]['error_rate'],
        'ner': report[CAT_NUMERAL]['error_rate'],
        'per': report[CAT_PUNCT]['error_rate'],
        'sandhi': report[CAT_WORD]['sandhi_hits']
    }

    if domain_config:
        # Use lowercase label for consistency
        result[domain_config.label.lower()] = report[domain_config.category]['error_rate']

    return result


def format_dataset_table(agg_results: Dict, domain_config: Optional[DomainConfig] = None) -> List[Dict]:
    """
    Format aggregate results as list of dicts for table display.

    Args:
        agg_results: Dictionary with 'overall' and 'by_dataset' keys
        domain_config: Domain configuration for metric formatting

    Returns:
        List of dictionaries, each containing Dataset name and error metrics
    """
    table_data = []

    # Overall row
    overall = format_metrics_dict(agg_results['overall'], domain_config)
    overall['Dataset'] = 'OVERALL'
    table_data.append(overall)

    # Per-dataset rows
    for ds, metrics in agg_results['by_dataset'].items():
        row = format_metrics_dict(metrics, domain_config)
        row['Dataset'] = ds
        table_data.append(row)

    return table_data


def format_error_counts_table(report: Dict, domain_config: Optional[DomainConfig] = None) -> List[Dict]:
    """
    Format error counts by category for detailed inspection.

    Args:
        report: Token error rates report from token_error_rates()
        domain_config: Domain configuration (None to use base categories)

    Returns:
        List of dictionaries with Category, Type, and Count
    """
    categories = get_categories(domain_config)

    counts = []
    for cat in categories:
        if cat not in report:
            continue
        counts.extend([
            {"Category": cat, "Type": "Substitutions", "Count": report[cat]["substitutions"]},
            {"Category": cat, "Type": "Insertions", "Count": report[cat]["insertions"]},
            {"Category": cat, "Type": "Deletions", "Count": report[cat]["deletions"]},
            {"Category": cat, "Type": "Correct", "Count": report[cat]["correct"]}
        ])
    return counts


def write_summary_to_file(agg_results: Dict, output_path: str, domain_config: Optional[DomainConfig] = None) -> None:
    """
    Write evaluation summary to file safely.

    Args:
        agg_results: Dictionary with 'overall' and 'by_dataset' keys
        output_path: Path to output file
        domain_config: Domain configuration for label formatting
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        table_data = format_dataset_table(agg_results, domain_config)

        # Write formatted table with proper headers
        domain_label = domain_config.label if domain_config else "DER"
        f.write("\n" + "=" * TABLE_WIDTH + "\n")
        f.write(format_table_header(domain_label) + "\n")

        for row in table_data:
            is_overall = row['Dataset'] == 'OVERALL'
            if is_overall and table_data.index(row) > 0:
                # Add separator line before OVERALL row if it's not first
                f.write("-" * TABLE_WIDTH + "\n")

            # Dynamic column access
            f.write(
                f"{row['Dataset']:<25} | "
                f"{row['WER']:>8} | "
                f"{row[domain_label]:>8} | "
                f"{row['NER']:>8} | "
                f"{row['PER']:>8} | "
                f"{row['Sandhi']:>6}\n"
            )

        f.write("=" * TABLE_WIDTH + "\n")


def format_alignment_dict(aligned_ref: List[Tuple], aligned_hyp: List[Tuple], normalize: bool = True) -> List[Dict]:
    """
    Extract alignment data as structured dict for rendering.

    Provides shared error detection logic used by both CLI and UI.

    Args:
        aligned_ref: List of (text, tag) tuples for reference
        aligned_hyp: List of (text, tag) tuples for hypothesis
        normalize: If True, apply normalization when checking equality (default: True)

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
            # Check if tokens match after normalization
            if normalize:
                from .normalize import normalize_token
                ref_normalized = normalize_token(ref_txt, ref_tag)
                hyp_normalized = normalize_token(hyp_txt, hyp_tag)
                if ref_normalized == hyp_normalized:
                    error_type = "correct"
                else:
                    error_type = "substitution"
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


def format_alignment_table(aligned_ref: List[Tuple], aligned_hyp: List[Tuple], normalize: bool = True) -> List[Dict]:
    """
    Format aligned tokens for visualization table.

    Uses format_alignment_dict() internally for error detection logic.

    Args:
        aligned_ref: List of (text, tag) tuples for reference
        aligned_hyp: List of (text, tag) tuples for hypothesis
        normalize: If True, apply normalization when checking equality (default: True)

    Returns:
        List of dictionaries with Position, Reference, Hypothesis, Error Type, Token Type
    """
    # Use shared error detection logic
    alignment_data = format_alignment_dict(aligned_ref, aligned_hyp, normalize)

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
