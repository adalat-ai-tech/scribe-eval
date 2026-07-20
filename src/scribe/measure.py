from typing import Optional

from .align import align_arrays
from .constants import calculate_combined_total, get_categories, init_stat_dict
from .domain_config import DomainConfig
from .tokenize import domain_aware_tokenizer


def token_error_rates(
    aligned_ref,
    aligned_hyp,
    domain_config: Optional[DomainConfig] = None,
    normalize: bool = True,
) -> dict[str, dict[str, float | int]]:
    """
    Calculate error rates from aligned tokens.

    Sandhi handling is decided at alignment time: this function counts
    whatever MERGE:/SPLIT: markers align_arrays() emitted. To disable
    sandhi detection, pass use_sandhi=False to align_arrays() (or to the
    text_error_rates() end-to-end pipeline).

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
        if r_tag not in stats:
            continue
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
            "combined_total": combined_total,  # Store for transparency
        }

    return report


def token_error_details(
    aligned_ref,
    aligned_hyp,
    domain_config: Optional[DomainConfig] = None,
    normalize: bool = True,
) -> list[dict]:
    """
    Extract individual token-level error records from aligned tokens.

    Walks the same aligned pairs as token_error_rates() but records each
    error or sandhi correction as a structured dict instead of just counting.
    Correct matches are excluded.

    Args:
        aligned_ref: list of (text, tag) tuples
        aligned_hyp: list of (text, tag) tuples
        domain_config: Domain configuration (None for no domain)
        normalize: If True, check normalized equality for matches

    Returns:
        List of error record dicts. Each dict has:
            - "error_type": "substitution" | "insertion" | "deletion"
                            | "sandhi_merge" | "sandhi_split"
            - "category": the token category (WORD, PUNCT, NUMERAL, etc.)
            - "ref_token": the reference token text (None for insertions;
                           "word1 word2" for sandhi_merge)
            - "hyp_token": the hypothesis token text (None for deletions;
                           "word1 word2" for sandhi_split)
    """
    categories = set(get_categories(domain_config))
    errors = []

    for (r_text, r_tag), (h_text, h_tag) in zip(aligned_ref, aligned_hyp):
        # 1. Handle Insertions (Gap in Reference)
        if r_text == "**":
            if h_tag in categories:
                errors.append(
                    {
                        "error_type": "insertion",
                        "category": h_tag,
                        "ref_token": None,
                        "hyp_token": h_text,
                    }
                )
            continue

        # Skip unknown reference tags
        if r_tag not in categories:
            continue

        # 2. Handle Sandhi (Corrected Matches) — record them as their own type
        if "MERGE:" in r_text:
            errors.append(
                {
                    "error_type": "sandhi_merge",
                    "category": r_tag,
                    "ref_token": r_text[len("MERGE:") :],
                    "hyp_token": h_text,
                }
            )
            continue

        if "SPLIT:" in h_text:
            errors.append(
                {
                    "error_type": "sandhi_split",
                    "category": r_tag,
                    "ref_token": r_text,
                    "hyp_token": h_text[len("SPLIT:") :],
                }
            )
            continue

        # 3. Standard Logic
        if h_text == "**":
            errors.append(
                {
                    "error_type": "deletion",
                    "category": r_tag,
                    "ref_token": r_text,
                    "hyp_token": None,
                }
            )
        elif r_text == h_text:
            pass  # Correct match
        else:
            # Check normalization
            if normalize:
                from .normalize import normalize_token

                r_normalized = normalize_token(r_text, r_tag)
                h_normalized = normalize_token(h_text, h_tag)
                if r_normalized == h_normalized:
                    continue  # Normalized match — not an error

            errors.append(
                {
                    "error_type": "substitution",
                    "category": r_tag,
                    "ref_token": r_text,
                    "hyp_token": h_text,
                }
            )

    return errors


def text_error_details(
    ref_text,
    hyp_text,
    domain_config: Optional[DomainConfig] = None,
    normalize: bool = True,
    use_sandhi: bool = True,
) -> list[dict]:
    """
    Extract token-level error records from raw text.

    End-to-end: tokenize -> align -> extract error details.

    Args:
        ref_text: Reference text
        hyp_text: Hypothesis text
        domain_config: Domain configuration (None for no domain)
        normalize: If True, apply normalization for matching
        use_sandhi: If True, detect sandhi splits/merges

    Returns:
        List of error record dicts (see token_error_details)
    """
    t1, g1 = domain_aware_tokenizer(ref_text, domain_config)
    t2, g2 = domain_aware_tokenizer(hyp_text, domain_config)
    aligned_ref, aligned_hyp, _ = align_arrays(t1, g1, t2, g2, use_sandhi=use_sandhi)
    return token_error_details(aligned_ref, aligned_hyp, domain_config, normalize)


def text_error_rates(
    ref_text,
    hyp_text,
    domain_config: Optional[DomainConfig] = None,
    normalize: bool = True,
    use_sandhi: bool = True,
) -> dict[str, dict[str, float | int]]:
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
