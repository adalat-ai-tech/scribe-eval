# Batch Processing

scribe-eval supports processing multiple samples from a JSONL file and aggregating metrics across datasets.

## Input Format

Each line in the JSONL file must have:

| Field | Default key | Description |
|---|---|---|
| Reference text | `text` | Ground truth transcription (NeMo manifest convention) |
| Hypothesis text | `pred_text` | ASR model output |
| Dataset ID | `source_dataset` | Optional; groups per-dataset metrics |

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

# Per-dataset metrics
for dataset, data in metrics['by_dataset'].items():
    print(f"{dataset}: ER_LEX={data['LEXICAL']['error_rate']:.2%}")
```

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

## CLI (`batch_evaluate.py`)

```bash
# Default run (uses the bundled examples/predictions.jsonl sample)
uv run examples/batch_evaluate.py

# Custom input/output
uv run examples/batch_evaluate.py \
    --input ./my-data/predictions.jsonl \
    --output-dir ./results \
    --ref-field reference \
    --hyp-field hypothesis

# Bundled domain by name, or none
uv run examples/batch_evaluate.py --input data/predictions.jsonl --domain medical
uv run examples/batch_evaluate.py --input data/predictions.jsonl --domain none

# With domain config file (auto-detected: not a bundled name)
uv run examples/batch_evaluate.py \
    --input data/predictions.jsonl \
    --domain examples/sample_legal.txt

# With detailed error analysis and category breakdown chart
uv run examples/batch_evaluate.py \
    --input data/predictions.jsonl \
    --analysis \
    --top-n 15 \
    --chart
```

### All CLI Arguments

| Argument | Default | Description |
|---|---|---|
| `-i`, `--input` | bundled `examples/predictions.jsonl` | Input JSONL file |
| `-o`, `--output-dir` | `examples/output/` | Output directory (defaults alongside the script) |
| `--ref-field` | `text` | Reference field name |
| `--hyp-field` | `pred_text` | Hypothesis field name |
| `--dataset-field` | `source_dataset` | Dataset identifier field |
| `--domain` | `legal` | Bundled domain name (`legal`, `medical`, `technical`, `none`) or path to a domain config file |
| `--no-normalize` | *(normalization enabled)* | Disable token normalization |
| `--analysis` | *(off)* | Enable detailed error analysis (contributions, frequent errors) |
| `--top-n N` | `10` | Number of top frequent errors to display |
| `--chart` | *(off)* | Save `category_breakdown.png` (requires `--analysis` and `matplotlib`) |
| `--workers N` | `1` | Worker processes for parallel evaluation |
| `--skip-bad-records` | *(fail fast)* | Skip invalid lines/records with a warning each instead of stopping |

### Output Files

Always produced:
- `summary_report.txt` — formatted aggregate metrics table
- `evaluation-detailed.jsonl` — per-sample breakdown (see below)

With `--analysis`:
- `analysis_report.txt` — WER_SCRIBE, accuracy, category breakdown table, top-N frequent substitutions / deletions / insertions / sandhi merges / sandhi splits (the last two are only populated for agglutinative languages with sandhi events detected)

With `--analysis --chart`:
- `category_breakdown.png` — 2-panel stacked bar chart: token matches per category (left panel) and each category's contribution to the overall WER_SCRIBE (right panel)

## Detailed JSONL Output Format

Each line is the original input record with the evaluation added: all
original fields are kept verbatim, `source_dataset` is canonicalized
("unknown" when missing), and the per-category breakdown is nested
under `detailed_report`. A real example:

```json
{
  "audio_id": "case-042",
  "text": "charged u/s 302 IPC",
  "pred_text": "charged u/s 303 IPC",
  "source_dataset": "adalat-ai/court-audio",
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
  }
}
```

All error rates use the combined denominator (total tokens across all categories). See [Combined denominator](architecture.md#glossary) in the architecture glossary for details.
