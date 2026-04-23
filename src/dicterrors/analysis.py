"""
Analytical computations for ASR error insights.

This module transforms measured error data into actionable insights:
total error rates, category contributions, error type distributions,
and frequency analysis of specific token errors.
"""

from collections import Counter


def compute_total_error_rate(metrics: dict[str, dict]) -> float:
    """
    Compute composite Total Error Rate from category metrics.

    Since each category's error_rate uses combined_total as denominator,
    the sum naturally equals total_errors / combined_total.

    Args:
        metrics: Output of token_error_rates() or aggregate metrics —
                 maps category name -> dict with 'error_rate' key

    Returns:
        Total error rate as a float (0.0 to 1.0)
    """
    return sum(cat_data["error_rate"] for cat_data in metrics.values())


def compute_category_contributions(
    metrics: dict[str, dict],
) -> dict[str, dict]:
    """
    Compute full breakdown per category: correct/sub/del/ins counts and rates.

    Args:
        metrics: Output of token_error_rates() or aggregate metrics

    Returns:
        Dict mapping category -> {
            "correct": int,
            "substitutions": int,
            "deletions": int,
            "insertions": int,
            "ref_tokens": int,       # correct + sub + del (reference side)
            "correct_pct": float,    # correct / ref_tokens * 100
            "error_count": int,      # sub + ins + del
            "error_rate": float,     # from metrics (uses combined denominator)
            "contribution_pct": float, # this category's share of total errors
        }
    """
    contributions = {}
    total_errors = 0

    for cat, data in metrics.items():
        correct = data["correct"]
        subs = data["substitutions"]
        ins = data["insertions"]
        dels = data["deletions"]
        ref_tokens = data.get("total_ref", data.get("total", 0))
        error_count = subs + ins + dels
        total_errors += error_count

        contributions[cat] = {
            "correct": correct,
            "substitutions": subs,
            "deletions": dels,
            "insertions": ins,
            "ref_tokens": ref_tokens,
            "correct_pct": (correct / ref_tokens * 100) if ref_tokens > 0 else 0.0,
            "error_count": error_count,
            "error_rate": data["error_rate"],
        }

    for cat in contributions:
        if total_errors > 0:
            contributions[cat]["contribution_pct"] = (
                contributions[cat]["error_count"] / total_errors * 100
            )
        else:
            contributions[cat]["contribution_pct"] = 0.0

    return contributions


def compute_error_type_distribution(
    metrics: dict[str, dict],
) -> dict[str, dict[str, float]]:
    """
    For each category, compute the fraction of errors that are subs/ins/del.

    Args:
        metrics: Output of token_error_rates() or aggregate metrics

    Returns:
        Dict mapping category -> {
            "substitution_pct": float (0-100),
            "insertion_pct": float (0-100),
            "deletion_pct": float (0-100),
        }
    """
    result = {}
    for cat, data in metrics.items():
        total = data["substitutions"] + data["insertions"] + data["deletions"]
        if total > 0:
            result[cat] = {
                "substitution_pct": data["substitutions"] / total * 100,
                "insertion_pct": data["insertions"] / total * 100,
                "deletion_pct": data["deletions"] / total * 100,
            }
        else:
            result[cat] = {
                "substitution_pct": 0.0,
                "insertion_pct": 0.0,
                "deletion_pct": 0.0,
            }
    return result


def compute_frequent_substitutions(
    error_details: list[dict],
    top_n: int = 20,
) -> dict[str, list[tuple[str, str, int]]]:
    """
    Find the most frequently substituted token pairs.

    Args:
        error_details: List of error record dicts from token_error_details()
        top_n: Number of top substitutions to return per category

    Returns:
        Dict mapping category -> list of (ref_token, hyp_token, count)
        sorted by count descending. Key "_all" has the overall list.
    """
    subs = [e for e in error_details if e["error_type"] == "substitution"]

    # Overall
    overall_counter = Counter((e["ref_token"], e["hyp_token"]) for e in subs)
    result = {
        "_all": [(ref, hyp, count) for (ref, hyp), count in overall_counter.most_common(top_n)]
    }

    # By category
    by_cat: dict[str, list[dict]] = {}
    for e in subs:
        by_cat.setdefault(e["category"], []).append(e)

    for cat, cat_errors in by_cat.items():
        counter = Counter((e["ref_token"], e["hyp_token"]) for e in cat_errors)
        result[cat] = [(ref, hyp, count) for (ref, hyp), count in counter.most_common(top_n)]

    return result


def compute_frequent_deletions(
    error_details: list[dict],
    top_n: int = 20,
) -> dict[str, list[tuple[str, int]]]:
    """
    Find the most frequently deleted tokens.

    Args:
        error_details: from token_error_details()
        top_n: number of top deletions to return

    Returns:
        Dict mapping category -> list of (ref_token, count) sorted descending.
        Key "_all" for the overall list.
    """
    dels = [e for e in error_details if e["error_type"] == "deletion"]

    overall_counter = Counter(e["ref_token"] for e in dels)
    result = {"_all": [(token, count) for token, count in overall_counter.most_common(top_n)]}

    by_cat: dict[str, list[dict]] = {}
    for e in dels:
        by_cat.setdefault(e["category"], []).append(e)

    for cat, cat_errors in by_cat.items():
        counter = Counter(e["ref_token"] for e in cat_errors)
        result[cat] = [(token, count) for token, count in counter.most_common(top_n)]

    return result


def compute_frequent_insertions(
    error_details: list[dict],
    top_n: int = 20,
) -> dict[str, list[tuple[str, int]]]:
    """
    Find the most frequently inserted tokens.

    Args:
        error_details: from token_error_details()
        top_n: number of top insertions to return

    Returns:
        Dict mapping category -> list of (hyp_token, count) sorted descending.
        Key "_all" for the overall list.
    """
    ins = [e for e in error_details if e["error_type"] == "insertion"]

    overall_counter = Counter(e["hyp_token"] for e in ins)
    result = {"_all": [(token, count) for token, count in overall_counter.most_common(top_n)]}

    by_cat: dict[str, list[dict]] = {}
    for e in ins:
        by_cat.setdefault(e["category"], []).append(e)

    for cat, cat_errors in by_cat.items():
        counter = Counter(e["hyp_token"] for e in cat_errors)
        result[cat] = [(token, count) for token, count in counter.most_common(top_n)]

    return result


def compute_error_summary(
    metrics: dict[str, dict],
    error_details: list[dict],
    top_n: int = 10,
) -> dict:
    """
    Compute all analysis in one call.

    Args:
        metrics: Output of token_error_rates() or aggregate metrics
        error_details: Flat list of error records from token_error_details()
        top_n: Number of top frequent errors to include

    Returns:
        {
            "total_error_rate": float,
            "contributions": dict from compute_category_contributions,
            "error_type_distribution": dict from compute_error_type_distribution,
            "frequent_substitutions": dict from compute_frequent_substitutions,
            "frequent_deletions": dict from compute_frequent_deletions,
            "frequent_insertions": dict from compute_frequent_insertions,
        }
    """
    contributions = compute_category_contributions(metrics)

    # Overall correct rate across all categories
    total_correct = sum(c["correct"] for c in contributions.values())
    total_ref = sum(c["ref_tokens"] for c in contributions.values())
    total_correct_pct = (total_correct / total_ref * 100) if total_ref > 0 else 0.0

    return {
        "total_error_rate": compute_total_error_rate(metrics),
        "total_correct_pct": total_correct_pct,
        "contributions": contributions,
        "error_type_distribution": compute_error_type_distribution(metrics),
        "frequent_substitutions": compute_frequent_substitutions(error_details, top_n),
        "frequent_deletions": compute_frequent_deletions(error_details, top_n),
        "frequent_insertions": compute_frequent_insertions(error_details, top_n),
    }
