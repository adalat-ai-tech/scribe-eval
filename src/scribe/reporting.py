"""
Report formatting and presentation utilities.

This module provides shared functions for formatting error metrics
and alignment results for both CLI and web UI presentations.
"""

from typing import Dict, List, Optional, Tuple

from .constants import (
    CAT_NUMERAL,
    CAT_PUNCT,
    CAT_WORD,
    TABLE_WIDTH,
    format_table_header,
    get_categories,
)
from .domain_config import DomainConfig


def format_metrics_dict(
    metrics: Dict, domain_config: Optional[DomainConfig] = None
) -> Dict[str, str]:
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
        # Sum sandhi_hits across all categories (Sandhi can occur in WORD, LEGAL, MEDICAL, etc.)
        total_sandhi = sum(metrics[cat]["sandhi_hits"] for cat in metrics.keys())
        result["Sandhi"] = total_sandhi
        result["Total"] = metrics[CAT_WORD].get("combined_total", 0)

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
    # Sum sandhi_hits across all categories (Sandhi can occur in WORD, LEGAL, MEDICAL, etc.)
    total_sandhi = sum(report[cat]["sandhi_hits"] for cat in report.keys())

    result = {
        "wer": report[CAT_WORD]["error_rate"],
        "ner": report[CAT_NUMERAL]["error_rate"],
        "per": report[CAT_PUNCT]["error_rate"],
        "sandhi": total_sandhi,
    }

    if domain_config:
        # Use lowercase label for consistency
        result[domain_config.label.lower()] = report[domain_config.category]["error_rate"]

    return result


def format_dataset_table(
    agg_results: Dict, domain_config: Optional[DomainConfig] = None
) -> List[Dict]:
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
    overall = format_metrics_dict(agg_results["overall"], domain_config)
    overall["Dataset"] = "OVERALL"
    table_data.append(overall)

    # Per-dataset rows
    for ds, metrics in agg_results["by_dataset"].items():
        row = format_metrics_dict(metrics, domain_config)
        row["Dataset"] = ds
        table_data.append(row)

    return table_data


def format_error_counts_table(
    report: Dict, domain_config: Optional[DomainConfig] = None
) -> List[Dict]:
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
        counts.extend(
            [
                {"Category": cat, "Type": "Substitutions", "Count": report[cat]["substitutions"]},
                {"Category": cat, "Type": "Insertions", "Count": report[cat]["insertions"]},
                {"Category": cat, "Type": "Deletions", "Count": report[cat]["deletions"]},
                {"Category": cat, "Type": "Correct", "Count": report[cat]["correct"]},
            ]
        )
    return counts


def write_summary_to_file(
    agg_results: Dict, output_path: str, domain_config: Optional[DomainConfig] = None
) -> None:
    """
    Write evaluation summary to file safely.

    Args:
        agg_results: Dictionary with 'overall' and 'by_dataset' keys
        output_path: Path to output file
        domain_config: Domain configuration for label formatting
    """
    with open(output_path, "w", encoding="utf-8") as f:
        table_data = format_dataset_table(agg_results, domain_config)

        # Write formatted table with proper headers
        domain_label = domain_config.label if domain_config else "DER"
        f.write("\n" + "=" * TABLE_WIDTH + "\n")
        f.write(format_table_header(domain_label) + "\n")

        for row in table_data:
            is_overall = row["Dataset"] == "OVERALL"
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


def format_contribution_table(
    contributions: Dict, domain_config: Optional[DomainConfig] = None
) -> List[Dict]:
    """
    Format category breakdown as table rows with correct/error counts.

    Args:
        contributions: From compute_category_contributions()
        domain_config: For category label mapping

    Returns:
        List of dicts sorted by ref_tokens descending, plus a TOTAL row.
        Each dict includes:
            Error Rate: (S+I+D) / category_ref_tokens — accuracy within this category
            Impact on Total: (S+I+D) / total_ref_tokens — contribution to overall ER
    """
    # Display names for categories
    category_display = {
        CAT_WORD: "Word Tokens",
        CAT_PUNCT: "Punctuation Tokens",
        CAT_NUMERAL: "Numeral Tokens",
    }

    rows = []
    total_correct = 0
    total_subs = 0
    total_dels = 0
    total_ins = 0
    total_ref = 0

    # First pass: compute total_ref for the "Impact on Total" column
    for data in contributions.values():
        total_ref += data.get("ref_tokens", 0)

    for cat, data in sorted(contributions.items(), key=lambda x: x[1]["ref_tokens"], reverse=True):
        ref = data["ref_tokens"]
        cat_er = (data["error_count"] / ref * 100) if ref > 0 else 0.0
        impact = (data["error_count"] / total_ref * 100) if total_ref > 0 else 0.0
        display_name = category_display.get(cat, "Domain Tokens")
        rows.append(
            {
                "Category": display_name,
                "Ref Tokens": ref,
                "Exact Match": data["correct"],
                "Accuracy": f"{data['correct_pct']:.1f}%",
                "Sub": data["substitutions"],
                "Del": data["deletions"],
                "Ins": data["insertions"],
                "Errors": data["error_count"],
                "Error Rate": f"{cat_er:.1f}%",
                "Impact on Total": f"{impact:.1f}%",
            }
        )
        total_correct += data["correct"]
        total_subs += data["substitutions"]
        total_dels += data["deletions"]
        total_ins += data["insertions"]

    total_errors = total_subs + total_ins + total_dels
    total_correct_pct = (total_correct / total_ref * 100) if total_ref > 0 else 0.0
    total_er_pct = (total_errors / total_ref * 100) if total_ref > 0 else 0.0
    rows.append(
        {
            "Category": "TOTAL",
            "Ref Tokens": total_ref,
            "Exact Match": total_correct,
            "Accuracy": f"{total_correct_pct:.1f}%",
            "Sub": total_subs,
            "Del": total_dels,
            "Ins": total_ins,
            "Errors": total_errors,
            "Error Rate": f"{total_er_pct:.1f}%",
            "Impact on Total": f"{total_er_pct:.1f}%",
        }
    )
    return rows


def format_frequent_errors_table(
    freq_data: Dict[str, List], error_type: str, top_n: int = 10
) -> List[Dict]:
    """
    Format frequent error data as table rows.

    Args:
        freq_data: From compute_frequent_substitutions/deletions/insertions/
            sandhi_merges/sandhi_splits. Uses the "_all" key for overall ranking.
        error_type: "substitution", "deletion", "insertion",
            "sandhi_merge", or "sandhi_split"
        top_n: Max rows to return

    Returns:
        For substitutions/sandhi_merge/sandhi_split:
            [{Rank, Category, Reference, Hypothesis, Count}]
        For deletions/insertions:
            [{Rank, Category, Token, Count}]
    """
    pair_types = {"substitution", "sandhi_merge", "sandhi_split"}
    is_pair = error_type in pair_types

    # Use "_all" for the overall flat ranking
    items = freq_data.get("_all", [])[:top_n]

    # Build a reverse lookup: token -> category (from per-category data)
    token_to_cat: Dict[str, str] = {}
    for cat, cat_items in freq_data.items():
        if cat == "_all":
            continue
        for item in cat_items:
            if is_pair:
                token_to_cat[(item[0], item[1])] = cat
            else:
                token_to_cat[item[0]] = cat

    rows = []
    for rank, item in enumerate(items, 1):
        if is_pair:
            ref, hyp, count = item
            cat = token_to_cat.get((ref, hyp), "")
            rows.append(
                {
                    "Rank": rank,
                    "Category": cat,
                    "Reference": ref,
                    "Hypothesis": hyp,
                    "Count": count,
                }
            )
        else:
            token, count = item
            cat = token_to_cat.get(token, "")
            rows.append({"Rank": rank, "Category": cat, "Token": token, "Count": count})

    return rows


def format_alignment_dict(
    aligned_ref: List[Tuple], aligned_hyp: List[Tuple], normalize: bool = True
) -> List[Dict]:
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
        display_ref = (
            ref_txt.replace("MERGE:", "").replace("SPLIT:", "") if ref_txt != "**" else "**"
        )
        display_hyp = (
            hyp_txt.replace("MERGE:", "").replace("SPLIT:", "") if hyp_txt != "**" else "**"
        )
        token_type = ref_tag if ref_tag != "GAP" else hyp_tag

        results.append(
            {
                "ref_text": display_ref,
                "hyp_text": display_hyp,
                "error_type": error_type,
                "token_type": token_type,
            }
        )

    return results


def format_alignment_table(
    aligned_ref: List[Tuple], aligned_hyp: List[Tuple], normalize: bool = True
) -> List[Dict]:
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
        rows.append(
            {
                "Position": i + 1,
                "Reference": item["ref_text"],
                "Hypothesis": item["hyp_text"],
                "Error Type": item["error_type"].capitalize(),
                "Token Type": item["token_type"],
            }
        )

    return rows
