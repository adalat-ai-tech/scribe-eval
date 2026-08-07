"""
Report formatting and presentation utilities.

This module provides shared functions for formatting error metrics
and alignment results for both CLI and web UI presentations.
"""

from typing import Dict, List, Tuple

from .analysis import compute_wer_scribe
from .constants import (
    CAT_LEXICAL,
    CAT_NUMERAL,
    CAT_PUNCT,
    CATEGORIES,
    COLUMN_WIDTHS,
    format_table_header,
)


def _format_rate(cat_metrics: Dict) -> str:
    """Format a category's error rate, or N/A when there was nothing
    to measure.

    A category with zero reference tokens and zero errors renders as
    "N/A" — showing 0.00% would read as *perfect* when the truth is
    that no such tokens occurred. A hallucination-only category
    (insertions with no reference tokens) still shows its rate.
    """
    errors = cat_metrics["substitutions"] + cat_metrics["insertions"] + cat_metrics["deletions"]
    # Per-sample reports store the reference count as "total_ref";
    # aggregates store it as "total".
    total_ref = cat_metrics.get("total_ref", cat_metrics.get("total", 0))
    if total_ref == 0 and errors == 0:
        return "N/A"
    return f"{cat_metrics['error_rate']:.2%}"


def resolve_domain_labels(metrics: Dict) -> Dict[str, str]:
    """
    Map the domain category present in the metrics to its display label.

    SCRIBE supports a single active domain, and its error-rate column is
    always labelled "ER_DOMAIN" (Domain Error Rate) — the label is fixed
    by the toolkit, not by the domain configuration. If the data ever
    contains several domain categories (e.g. samples measured with
    different configs aggregated together), each falls back to its
    category name so none is hidden.

    Args:
        metrics: Dictionary containing error metrics for each category

    Returns:
        Ordered dict of {category: display_label} for domain categories
    """
    domain_cats = sorted(cat for cat in metrics.keys() if cat not in CATEGORIES)
    if len(domain_cats) == 1:
        return {domain_cats[0]: "ER_DOMAIN"}
    return {cat: cat for cat in domain_cats}


def format_metrics_dict(metrics: Dict) -> Dict[str, str]:
    """
    Extract ER_LEX/ER_DOMAIN/ER_NUM/ER_PUNCT and the composite
    WER_SCRIBE from aggregate metrics.

    Columns are derived from the categories present in the data; the
    domain category (if any) is reported as ER_DOMAIN. WER_SCRIBE is
    the sum of all category error rates (total errors over the combined
    denominator). A category with no tokens and no errors renders as
    "N/A" rather than a misleading 0.00%.

    Args:
        metrics: Dictionary containing error metrics for each category

    Returns:
        Dictionary with formatted metric strings ready for table display
    """
    result = {"ER_LEX": _format_rate(metrics[CAT_LEXICAL])}

    for cat, label in resolve_domain_labels(metrics).items():
        result[label] = _format_rate(metrics[cat])

    result["ER_NUM"] = _format_rate(metrics[CAT_NUMERAL])
    result["ER_PUNCT"] = _format_rate(metrics[CAT_PUNCT])
    result["WER_SCRIBE"] = f"{compute_wer_scribe(metrics):.2%}"

    # Sandhi can occur in any category (LEXICAL, LEGAL, MEDICAL, etc.).
    result["Sandhi"] = sum(metrics[cat]["sandhi_hits"] for cat in metrics.keys())
    result["Total"] = metrics[CAT_LEXICAL].get("combined_total", 0)

    return result


def extract_error_rates(report: Dict) -> Dict:
    """
    Extract error rates from report for display.

    The domain category's rate (if present in the data) is reported
    under the fixed "er_domain" key.

    Args:
        report: Dictionary containing error metrics for each category

    Returns:
        Dictionary with raw numeric error rates
    """
    # Sum sandhi_hits across all categories (Sandhi can occur in LEXICAL, LEGAL, MEDICAL, etc.)
    total_sandhi = sum(report[cat]["sandhi_hits"] for cat in report.keys())

    result = {
        "er_lex": report[CAT_LEXICAL]["error_rate"],
        "er_num": report[CAT_NUMERAL]["error_rate"],
        "er_punct": report[CAT_PUNCT]["error_rate"],
        "sandhi": total_sandhi,
    }

    for cat, label in resolve_domain_labels(report).items():
        result[label.lower()] = report[cat]["error_rate"]

    return result


def format_dataset_table(agg_results: Dict) -> List[Dict]:
    """
    Format aggregate results as list of dicts for table display.

    Args:
        agg_results: Dictionary with 'overall' and 'by_dataset' keys

    Returns:
        List of dictionaries, each containing Dataset name and error metrics
    """
    table_data = []

    # Overall row
    overall = format_metrics_dict(agg_results["overall"])
    overall["Dataset"] = "OVERALL"
    table_data.append(overall)

    # Per-dataset rows
    for ds, metrics in agg_results["by_dataset"].items():
        row = format_metrics_dict(metrics)
        row["Dataset"] = ds
        table_data.append(row)

    return table_data


def format_error_counts_table(report: Dict) -> List[Dict]:
    """
    Format error counts by category for detailed inspection.

    Every category present in the report is shown — nothing in the
    data is hidden.

    Args:
        report: Token error rates report from token_error_rates()

    Returns:
        List of dictionaries with Category, Type, and Count
    """
    counts = []
    for cat in report:
        counts.extend(
            [
                {"Category": cat, "Type": "Substitutions", "Count": report[cat]["substitutions"]},
                {"Category": cat, "Type": "Insertions", "Count": report[cat]["insertions"]},
                {"Category": cat, "Type": "Deletions", "Count": report[cat]["deletions"]},
                {"Category": cat, "Type": "Correct", "Count": report[cat]["correct"]},
            ]
        )
    return counts


def format_summary_lines(agg_results: Dict) -> List[str]:
    """
    Render the evaluation summary table as a list of text lines.

    Single renderer shared by print_evaluation_summary (console) and
    write_summary_to_file (file) so the two outputs cannot drift.
    Columns are derived from the categories present in the data; the
    domain category (if any) is shown as ER_DOMAIN.

    Args:
        agg_results: Dictionary with 'overall' and 'by_dataset' keys

    Returns:
        List of lines (no trailing newlines)
    """
    # Domain columns are fixed by the overall metrics; each row's value
    # is read by CATEGORY from that row's own metrics, not by label —
    # in a mixed aggregate a single-domain dataset row resolves its own
    # label differently than the table header, and a label lookup would
    # show N/A over a real number.
    labels = resolve_domain_labels(agg_results["overall"])

    header = format_table_header(list(labels.values()))
    width = len(header.split("\n")[0])
    dw = COLUMN_WIDTHS["dataset"]
    mw = COLUMN_WIDTHS["metric"]
    sw = COLUMN_WIDTHS["sandhi"]

    named_metrics = [("OVERALL", agg_results["overall"])]
    named_metrics += list(agg_results["by_dataset"].items())

    lines = ["=" * width, *header.split("\n")]
    for ds_name, metrics in named_metrics:
        row = format_metrics_dict(metrics)
        cells = [f"{ds_name:<{dw}}", f"{row['ER_LEX']:>{mw}}"]
        for cat in labels:
            if cat in metrics:
                # _format_rate renders N/A for a present-but-empty
                # category, matching the absent-category case below.
                cells.append(f"{_format_rate(metrics[cat]):>{mw}}")
            else:
                # Genuinely absent from this dataset's data.
                cells.append(f"{'N/A':>{mw}}")
        cells.append(f"{row['ER_NUM']:>{mw}}")
        cells.append(f"{row['ER_PUNCT']:>{mw}}")
        cells.append(f"{row['WER_SCRIBE']:>{mw}}")
        cells.append(f"{row['Sandhi']:>{sw}}")
        lines.append(" | ".join(cells))
        if ds_name == "OVERALL":
            lines.append("-" * width)
    lines.append("=" * width)
    return lines


def write_summary_to_file(agg_results: Dict, output_path: str) -> None:
    """
    Write evaluation summary to file safely.

    Args:
        agg_results: Dictionary with 'overall' and 'by_dataset' keys
        output_path: Path to output file
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n")
        for line in format_summary_lines(agg_results):
            f.write(line + "\n")


def format_contribution_table(contributions: Dict) -> List[Dict]:
    """
    Format category breakdown as table rows with correct/error counts.

    Args:
        contributions: From compute_category_contributions()

    Returns:
        List of dicts sorted by ref_tokens descending, plus a TOTAL row.
        Each dict includes:
            Error Rate: (S+I+D) / category_ref_tokens — accuracy within this category
            Impact on Total: (S+I+D) / total_ref_tokens — contribution to overall ER
    """
    # Display names for categories
    category_display = {
        CAT_LEXICAL: "Lexical Tokens",
        CAT_PUNCT: "Punctuation Tokens",
        CAT_NUMERAL: "Numeral Tokens",
    }

    rows = []
    total_correct = 0
    total_subs = 0
    total_dels = 0
    total_ins = 0
    total_ref = 0

    # A single domain category displays as "Domain Tokens"; with several
    # (mixed aggregates), each keeps its category name so distinct
    # counts remain distinguishable.
    domain_cats = [c for c in contributions if c not in category_display]
    if len(domain_cats) > 1:
        for c in domain_cats:
            category_display[c] = f"{c} Tokens"

    # First pass: compute total_ref for the "Impact on Total" column
    for data in contributions.values():
        total_ref += data.get("ref_tokens", 0)

    for cat, data in sorted(contributions.items(), key=lambda x: x[1]["ref_tokens"], reverse=True):
        ref = data["ref_tokens"]
        cat_er = (data["error_count"] / ref * 100) if ref > 0 else 0.0
        impact = (data["error_count"] / total_ref * 100) if total_ref > 0 else 0.0
        display_name = category_display.get(cat, "Domain Tokens")
        # Accuracy and Error Rate divide by the category's own ref
        # tokens — undefined when there are none (0.0% would read as
        # "all missed" and "perfect" respectively, both wrong for a
        # hallucination-only row). Impact on Total divides by ALL ref
        # tokens, so it stays meaningful whenever errors exist; it is
        # N/A only when there is nothing measured at all.
        nothing_measured = ref == 0 and data["error_count"] == 0
        rows.append(
            {
                "Category": display_name,
                "Ref Tokens": ref,
                "Match": data["correct"],
                "Accuracy": f"{data['correct_pct']:.1f}%" if ref > 0 else "N/A",
                "Sub": data["substitutions"],
                "Del": data["deletions"],
                "Ins": data["insertions"],
                "Errors": data["error_count"],
                "Error Rate": f"{cat_er:.1f}%" if ref > 0 else "N/A",
                "Impact on Total": "N/A" if nothing_measured else f"{impact:.1f}%",
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
            "Match": total_correct,
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


def format_category_chips(contributions: Dict, domain_display: str = "Domain Tokens") -> List[str]:
    """
    Return "Lexical Tokens 5.40%" style chips in canonical display order.

    The chips caption is an equation — the chip rates sum to WER_SCRIBE —
    so categories with no tokens and no errors are omitted: they
    contribute nothing to the sum, and a 0.00% chip would read as
    "perfect" when nothing was measured. A hallucination-only category
    (errors with no reference tokens) keeps its chip.

    Args:
        contributions: From compute_category_contributions()
        domain_display: Display name for domain categories
            (e.g. "Legal Tokens")

    Returns:
        List of chip strings in canonical order
        (Lexical, Domain, Numeral, Punctuation)
    """
    display_names = {
        CAT_LEXICAL: "Lexical Tokens",
        CAT_NUMERAL: "Numeral Tokens",
        CAT_PUNCT: "Punctuation Tokens",
    }
    base_cats = set(display_names)
    domain_cats = [c for c in contributions if c not in base_cats]
    # A single domain category uses the caller's display name; with
    # several (mixed aggregates) each keeps its category name so no
    # contribution is misattributed — same rule as the contribution
    # table.
    if len(domain_cats) > 1:
        for cat in domain_cats:
            display_names[cat] = f"{cat} Tokens"
    ordered_cats = [
        c for c in [CAT_LEXICAL] + domain_cats + [CAT_NUMERAL, CAT_PUNCT] if c in contributions
    ]
    chips = []
    for cat in ordered_cats:
        data = contributions[cat]
        if data["ref_tokens"] == 0 and data["error_count"] == 0:
            continue
        chips.append(f"{display_names.get(cat, domain_display)} {data['error_rate']:.2%}")
    return chips


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
