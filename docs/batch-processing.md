# Batch Processing

scribe-eval supports processing multiple samples from a JSONL file and aggregating metrics across datasets.

## Input Format

Each line in the JSONL file must have:

| Field | Default key | Description |
|---|---|---|
| Reference text | `transcript_cleaned` | Ground truth transcription |
| Hypothesis text | `prediction` | ASR model output |
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
metrics = compute_aggregate_metrics(results, domain_config=domain)

# Overall metrics
print(metrics['overall']['WORD']['error_rate'])
print(metrics['overall']['LEGAL']['error_rate'])

# Per-dataset metrics
for dataset, data in metrics['by_dataset'].items():
    print(f"{dataset}: WER={data['WORD']['error_rate']:.2%}")
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

metrics = compute_aggregate_metrics(results, domain_config=domain)

# Flatten all token-level error records across samples
all_error_details = aggregate_error_details(results)

# Full analysis in one call
summary = compute_error_summary(metrics["overall"], all_error_details, top_n=10)
print(f"TER:      {summary['total_error_rate']:.2%}")
print(f"Accuracy: {summary['total_correct_pct']:.1f}%")

# Formatted tables for display
contrib_rows = format_contribution_table(summary["contributions"], domain)
sub_rows = format_frequent_errors_table(summary["frequent_substitutions"], "substitution", top_n=10)
del_rows = format_frequent_errors_table(summary["frequent_deletions"], "deletion", top_n=10)
ins_rows = format_frequent_errors_table(summary["frequent_insertions"], "insertion", top_n=10)
```

## CLI (`batch_evaluate.py`)

```bash
cd examples/

# Default run
uv run batch_evaluate.py

# Custom input/output
uv run batch_evaluate.py \
    --input ./my-data/predictions.jsonl \
    --output-dir ./results \
    --ref-field reference \
    --hyp-field hypothesis

# With domain config file
uv run batch_evaluate.py \
    --input data/predictions.jsonl \
    --domain-config config/legal_terms.txt

# With detailed error analysis and category breakdown chart
uv run batch_evaluate.py \
    --input data/predictions.jsonl \
    --analysis \
    --top-n 15 \
    --chart
```

### All CLI Arguments

| Argument | Default | Description |
|---|---|---|
| `-i`, `--input` | `./dictation-eval/predictions.jsonl` | Input JSONL file |
| `-o`, `--output-dir` | `./dictation-eval` | Output directory |
| `--ref-field` | `transcript_cleaned` | Reference field name |
| `--hyp-field` | `prediction` | Hypothesis field name |
| `--dataset-field` | `source_dataset` | Dataset identifier field |
| `--domain-config` | *(uses `DomainConfig.legal()`)* | Path to domain config file |
| `--no-normalize` | *(normalization enabled)* | Disable token normalization |
| `--analysis` | *(off)* | Enable detailed error analysis (contributions, frequent errors) |
| `--top-n N` | `10` | Number of top frequent errors to display |
| `--chart` | *(off)* | Save `category_breakdown.png` (requires `--analysis` and `matplotlib`) |

### Output Files

Always produced:
- `evaluation-summary.txt` — formatted aggregate metrics table
- `evaluation-detailed.jsonl` — per-sample breakdown (see below)

With `--analysis`:
- `analysis_report.txt` — TER, accuracy, category breakdown table, top-N frequent substitutions/deletions/insertions

With `--analysis --chart`:
- `category_breakdown.png` — 2-panel stacked bar chart: token matches per category (left panel) and each category's contribution to the overall TER (right panel)

## Detailed JSONL Output Format

Each line in the detailed output contains:

```json
{
  "sample_id": 1,
  "source_dataset": "adalat-ai/court-audio",
  "reference": "charged u/s 302 IPC",
  "hypothesis": "charged u/s 303 IPC",
  "WORD": {
    "error_rate": 0.0,
    "substitutions": 0,
    "insertions": 0,
    "deletions": 0,
    "correct": 2,
    "sandhi_hits": 0
  },
  "LEGAL": {
    "error_rate": 0.0,
    "substitutions": 0,
    "insertions": 0,
    "deletions": 0,
    "correct": 1,
    "sandhi_hits": 0
  },
  "NUMERAL": {
    "error_rate": 0.2,
    "substitutions": 1,
    "insertions": 0,
    "deletions": 0,
    "correct": 0,
    "sandhi_hits": 0
  },
  "PUNCT": {
    "error_rate": 0.0,
    "substitutions": 0,
    "insertions": 0,
    "deletions": 0,
    "correct": 0,
    "sandhi_hits": 0
  }
}
```

All error rates use the combined denominator (total tokens across all categories). See [Normalized Error Rates](../README.md#normalized-error-rates) for details.
