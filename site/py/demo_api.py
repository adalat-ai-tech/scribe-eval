"""Single-sample evaluation API for the SCRIBE demo page.

Runs identically in CPython (CI showcase baking via
``scripts/generate_showcase_data.py``, pytest) and in Pyodide (the live
demo). All metric logic is delegated to scribe — this module only
assembles a JSON-serializable dict for the page's renderers, mirroring
the visualizer's ``render_analysis`` (src/scribe/visualizer/app.py).
"""

import json

from scribe import (
    DomainConfig,
    align_arrays,
    compute_category_contributions,
    compute_cer_scribe,
    domain_aware_tokenizer,
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


def evaluate_single(
    ref: str,
    hyp: str,
    domain_name: str = "none",
    normalize: bool = True,
    use_sandhi: bool = True,
) -> dict:
    """Evaluate one ref/hyp pair; return alignment rows, metric tiles,
    category chips, and the contribution table as plain data."""
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
