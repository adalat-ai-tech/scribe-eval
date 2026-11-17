# Batch Processing

scribe-eval supports processing multiple samples from a JSONL file and aggregating metrics overall and per group (per dataset, per speaker, or any other record field).

## Input Format

Each line in the JSONL file must have:

| Field | Default key | Description |
|---|---|---|
| Reference text | `text` | Ground truth transcription (NeMo manifest convention) |
| Hypothesis text | `pred_text` | ASR model output |
| Group field | `source_dataset` | Optional; the field whose value splits the per-group metrics. Any record field can be chosen with `group_by=` (`--group-by` on the CLI). Missing or empty values fall into `unknown`; when no record has the field (or `group_by=None`), everything is one `overall` group |

Example:

```jsonl
{"text": "charged u/s 302 IPC on 22.05.2023", "pred_text": "charged u/s 303 IPC on 22-05-2023", "source_dataset": "legal-dictation"}
{"text": "witness PW1 deposed before the court", "pred_text": "witness PW 1 deposed before court", "source_dataset": "legal-dictation"}
{"text": "എനിക്ക് അറിയാം", "pred_text": "എനിക്കറിയാം", "source_dataset": "malayalam-read"}
```

The Malayalam hypothesis merges a two-word compound; with sandhi detection
on it is counted as a Sandhi match, not as errors.

## Python API

### Basic batch evaluation

```python
from scribe import compute_sample_errors, compute_aggregate_metrics, DomainConfig

domain = DomainConfig.legal()

# Process JSONL file; optionally save per-sample details
results = compute_sample_errors(
    "predictions.jsonl",
    output_file="detailed_results.jsonl",
    domain_config=domain
)

# Aggregate across all samples
metrics = compute_aggregate_metrics(results)

# Overall metrics
print(metrics['overall']['LEXICAL']['error_rate'])
print(metrics['overall']['LEGAL']['error_rate'])

# Per-group metrics (one entry per source_dataset value by default)
for group, data in metrics['by_group'].items():
    print(f"{group}: ER_LEX={data['LEXICAL']['error_rate']:.2%}")

# Group by any other record field instead
by_speaker = compute_aggregate_metrics(
    compute_sample_errors("predictions.jsonl", group_by="speaker", domain_config=domain)
)
```

`group_by=` replaces the 0.1.x `source_dataset_field=` keyword, which has
been removed.

### In-memory evaluation (no file needed)

`evaluate_records()` is the core batch API — `compute_sample_errors()` is a
thin JSONL loader over it. Pass any iterable of dicts (parsed JSON, a
DataFrame's `to_dict("records")`, predictions generated inside a training
loop); input dicts are never mutated.

```python
from scribe import evaluate_records, compute_aggregate_metrics

records = [
    {"text": "charged u/s 302", "pred_text": "charged us 302"},
    {"text": "hearing on 22.05.2023", "pred_text": "hearing on 22.05.2023"},
]

results = evaluate_records(records, domain_config=DomainConfig.legal())
metrics = compute_aggregate_metrics(results)
```

### Bad input handling

Both entry points fail fast on bad data so a file problem cannot
silently distort metrics: a line that is not valid JSON, or a record
whose text fields are missing, null, or not strings, raises
`ValueError` naming the file and line number (`compute_sample_errors`)
or the record number (`evaluate_records`). Blank lines are not records
and are always skipped. Empty-string text is allowed — an empty
reference is a legitimate transcript (e.g. silence).

To tolerate dirty files instead, pass `skip_bad_records=True`: bad
lines/records are skipped with a warning each, and only the valid
records are evaluated.

```python
results = compute_sample_errors("dirty.jsonl", skip_bad_records=True)
```

### Parallel evaluation

Both `evaluate_records()` and `compute_sample_errors()` accept `workers=N`
to spread samples over a process pool — useful for large batches or long
dictation samples. Results are identical to sequential evaluation and stay
in input order. The CLI equivalent is `--workers N`.

```python
results = evaluate_records(records, workers=4)
```

### Error analysis (contributions + frequent errors)

```python
from scribe import (
    aggregate_error_details,
    compute_error_summary,
    format_contribution_table,
    format_frequent_errors_table,
)

# Enable per-token error tracking during batch run
results = compute_sample_errors(
    "predictions.jsonl",
    domain_config=domain,
    collect_error_details=True,
)

metrics = compute_aggregate_metrics(results)

# Flatten all token-level error records across samples
all_error_details = aggregate_error_details(results)

# Full analysis in one call
summary = compute_error_summary(metrics["overall"], all_error_details, top_n=10)
print(f"WER_SCRIBE: {summary['wer_scribe']:.2%}")
print(f"Accuracy: {summary['total_correct_pct']:.1f}%")

# Formatted tables for display
contrib_rows = format_contribution_table(summary["contributions"])
sub_rows   = format_frequent_errors_table(summary["frequent_substitutions"],   "substitution",  top_n=10)
del_rows   = format_frequent_errors_table(summary["frequent_deletions"],       "deletion",      top_n=10)
ins_rows   = format_frequent_errors_table(summary["frequent_insertions"],      "insertion",     top_n=10)
merge_rows = format_frequent_errors_table(summary["frequent_sandhi_merges"],   "sandhi_merge",  top_n=10)
split_rows = format_frequent_errors_table(summary["frequent_sandhi_splits"],   "sandhi_split",  top_n=10)
```

Sandhi merges / splits surface only when `use_sandhi=True` (the default)
and the language has agglutinative compounds. For non-agglutinative
languages (English, Hindi, etc.) the two tables will be empty.

### Chart

`category_breakdown_chart()` draws the per-category report card that
`scribe-batch --chart` saves (matplotlib ships with the package):

```python
from scribe.charts import category_breakdown_chart

category_breakdown_chart(summary["contributions"], output_path="breakdown.png")
```

## CLI (`scribe-batch`)

The batch evaluation is installed with the package as the `scribe-batch`
command (`python -m scribe.batch_cli` is equivalent). In a source checkout,
`uv run examples/batch_evaluate.py` runs the same command with the bundled
`examples/predictions.jsonl` as the default input and `examples/output/` as
the default output directory.

### Reproducible research run

One command produces everything a results section needs:

```bash
pip install scribe-eval

scribe-batch \
    --input predictions.jsonl \
    --output-dir results \
    --ref-field text \
    --hyp-field pred_text \
    --domain legal \
    --analysis \
    --chart
```

`results/` then contains:

- `summary_report.txt` — the aggregate table (ER_LEX, ER_DOMAIN, ER_NUM,
  ER_PUNCT, WER_SCRIBE, CER_SCRIBE and Sandhi hits), one OVERALL row plus one
  row per group, followed by a run-info line recording the sample count,
  worker count, sandhi and normalization settings, domain, `top_n` and the
  `scribe-eval` version, e.g.
  `Evaluation completed in 38.2s (20 samples, workers=16, sandhi=on, normalize=on, domain=legal, top_n=all, scribe-eval 0.2.0)`.
  Quote the command and this line and the run is reproducible.
- `evaluation-detailed.jsonl` — every input record with its per-category
  breakdown and CER block added (schema below).
- `analysis_report.txt` — accuracy, WER_SCRIBE, CER_SCRIBE, the token
  breakdown by category, and the frequent substitutions, deletions,
  insertions, sandhi merges and sandhi splits. With the default
  `--top-n all` every distinct error is listed; the console echo shows at
  most 20 rows per table and says how many more the file holds.
- `category_breakdown.png` — the category breakdown chart.

Notes:

- **Workers.** `--workers auto` (the default) starts one process per usable
  CPU (respecting container/cgroup limits), never more than there are
  samples. Results are identical for any worker count and stay in input
  order; only wall time changes, and it is bounded by the longest sample,
  so gains flatten once there are more workers than long samples. On a
  shared machine pass a smaller number; a number above the CPU count is
  allowed and merely oversubscribes.
- **Sandhi.** Detection is on by default; merged or split Indic compounds
  count as Sandhi matches, not errors. Pass `--no-sandhi` for
  non-agglutinative languages (English, Hindi, ...) or to report the strict
  variant; the sandhi sections then disappear from the analysis report and
  the SANDHI column is 0.
- **Top-N.** `--top-n 15` cuts every frequent-error table in the file to 15
  rows (and the console to the same). The default `all` is right for a
  report file; use a number when you only want a glance.

More invocations:

```bash
# Custom field names, sandhi off
scribe-batch -i predictions.jsonl -o results \
    --ref-field reference --hyp-field hypothesis --no-sandhi --analysis

# Bundled domain by name, or none
scribe-batch -i predictions.jsonl -o results --domain medical
scribe-batch -i predictions.jsonl -o results --domain none

# Domain config file (auto-detected: not a bundled name)
scribe-batch -i predictions.jsonl -o results --domain my_terms.txt

# Group the per-group table by another record field
scribe-batch -i predictions.jsonl -o results --group-by speaker

# Shorter tables, fixed worker count
scribe-batch -i predictions.jsonl -o results --analysis --top-n 15 --workers 4
```

### All CLI Arguments

| Argument | Default | Description |
|---|---|---|
| `-i`, `--input` | *(required)* | Input JSONL file (the examples wrapper defaults to the bundled sample) |
| `-o`, `--output-dir` | `./scribe-output` | Output directory, created if missing |
| `--ref-field` | `text` | Reference field name |
| `--hyp-field` | `pred_text` | Hypothesis field name |
| `--group-by FIELD` | `source_dataset` | Record field whose value splits the per-group rows (any field, e.g. `speaker`) |
| `--domain` | `legal` | Bundled domain name (`legal`, `medical`, `technical`, `none`) or path to a domain config file |
| `--no-normalize` | *(normalization enabled)* | Disable token normalization |
| `--no-sandhi` | *(sandhi detection enabled)* | Disable Sandhi merge/split detection |
| `--analysis` | *(off)* | Enable detailed error analysis (contributions, frequent errors) |
| `--top-n N\|all` | `all` | Frequent-error rows per table in `analysis_report.txt`; the console shows at most 20 |
| `--chart` | *(off)* | Save `category_breakdown.png` (requires `--analysis`) |
| `--workers N\|auto` | `auto` | Worker processes; `auto` = usable CPUs, capped at the sample count |
| `--skip-bad-records` | *(fail fast)* | Skip invalid lines/records with a warning each instead of stopping |

The command exits 0 on success and 1 on a missing input file, an unknown
domain, a bad record (without `--skip-bad-records`), or when every record
was skipped.

### Output Files

Always produced:
- `summary_report.txt` — formatted aggregate metrics table plus the run-info line
- `evaluation-detailed.jsonl` — per-sample breakdown (see below)

With `--analysis`:
- `analysis_report.txt` — WER_SCRIBE, accuracy, category breakdown table, frequent substitutions / deletions / insertions / sandhi merges / sandhi splits (the last two are only populated for agglutinative languages with sandhi events detected)

With `--analysis --chart`:
- `category_breakdown.png` — the category breakdown report card: one row per category with a normalized match/sub/del/ins bar, accuracy figure and contribution to WER_SCRIBE

## Detailed JSONL Output Format

Each line is the original input record with the evaluation added. Three
keys are reserved and written by evaluation — `group` holds the grouping
value (copied from the `group_by` field, stringified, "unknown" when
missing, "overall" when no record has the field), `detailed_report` holds the per-category breakdown, and
`cer_scribe` holds the character error rate block (cer_scribe,
char_errors, ref_chars, and character-level S/I/D counts, computed on
normalized token streams); input fields with those names are replaced. Every other
original field is preserved verbatim, including the field that was
grouped by. (In-memory results may also carry a reserved `error_details`
key when `collect_error_details=True`; it is never written to the
JSONL.) A real example:

```json
{
  "audio_id": "case-042",
  "text": "charged u/s 302 IPC",
  "pred_text": "charged u/s 303 IPC",
  "source_dataset": "adalat-ai/court-audio",
  "group": "adalat-ai/court-audio",
  "detailed_report": {
    "LEXICAL": {
      "error_rate": 0.0,
      "substitutions": 0,
      "insertions": 0,
      "deletions": 0,
      "correct": 1,
      "total_ref": 1,
      "sandhi_hits": 0,
      "combined_total": 4
    },
    "PUNCT": {
      "error_rate": 0.0,
      "substitutions": 0,
      "insertions": 0,
      "deletions": 0,
      "correct": 0,
      "total_ref": 0,
      "sandhi_hits": 0,
      "combined_total": 4
    },
    "NUMERAL": {
      "error_rate": 0.25,
      "substitutions": 1,
      "insertions": 0,
      "deletions": 0,
      "correct": 0,
      "total_ref": 1,
      "sandhi_hits": 0,
      "combined_total": 4
    },
    "LEGAL": {
      "error_rate": 0.0,
      "substitutions": 0,
      "insertions": 0,
      "deletions": 0,
      "correct": 2,
      "total_ref": 2,
      "sandhi_hits": 0,
      "combined_total": 4
    }
  },
  "cer_scribe": {
    "cer_scribe": 0.05263157894736842,
    "char_errors": 1,
    "ref_chars": 19,
    "substitutions": 1,
    "deletions": 0,
    "insertions": 0
  }
}
```

All error rates use the combined denominator (total tokens across all categories). See [Combined denominator](architecture.md#glossary) in the architecture glossary for details.
