# Architecture

scribe-eval is a five-stage pipeline. Each stage is a module under
`src/scribe/`. Use the high-level API (`text_error_rates`) to run the
whole pipeline, or import individual stages for custom flows.

## Pipeline

```
raw text  ──▶  tokenize  ──▶  align  ──▶  measure  ──▶  aggregate  ──▶  report
              (per side)    (paired)     (per sample)   (across       (CLI / UI)
                                                         samples)
```

| Arrow | Payload |
|---|---|
| tokenize → align | `(tokens, tags, normalized_tokens)` per side |
| align → measure | aligned `[(text, tag), ...]` pairs (gaps as `("**", "GAP")`) |
| measure → aggregate | per-sample report `{WORD: {...}, NUMERAL: {...}, ...}` |
| aggregate → report | `{"overall": ..., "by_dataset": {...}}` |

## Module map

| Module | Owns | Key callables |
|---|---|---|
| `tokenize.py` | Splitting text into tagged tokens; date / time / currency detection | `domain_aware_tokenizer` |
| `domain_config.py` | Loading and applying domain-shielding patterns | `DomainConfig`, `.legal()` / `.medical()` / `.technical()`, `.from_file()` |
| `normalize.py` | Canonicalising date / currency / numeral surface forms before comparison | `normalize_token`, `normalize_date`, `normalize_currency` |
| `align.py` | Modified Needleman–Wunsch with token-type-aware scoring; sandhi merge / split detection | `align_arrays`, `DEFAULT_WEIGHTS` |
| `measure.py` | Per-sample error rates and per-token error records | `text_error_rates`, `token_error_rates`, `text_error_details` |
| `measure_batch.py` | JSONL ingestion, per-sample running, per-dataset & overall aggregation | `compute_sample_errors`, `compute_aggregate_metrics`, `aggregate_error_details` |
| `analysis.py` | Category contributions, frequent substitutions / deletions / insertions, total error rate | `compute_error_summary`, `compute_category_contributions` |
| `reporting.py` | Formatters shared by the CLI and Streamlit UI | `format_metrics_dict`, `format_contribution_table`, `format_alignment_table` |
| `charts.py` | matplotlib chart generation (optional `[charts]` extra) | `category_breakdown_chart` |
| `visualizer/` | Streamlit app and `scribe-visualizer` console script (optional `[visualizer]` extra) | `app.py`, `__main__.py` |
| `constants.py` | Category names and helpers | `CAT_WORD`, `CAT_NUMERAL`, `get_categories(domain_config)` |

## Where to make a change

| You want to... | Touch |
|---|---|
| Add a new bundled domain | `src/scribe/config/<name>_terms.txt` + a factory method in `domain_config.py` |
| Recognise a new numeral form (e.g. ISO-8601 dates) | The numeral regex in `tokenize.py`, plus a matching `normalize_*` in `normalize.py` |
| Tweak alignment scoring | `DEFAULT_WEIGHTS` in `align.py` |
| Add a new aggregate metric | The math in `analysis.py`, the formatter in `reporting.py` |
| Add a CLI flag | `examples/batch_evaluate.py` — the CLI lives in `examples/`, not in the library |
| Add a UI element | `src/scribe/visualizer/app.py` |

## Tests mirror the pipeline

`tests/` has one file per module (`test_tokenize.py`, `test_align.py`,
`test_measure.py`, `test_normalize.py`, `test_measure_batch.py`,
`test_reporting.py`, `test_domain_config.py`), plus
`test_paper_cases.py` for end-to-end golden cases from the SCRIBE
paper. When you change a module, run its corresponding test file first.

## Key design decisions

- **Combined denominator** — error rates are `(category errors) / (total tokens across all categories)`, not `(category errors) / (category tokens)`. Stops sparse categories (e.g. 1 LEGAL error in 1 LEGAL token) reading as 100%. Implemented in `measure.py::token_error_rates`.
- **Domain shielding** — domain entities (`u/s`, `r/w`, `PW1`) are extracted *before* general tokenization so they stay atomic and are tracked under their own category. Implemented across `tokenize.py` + `domain_config.py`.
- **Sandhi awareness** — the alignment step detects when ASR has merged or split adjacent words (common in agglutinative Indic languages) and counts those separately from substitutions. Implemented in `align.py`. Disable with `use_sandhi=False` for non-agglutinative languages.
- **Two error-rate views per category** — `error_rate` (errors / category_ref) for in-isolation accuracy, `combined_total` (errors / total_ref) for contribution to overall TER. The Streamlit UI shows both side-by-side.

## Glossary

Quick reference for terms used throughout the codebase, docs, and the
SCRIBE paper. Each entry points at the module that owns the concept.

- **Sandhi** — in agglutinative Indic languages, the phonological merging of adjacent words at morpheme boundaries (e.g. `ഇന്ന്` + `അല്ലെങ്കിൽ` → `ഇന്നല്ലെങ്കിൽ`). ASR systems often produce one form when the reference uses the other.
- **Sandhi correction** — an alignment hit where one reference token spans two hypothesis tokens (split) or two reference tokens collapse into one hypothesis token (merge). Tracked separately from substitutions because the underlying word identity is preserved. See `align.py`.
- **Combined denominator** — the total reference-token count across all categories, used as the divisor for every category's error rate. Prevents 1-error-in-1-token categories from reading as 100%. See `measure.py::token_error_rates`.
- **Domain shielding** — extracting domain-critical multi-character tokens (e.g. `u/s`, `r/w`, `PW1`) before general tokenization so they stay atomic and aren't split on punctuation. See `tokenize.py` + `domain_config.py`.
- **TER (Total Error Rate)** — the headline overall error rate, equal to the sum of every category's `error_rate` (since they share the combined denominator). Reported alongside `Accuracy = 1 − TER` minus a small correction for sandhi hits.
- **Error rate vs Impact on Total** — every category exposes two numbers. `error_rate = (sub + ins + del) / category_ref` answers "how accurate is the model on this category in isolation". `Impact on Total = (sub + ins + del) / total_ref` answers "how much does this category contribute to TER". Across categories the *Impact on Total* values sum to TER.
- **Gap penalty / DP weight** — in the modified Needleman–Wunsch alignment, the cost of inserting a gap on either side. Tuned per-category in `DEFAULT_WEIGHTS` (align.py); punctuation gaps are cheaper than word or domain gaps because punctuation errors carry less semantic weight.
