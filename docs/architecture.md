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

## Quick example

End-to-end, with the high-level API:

```python
from scribe import text_error_rates, DomainConfig

ref = "charged u/s 302 IPC on 22.05.2023"
hyp = "charged u/s 303 IPC on 22/05/2023"

report = text_error_rates(ref, hyp, DomainConfig.legal())
print(f"WER:   {report['WORD']['error_rate']:.2%}")    # 0.00% — words match
print(f"LER:   {report['LEGAL']['error_rate']:.2%}")   # 0.00% — u/s, IPC shielded
print(f"NER:   {report['NUMERAL']['error_rate']:.2%}") # 16.67% — 302 → 303
                                                       # (date is normalized away)
```

The same flow, stage by stage, when you need finer control:

```python
from scribe import (
    DomainConfig, domain_aware_tokenizer, align_arrays,
    token_error_rates, token_error_details,
)

domain = DomainConfig.legal()

# 1. tokenize each side
t1, g1 = domain_aware_tokenizer(ref, domain)   # tokens, tags
t2, g2 = domain_aware_tokenizer(hyp, domain)

# 2. align (Needleman-Wunsch with sandhi/category-aware scoring)
aligned_ref, aligned_hyp, _ = align_arrays(t1, g1, t2, g2)

# 3. measure (rates and per-token error records)
rates   = token_error_rates(aligned_ref, aligned_hyp, domain)
details = token_error_details(aligned_ref, aligned_hyp, domain)
# details: [{"error_type": "substitution", "category": "NUMERAL",
#            "ref_token": "302", "hyp_token": "303"}, ...]
```

For batch evaluation across a JSONL dataset, see
[batch-processing.md](batch-processing.md).

## Module map

| Module | Owns | Key callables |
|---|---|---|
| `tokenize.py` | Splitting text into tagged tokens; date / time / currency detection | `domain_aware_tokenizer` |
| `domain_config.py` | Loading and applying domain-shielding patterns | `DomainConfig`, `.legal()` / `.medical()` / `.technical()`, `.from_file()` |
| `normalize.py` | Canonicalising date / currency / numeral surface forms before comparison | `normalize_token`, `normalize_date`, `normalize_currency` |
| `align.py` | Modified Needleman–Wunsch with token-type-aware scoring; sandhi merge / split detection | `align_arrays`, `DEFAULT_WEIGHTS` |
| `measure.py` | Per-sample error rates and per-token error records | `text_error_rates`, `token_error_rates`, `text_error_details` |
| `measure_batch.py` | JSONL ingestion, per-sample running, per-dataset & overall aggregation | `compute_sample_errors`, `compute_aggregate_metrics`, `aggregate_error_details` |
| `analysis.py` | Category contributions, frequent substitutions / deletions / insertions / sandhi merges / sandhi splits, Token Error Rate (TER) | `compute_error_summary`, `compute_category_contributions`, `compute_frequent_sandhi_merges`, `compute_frequent_sandhi_splits` |
| `reporting.py` | Formatters shared by the CLI and Streamlit UI | `format_metrics_dict`, `format_contribution_table`, `format_alignment_table` |
| `charts.py` | matplotlib chart generation (optional `[charts]` extra) | `category_breakdown_chart` |
| `visualizer/` | Streamlit app and `scribe-visualizer` console script (optional `[visualizer]` extra) | `app.py`, `__main__.py` |
| `constants.py` | Category names and helpers | `CAT_WORD`, `CAT_NUMERAL`, `get_categories(domain_config)` |

## Stage-by-stage examples

Small, runnable snippets for the parts of the pipeline you most often
reach into directly.

### Tokenize

```python
from scribe import domain_aware_tokenizer, DomainConfig

tokens, tags = domain_aware_tokenizer("filed u/s 302 IPC", DomainConfig.legal())
# tokens: ['filed', 'u/s',  '302',     'IPC']
# tags:   ['WORD',  'LEGAL', 'NUMERAL', 'LEGAL']
```

Both `u/s` and `IPC` are LEGAL — they're tracked under LER, not WER, so
a misrecognised legal abbreviation doesn't inflate your general word
error rate. `u/s` also stays atomic instead of being split on `/`.

### Normalize

```python
from scribe.normalize import normalize_token

normalize_token("22.05.2023", "NUMERAL")  # '22-05-2023'  (canonical date)
normalize_token("10,500",     "NUMERAL")  # '10500'        (commas stripped)
normalize_token("೧೫.೦೫.೨೦೨೩", "NUMERAL") # '15-05-2023'  (Kannada → Arabic)
```

Normalization runs *post-alignment* on each surviving substitution pair:
if both sides normalize to the same string, the pair is reclassified
from "sub" to "correct". Enabled by default; opt out with
`text_error_rates(..., normalize=False)`.

### Align (sandhi-aware)

```python
from scribe import align_arrays, domain_aware_tokenizer

t1, g1 = domain_aware_tokenizer("ഇന്ന് അല്ലെങ്കിൽ", None)
t2, g2 = domain_aware_tokenizer("ഇന്നല്ലെങ്കിൽ",     None)
ref, hyp, _ = align_arrays(t1, g1, t2, g2)
# ref: [('MERGE:ഇന്ന് അല്ലെങ്കിൽ', 'WORD')]
# hyp: [('ഇന്നല്ലെങ്കിൽ',          'WORD')]
```

The aligner tags merge / split events with `MERGE:` / `SPLIT:` prefixes
on the affected side. Downstream, `measure.py` reads those prefixes and
records the event as a *sandhi correction* — not an error.

### Measure — rates and per-token records

```python
from scribe import text_error_rates, text_error_details

rates = text_error_rates("alpha beta gamma", "alpha delta epsilon", None)
# rates['WORD']: {'error_rate': 0.667, 'substitutions': 2, 'correct': 1,
#                 'total_ref': 3, 'sandhi_hits': 0, ...}

details = text_error_details("alpha beta gamma", "alpha delta epsilon", None)
# [{'error_type': 'substitution', 'category': 'WORD',
#   'ref_token': 'beta',  'hyp_token': 'delta'},
#  {'error_type': 'substitution', 'category': 'WORD',
#   'ref_token': 'gamma', 'hyp_token': 'epsilon'}]
```

`text_error_details` is the input to the frequent-error analysis below.
For a sandhi event it emits `{"error_type": "sandhi_merge"|"sandhi_split", ...}`
records (no contribution to sub / ins / del counters).

### Analyse — frequent errors and sandhi events

```python
from scribe import (
    text_error_details, text_error_rates,
    compute_error_summary, compute_aggregate_metrics,
    format_frequent_errors_table,
)

pairs = [
    ("ഇന്ന് അല്ലെങ്കിൽ നാളെ", "ഇന്നല്ലെങ്കിൽ നാളെ"),  # merge
    ("ഇന്ന് അല്ലെങ്കിൽ പിന്നെ", "ഇന്നല്ലെങ്കിൽ പിന്നെ"), # merge (repeat)
    ("നാളെ വരാം",            "നാളെ പോകാം"),            # plain sub
]
details = []
samples = []
for r, h in pairs:
    details.extend(text_error_details(r, h, None))
    samples.append({"detailed_report": text_error_rates(r, h, None),
                    "source_dataset": "demo"})

agg = compute_aggregate_metrics(samples)
summary = compute_error_summary(agg["overall"], details, top_n=5)

merge_rows = format_frequent_errors_table(
    summary["frequent_sandhi_merges"], "sandhi_merge", 5
)
# [{'Rank': 1, 'Category': 'WORD', 'Reference': 'ഇന്ന് അല്ലെങ്കിൽ',
#   'Hypothesis': 'ഇന്നല്ലെങ്കിൽ', 'Count': 2}]
```

`compute_error_summary` returns a single dict with all per-category
contributions, top-N substitutions / deletions / insertions, and the
two new top-N sandhi tables (`frequent_sandhi_merges`,
`frequent_sandhi_splits`). The CLI (`examples/batch_evaluate.py
--analysis`) and the Streamlit visualizer both render straight from
this dict.

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
- **Sandhi awareness** — the alignment step detects when ASR has merged or split adjacent words (common in agglutinative Indic languages) and counts those separately from substitutions. The detected pairs are also surfaced as their own frequent-event tables (`frequent_sandhi_merges`, `frequent_sandhi_splits`) alongside the substitution / deletion / insertion tables, so recurring sandhi patterns are diagnosable at a dataset level. Implemented in `align.py` (detection) + `analysis.py` (aggregation). Disable with `use_sandhi=False` for non-agglutinative languages.
- **Two error-rate views per category** — `error_rate` (errors / category_ref) for in-isolation accuracy, `combined_total` (errors / total_ref) for contribution to overall TER. The Streamlit UI shows both side-by-side.

## Glossary

Quick reference for terms used throughout the codebase, docs, and the
SCRIBE paper. Each entry points at the module that owns the concept.

- **Sandhi** — in agglutinative Indic languages, the phonological merging of adjacent words at morpheme boundaries (e.g. `ഇന്ന്` + `അല്ലെങ്കിൽ` → `ഇന്നല്ലെങ്കിൽ`). ASR systems often produce one form when the reference uses the other.
- **Sandhi correction** — an alignment hit where one reference token spans two hypothesis tokens (split) or two reference tokens collapse into one hypothesis token (merge). Tracked separately from substitutions because the underlying word identity is preserved. See `align.py`.
- **Combined denominator** — the total reference-token count across all categories, used as the divisor for every category's error rate. Prevents 1-error-in-1-token categories from reading as 100%. See `measure.py::token_error_rates`.
- **Domain shielding** — extracting domain-critical multi-character tokens (e.g. `u/s`, `r/w`, `PW1`) before general tokenization so they stay atomic and aren't split on punctuation. See `tokenize.py` + `domain_config.py`.
- **TER (Token Error Rate)** — the headline overall error rate: `(sub + ins + del) / total_ref`, where `total_ref` is the combined-denominator count of reference tokens across all categories. Equivalently, TER is the sum of every category's `error_rate` (since they share the same denominator).
- **Accuracy** — `total_correct / total_ref`, the fraction of reference tokens recovered exactly. **Accuracy and TER are independent quantities** — they do not sum to 100% in general because (a) insertions appear in the TER numerator but not in the reference token count, and (b) sandhi hits count as correct but consume two reference tokens per single hypothesis token. Both numbers are reported side-by-side in the CLI and visualizer.
- **Error rate vs Impact on Total** — every category exposes two numbers. `error_rate = (sub + ins + del) / category_ref` answers "how accurate is the model on this category in isolation". `Impact on Total = (sub + ins + del) / total_ref` answers "how much does this category contribute to TER". Across categories the *Impact on Total* values sum to TER.
- **Gap penalty / DP weight** — in the modified Needleman–Wunsch alignment, the cost of inserting a gap on either side. Tuned per-category in `DEFAULT_WEIGHTS` (align.py); punctuation gaps are cheaper than word or domain gaps because punctuation errors carry less semantic weight.
