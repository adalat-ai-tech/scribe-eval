"""Single-sample evaluation API for the SCRIBE demo page.

Runs identically in CPython (CI showcase baking via
``scripts/generate_showcase_data.py``, pytest) and in Pyodide (the live
demo). All metric logic is delegated to scribe — this module only
assembles a JSON-serializable dict for the page's renderers, mirroring
the visualizer's ``render_analysis`` (src/scribe/visualizer/app.py).
"""

import json

import Levenshtein

from scribe import (
    DomainConfig,
    align_arrays,
    compute_category_contributions,
    compute_cer_scribe,
    domain_aware_tokenizer,
    text_error_details,
    token_error_rates,
)
from scribe.reporting import (
    extract_error_rates,
    format_alignment_dict,
    format_category_chips,
    format_contribution_table,
)

_DOMAINS = {
    "legal": DomainConfig.legal,
    "medical": DomainConfig.medical,
    "technical": DomainConfig.technical,
}


def _word_alignment(ref_words: list, hyp_words: list) -> list:
    """Plain word-level Levenshtein alignment, as jiwer computes by default.

    Returns aligned rows using "**" for gap cells, the same convention as
    the visualizer's jiwer view.
    """
    n, m = len(ref_words), len(hyp_words)
    cost = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        cost[i][0] = i
    for j in range(m + 1):
        cost[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            diff = 0 if ref_words[i - 1] == hyp_words[j - 1] else 1
            cost[i][j] = min(cost[i - 1][j - 1] + diff, cost[i - 1][j] + 1, cost[i][j - 1] + 1)

    rows = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            diff = 0 if ref_words[i - 1] == hyp_words[j - 1] else 1
            if cost[i][j] == cost[i - 1][j - 1] + diff:
                kind = "correct" if diff == 0 else "substitution"
                rows.append(
                    {"ref_text": ref_words[i - 1], "hyp_text": hyp_words[j - 1], "error_type": kind}
                )
                i, j = i - 1, j - 1
                continue
        if i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            rows.append({"ref_text": ref_words[i - 1], "hyp_text": "**", "error_type": "deletion"})
            i -= 1
        else:
            rows.append({"ref_text": "**", "hyp_text": hyp_words[j - 1], "error_type": "insertion"})
            j -= 1
    rows.reverse()
    return rows


def plain_error_rates(ref: str, hyp: str) -> dict:
    """Standard word and character error rates with no transforms, the
    baseline the page sets against SCRIBE's metrics."""
    ref_words, hyp_words = ref.split(), hyp.split()
    alignment = _word_alignment(ref_words, hyp_words)
    counts = {
        t: sum(r["error_type"] == t for r in alignment)
        for t in ("substitution", "insertion", "deletion")
    }
    errors = sum(counts.values())
    return {
        "wer": errors / len(ref_words) if ref_words else float(bool(hyp_words)),
        "cer": Levenshtein.distance(ref, hyp) / len(ref) if ref else float(bool(hyp)),
        "subs": counts["substitution"],
        "ins": counts["insertion"],
        "dels": counts["deletion"],
        "alignment": alignment,
    }


def evaluate_single(
    ref: str,
    hyp: str,
    domain_name: str = "none",
    normalize: bool = True,
    use_sandhi: bool = True,
) -> dict:
    """Evaluate one ref/hyp pair; return alignment rows, metric tiles,
    category chips, the contribution table, error records and the plain
    WER baseline as plain data."""
    domain = _DOMAINS[domain_name]() if domain_name in _DOMAINS else None
    t1, g1 = domain_aware_tokenizer(ref, domain)
    t2, g2 = domain_aware_tokenizer(hyp, domain)
    a_ref, a_hyp, _ = align_arrays(t1, g1, t2, g2, use_sandhi=use_sandhi)
    report = token_error_rates(a_ref, a_hyp, domain, normalize)

    contributions = compute_category_contributions(report)
    rates = extract_error_rates(report)
    cer = compute_cer_scribe(ref, hyp, domain, normalize)

    total_correct = sum(c["correct"] for c in contributions.values())
    total_ref = sum(c["ref_tokens"] for c in contributions.values())
    domain_display = f"{domain.name.title()} Tokens" if domain else "Domain Tokens"

    return {
        "alignment": format_alignment_dict(a_ref, a_hyp, normalize),
        "tiles": {
            "wer_scribe": sum(c["error_rate"] for c in contributions.values()),
            "cer_scribe": cer["cer_scribe"],
            "accuracy": (total_correct / total_ref) if total_ref > 0 else 0.0,
            "sandhi_hits": rates["sandhi"],
        },
        "chips": format_category_chips(contributions, domain_display),
        "contribution": format_contribution_table(contributions),
        "errors": text_error_details(ref, hyp, domain, normalize, use_sandhi),
        "plain": plain_error_rates(ref, hyp),
    }


def evaluate_single_json(
    ref: str,
    hyp: str,
    domain_name: str = "none",
    normalize: bool = True,
    use_sandhi: bool = True,
) -> str:
    """Pyodide entry point: JSON string in/out avoids PyProxy conversion."""
    return json.dumps(
        evaluate_single(ref, hyp, domain_name, normalize, use_sandhi),
        ensure_ascii=False,
    )
