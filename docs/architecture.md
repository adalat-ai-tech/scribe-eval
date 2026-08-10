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
| measure → aggregate | per-sample report `{LEXICAL: {...}, NUMERAL: {...}, ...}` |
| aggregate → report | `{"overall": ..., "by_dataset": {...}}` |

## Quick example

End-to-end, with the high-level API:

```python
from scribe import text_error_rates, DomainConfig

ref = "charged u/s 302 IPC on 22.05.2023"
hyp = "charged u/s 303 IPC on 22/05/2023"

report = text_error_rates(ref, hyp, DomainConfig.legal())
print(f"ER_LEX:    {report['LEXICAL']['error_rate']:.2%}")    # 0.00% — words match
print(f"ER_DOMAIN: {report['LEGAL']['error_rate']:.2%}")   # 0.00% — u/s, IPC shielded
print(f"ER_NUM:    {report['NUMERAL']['error_rate']:.2%}") # 16.67% — 302 → 303
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
details = token_error_details(aligned_ref, aligned_hyp)
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
| `measure.py` | Per-sample error rates, per-token error records, character error rate | `text_error_rates`, `token_error_rates`, `text_error_details`, `compute_cer_scribe` |
| `measure_batch.py` | JSONL ingestion, per-sample running, per-dataset & overall aggregation | `compute_sample_errors`, `compute_aggregate_metrics`, `aggregate_error_details` |
| `analysis.py` | Category contributions, frequent substitutions / deletions / insertions / sandhi merges / sandhi splits, the composite WER_SCRIBE | `compute_error_summary`, `compute_category_contributions`, `compute_frequent_sandhi_merges`, `compute_frequent_sandhi_splits` |
| `reporting.py` | Formatters shared by the CLI and Streamlit UI | `format_metrics_dict`, `format_contribution_table`, `format_alignment_table` |
| `charts.py` | matplotlib chart generation (optional `[charts]` extra) | `category_breakdown_chart` |
| `visualizer/` | Streamlit app and `scribe-visualizer` console script (optional `[visualizer]` extra) | `app.py`, `__main__.py` |
| `constants.py` | Category names and helpers | `CAT_LEXICAL`, `CAT_NUMERAL`, `get_categories(domain_config)` |

## Stage-by-stage examples

Small, runnable snippets for the parts of the pipeline you most often
reach into directly.

### Tokenize

```python
from scribe import domain_aware_tokenizer, DomainConfig

tokens, tags = domain_aware_tokenizer("filed u/s 302 IPC", DomainConfig.legal())
# tokens: ['filed', 'u/s',  '302',     'IPC']
# tags:   ['LEXICAL',  'LEGAL', 'NUMERAL', 'LEGAL']
```

Both `u/s` and `IPC` are LEGAL — they're tracked under the domain error rate (ER_DOMAIN), not ER_LEX, so
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
# ref: [('MERGE:ഇന്ന് അല്ലെങ്കിൽ', 'LEXICAL')]
# hyp: [('ഇന്നല്ലെങ്കിൽ',          'LEXICAL')]
```

The aligner tags merge / split events with `MERGE:` / `SPLIT:` prefixes
on the affected side. Downstream, `measure.py` reads those prefixes and
records the event as a *sandhi correction* — not an error.

### Sandhi detection: scope and limitations

Sandhi detection is an **orthographic heuristic, not a linguistic
analysis**. It consults no grammar, lexicon, or sandhi rules. When one
reference token could correspond to two hypothesis tokens (or the
reverse), it anchors the outer characters — the merged word must start
like the first word and end like the second — and accepts the pair as a
sandhi merge/split if the characters at the junction differ by at most
`sandhi_char_tolerance` (default 2, in `DEFAULT_WEIGHTS`). That bounded
character difference at the boundary is the entire test. Detection is
limited to **two-word events**: a merge or split spanning three or more
words is never proposed and scores as ordinary errors.

**Validation scope.** The heuristic is tuned against real Malayalam,
Kannada, and Hindi ASR evaluation sets, where accepted events are
overwhelmingly genuine (see the examples in the README). Its leniency
is a deliberate trade: on an internal benchmark of 48 Malayalam legal
dictations (private data) it recovers 3.0 percentage points of
WER_SCRIBE across 377 events. A
human annotation of accepted events (valid vs invalid) is planned;
until then the false-positive rate is not precisely quantified.

**Known false positives — and why.** The tolerance counts *how many*
characters changed at the junction, never *which kind*. Genuine vowel
sandhi can eliminate the junction entirely (ഇന്ന് + അല്ലെങ്കിൽ →
ഇന്നല്ലെങ്കിൽ: the chandrakkala and the vowel merge away — 2 characters,
correctly accepted). But a lost consonant produces the same arithmetic:

- `കണ്ട് പറഞ്ഞു` ("saw and told") → `കണ്ടറഞ്ഞു` is accepted as a merge,
  though the consonant പ simply vanished — a real deletion, and the
  merged form is not a word (a genuine compound keeps it:
  `കണ്ടുപറഞ്ഞു`). The virama and the പ together are two characters,
  exactly at the tolerance. The same shape occurs in real data:
  `ജസ് സോളി` → `ജസോളി`, a name losing its സ (a genuine merge would
  geminate: `ജസ്സോളി`).
- From real evaluation data: `പ്രതി ഷിജിലിനെ` → `പ്രതിജിലിനെ` — a
  witness name losing its ഷി is forgiven as sandhi (flagged pending the
  annotation effort).
- The same hole exists in any script: `ab cd` → `ad` is accepted in
  Latin text.

Distinguishing these cases from genuine elision requires knowing that a
virama+vowel junction may vanish while a consonant may not — character
*class* knowledge the heuristic deliberately does not have.

**Tolerance in practice.** Every genuine sandhi examined in the
Malayalam, Kannada, and Hindi evaluation data changes the junction by
at most two characters (vowel elision, gemination), so the default
tolerance has not been observed to reject a real sandhi.
`sandhi_char_tolerance` is configurable should another language need a
wider bound.

**Consequences and how to audit.**

- A false-positive sandhi converts real errors into "correct + 1 sandhi
  hit", so WER_SCRIBE *underestimates*. CER_SCRIBE involves no
  alignment and is immune — the divergence pattern documented below
  (WER_SCRIBE ≈ 0, CER_SCRIBE > 0, sandhi hits > 0) doubles as the
  detection signal for suspect sandhi counts.
- The frequent sandhi merge/split tables (CLI `--analysis`, visualizer
  sub-tabs) show the **top-N** most frequent accepted pairs
  (default 10) — raise `--top-n` / the visualizer slider when auditing,
  since rare pairs are the suspicious ones. For an exhaustive list,
  every accepted event is a `sandhi_merge`/`sandhi_split` record in the
  per-token error details (`collect_error_details=True`,
  `aggregate_error_details()`).
- `use_sandhi=False` disables detection entirely;
  `sandhi_char_tolerance` tightens it.

A stricter, linguistically informed junction check exists in prototype
and is under validation across the scheduled languages' scripts; it will
land after the per-language review rather than ship half-validated.

### Measure — rates and per-token records

```python
from scribe import text_error_rates, text_error_details

rates = text_error_rates("alpha beta gamma", "alpha delta epsilon", None)
# rates['LEXICAL']: {'error_rate': 0.667, 'substitutions': 2, 'correct': 1,
#                 'total_ref': 3, 'sandhi_hits': 0, ...}

details = text_error_details("alpha beta gamma", "alpha delta epsilon", None)
# [{'error_type': 'substitution', 'category': 'LEXICAL',
#   'ref_token': 'beta',  'hyp_token': 'delta'},
#  {'error_type': 'substitution', 'category': 'LEXICAL',
#   'ref_token': 'gamma', 'hyp_token': 'epsilon'}]
```

`text_error_details` is the input to the frequent-error analysis below.
For a sandhi event it emits `{"error_type": "sandhi_merge"|"sandhi_split", ...}`
records (no contribution to sub / ins / del counters).

### CER_SCRIBE vs a raw CER — worked examples

CER_SCRIBE measures the *canonical tokenized surface*, not the raw
string. Even with `normalize=False`, that produces different numbers
from a raw character error rate such as jiwer's. Two verified cases:

**1. Whitespace runs cost nothing in CER_SCRIBE** — tokenization
collapses them, so spacing noise is not treated as a recognition error:

```python
ref, hyp = "the  case   closed", "the case closed"

jiwer.cer(ref, hyp)                       # 0.1667 — 3 extra spaces counted
compute_cer_scribe(ref, hyp, normalize=False)
# compares "the case closed" vs "the case closed"  ->  0.0
```

**2. Punctuation becomes its own token, changing both numerator and
denominator** — SCRIBE reconstructs `"closed."` as `"closed ."`:

```python
ref, hyp = "the case closed.", "the case closed"

jiwer.cer(ref, hyp)
# compares "the case closed." vs "the case closed"
# 1 edit / 16 chars = 0.0625

compute_cer_scribe(ref, hyp, normalize=False)
# compares "the case closed ." vs "the case closed"
# 2 edits (space + period) / 17 chars = 0.1176
```

Word-medial punctuation is preserved by the tokenizer (`u/s`,
`O'Connor`), so such tokens compare identically in both metrics. On
realistic batches the two CERs track closely (the bundled sample file:
jiwer ≈ 3.3%, raw CER_SCRIBE ≈ 3.5%); the gap grows with spacing noise
and punctuation-heavy text. With `normalize=True` (the default),
CER_SCRIBE additionally stops charging for date/currency format
variants — that difference is by design, not drift.

### Reading WER_SCRIBE and CER_SCRIBE together

The two metrics measure the same predictions at different granularities,
and their *disagreement* is diagnostic:

| Pattern | Typical cause |
|---|---|
| WER_SCRIBE ≈ 0, CER_SCRIBE > 0, sandhi hits > 0 | Segmentation differences: token-level matching forgives merges/splits as sandhi, while the characters record each junction. Real example from the bundled sample file — one dataset scores WER_SCRIBE 0.00% with CER_SCRIBE 3.09% and 1 sandhi match. |
| WER_SCRIBE high, CER_SCRIBE low | Near-miss recognition: many tokens each wrong by a character or two — every one counts fully at token level but barely at character level. Common for very long Indic words. |
| WER_SCRIBE ≈ CER_SCRIBE, both high | Gross errors: whole words substituted, deleted, or hallucinated. |

A model improving CER_SCRIBE while WER_SCRIBE stalls is getting the
sounds right but not the word forms; the reverse suggests token-level
luck on top of noisy characters. Report both.

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
# [{'Rank': 1, 'Category': 'LEXICAL', 'Reference': 'ഇന്ന് അല്ലെങ്കിൽ',
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
- **Two error-rate views per category** — `error_rate` (errors / category_ref) for in-isolation accuracy, `combined_total` (errors / total_ref) for contribution to the overall WER_SCRIBE. The Streamlit UI shows both side-by-side.

## Glossary

Quick reference for terms used throughout the codebase, docs, and the
SCRIBE paper. Each entry points at the module that owns the concept.

- **Sandhi** — in agglutinative Indic languages, the phonological merging of adjacent words at morpheme boundaries (e.g. `ഇന്ന്` + `അല്ലെങ്കിൽ` → `ഇന്നല്ലെങ്കിൽ`). ASR systems often produce one form when the reference uses the other.
- **Sandhi correction** — an alignment hit where one reference token spans two hypothesis tokens (split) or two reference tokens collapse into one hypothesis token (merge). Tracked separately from substitutions because the underlying word identity is preserved. See `align.py`.
- **Combined denominator** — the total reference-token count across all categories, used as the divisor for every category's error rate. Prevents 1-error-in-1-token categories from reading as 100%. See `measure.py::token_error_rates`.
- **Domain shielding** — extracting domain-critical multi-character tokens (e.g. `u/s`, `r/w`, `PW1`) before general tokenization so they stay atomic and aren't split on punctuation. See `tokenize.py` + `domain_config.py`.
- **WER_SCRIBE** — the headline composite error rate: `(sub + ins + del) / total_ref`, where `total_ref` is the combined-denominator count of reference tokens across all categories (lexical, domain, numeral, punctuation). Equivalently, WER_SCRIBE is the sum of every category's `error_rate` (since they share the same denominator). Not comparable to a standard word-level WER, which ignores token categories.
- **CER_SCRIBE** — character edits over reference characters, computed on *normalized* token streams (tokenize, canonicalize each token, rejoin, one Levenshtein pass). Format variants (dates, currency) contribute zero character errors, unlike a raw CER. No alignment is involved, so sandhi detection cannot affect it — a merged/split word costs only its few junction characters, which is CER's natural robustness to agglutination. Even with `normalize=False`, CER_SCRIBE differs from a raw CER (e.g. jiwer's): it measures the *canonical tokenized surface* — whitespace runs collapse to single spaces (spacing noise costs nothing), and punctuation splits into its own space-separated tokens (a missing period costs its space too, over a slightly larger denominator).
- **Accuracy** — `total_correct / total_ref`, the fraction of reference tokens recovered exactly. **Accuracy and WER_SCRIBE are independent quantities** — they do not sum to 100% in general because (a) insertions appear in the WER_SCRIBE numerator but not in the reference token count, and (b) sandhi hits count as correct but consume two reference tokens per single hypothesis token. Both numbers are reported side-by-side in the CLI and visualizer.
- **Error rate vs Impact on Total** — every category exposes two numbers. `error_rate = (sub + ins + del) / category_ref` answers "how accurate is the model on this category in isolation". `Impact on Total = (sub + ins + del) / total_ref` answers "how much does this category contribute to WER_SCRIBE". Across categories the *Impact on Total* values sum to WER_SCRIBE.
- **Gap penalty / DP weight** — in the modified Needleman–Wunsch alignment, the cost of inserting a gap on either side. Tuned per-category in `DEFAULT_WEIGHTS` (align.py); punctuation gaps are cheaper than word or domain gaps because punctuation errors carry less semantic weight.
