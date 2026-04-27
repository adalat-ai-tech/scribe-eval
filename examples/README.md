# scribe-eval examples

Each script is runnable with `uv run examples/<script>.py` from the repo
root. They exercise the public library API on real Indic and English
inputs.

| Script | Demonstrates | Public API |
|---|---|---|
| [`text_alignment.py`](text_alignment.py) | Side-by-side alignment for arbitrary text pairs (Malayalam sandhi, Kannada spelled-out numerals, English) | `domain_aware_tokenizer`, `align_arrays` |
| [`error_report.py`](error_report.py) | Single-sample analog of `batch_evaluate.py --analysis` — token-by-token alignment plus per-category breakdown for one `(ref, hyp)` pair | `text_error_rates`, `compute_error_summary`, `format_contribution_table` |
| [`custom_domain_file.py`](custom_domain_file.py) | Three ways to configure a domain — bundled factory, `from_file()`, inline | `DomainConfig`, `DomainConfig.from_file` |
| [`batch_evaluate.py`](batch_evaluate.py) | Full batch CLI: JSONL in, summary + analysis + charts out | `compute_sample_errors`, `compute_aggregate_metrics`, `compute_error_summary` |

## Bundled data

| File | Used by | Notes |
|---|---|---|
| `predictions.jsonl` | `batch_evaluate.py` (default input) | 8 small Indic ASR datasets — runs end-to-end with no extra setup |
| `sample_legal.txt` | `custom_domain_file.py` (Approach 2) | Demo legal-domain config showing the file format |

## Common invocations

```bash
# Quick alignment demo (4 multilingual pairs)
uv run examples/text_alignment.py

# One-pair detailed report
uv run examples/error_report.py "ref text" "hyp text"

# Domain-config patterns
uv run examples/custom_domain_file.py

# Batch evaluation (default sample data)
uv run examples/batch_evaluate.py

# Batch evaluation with detailed analysis and chart
uv run examples/batch_evaluate.py --analysis --chart --top-n 15
```

See [`docs/batch-processing.md`](../docs/batch-processing.md) for all
`batch_evaluate.py` flags, and
[`docs/domain-configuration.md`](../docs/domain-configuration.md) for
the domain-config file format.
