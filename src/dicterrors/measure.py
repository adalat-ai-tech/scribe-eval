from typing import Optional
from .tokenize import domain_aware_tokenizer
from .align import align_arrays
from .constants import get_categories, init_stat_dict, calculate_combined_total
from .domain_config import DomainConfig

def token_error_rates(aligned_ref, aligned_hyp, domain_config: Optional[DomainConfig] = None, normalize: bool = True, use_sandhi: bool = True) -> dict[str, dict[str, float | int]]:
    """
    Calculate error rates from aligned tokens.

    Args:
        aligned_ref: list of (text, tag) tuples
        aligned_hyp: list of (text, tag) tuples
        domain_config: Domain configuration (None for no domain)
        normalize: If True, check normalized equality for matches (default: True)

    Returns:
        Dictionary with error rates for each category
    """
    categories = get_categories(domain_config)
    stats = init_stat_dict(categories)

    for (r_text, r_tag), (h_text, h_tag) in zip(aligned_ref, aligned_hyp):
        
        # 1. Handle Insertions (Gap in Reference)
        if r_text == "**":
            # We categorize the insertion error based on what the ASR hallucinated
            if h_tag in stats:
                stats[h_tag]["insertions"] += 1
            continue

        # All other cases (Match, Sub, Del) are categorized by the REFERENCE tag
        if r_tag not in stats: continue
        curr = stats[r_tag]

        # 2. Handle Sandhi (Corrected Matches)
        if "MERGE:" in r_text:
            curr["total"] += 2  # A merge represents 2 original words
            curr["correct"] += 2
            curr["sandhi_hits"] += 1
            continue

        if "SPLIT:" in h_text:
            curr["total"] += 1
            curr["correct"] += 1
            curr["sandhi_hits"] += 1
            continue

        # 3. Standard Logic
        curr["total"] += 1
        if h_text == "**":
            curr["deletions"] += 1
        elif r_text == h_text:
            curr["correct"] += 1
        else:
            # Check if tokens match after normalization (if enabled)
            if normalize:
                from .normalize import normalize_token
                r_normalized = normalize_token(r_text, r_tag)
                h_normalized = normalize_token(h_text, h_tag)
                if r_normalized == h_normalized:
                    curr["correct"] += 1
                else:
                    curr["substitutions"] += 1
            else:
                curr["substitutions"] += 1

    # Final calculations for the report
    # Calculate combined denominator across ALL categories
    combined_total = calculate_combined_total(stats)

    report = {}
    for cat in categories:
        s = stats[cat]
        errors = s["substitutions"] + s["insertions"] + s["deletions"]

        # Use combined denominator for all categories
        rate = errors / max(1, combined_total)

        report[cat] = {
            "error_rate": rate,
            "substitutions": s["substitutions"],
            "insertions": s["insertions"],
            "deletions": s["deletions"],
            "correct": s["correct"],
            "total_ref": s["total"],
            "sandhi_hits": s["sandhi_hits"],
            "combined_total": combined_total  # Store for transparency
        }

    return report

def text_error_rates(ref_text, hyp_text, domain_config: Optional[DomainConfig] = None, normalize: bool = True, use_sandhi: bool = True) -> dict[str, dict[str, float | int]]:
    """
    Calculate error rates from raw text.

    Args:
        ref_text: Reference text
        hyp_text: Hypothesis text
        domain_config: Domain configuration (None for no domain)
        normalize: If True, apply normalization for matching (default: True)

    Returns:
        Dictionary with error rates for each category
    """
    t1, g1 = domain_aware_tokenizer(ref_text, domain_config)
    t2, g2 = domain_aware_tokenizer(hyp_text, domain_config)
    aligned_ref, aligned_hyp, _ = align_arrays(t1, g1, t2, g2, use_sandhi=use_sandhi)
    return token_error_rates(aligned_ref, aligned_hyp, domain_config, normalize)