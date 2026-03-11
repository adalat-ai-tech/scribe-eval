# Batch Processing

DictErrors supports processing multiple samples from a JSONL file and aggregating metrics across datasets.

## Input Format

Each line in the JSONL file must have:

| Field | Default key | Description |
|---|---|---|
| Reference text | `transcript_cleaned` | Ground truth transcription |
| Hypothesis text | `prediction` | ASR model output |
| Dataset ID | `source_dataset` | Optional; groups per-dataset metrics |

## Python API

```python
from dicterrors import compute_sample_errors, compute_aggregate_metrics, DomainConfig

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

## CLI (`batch_evaluate.py`)

```bash
cd examples/

# Default run (uses built-in sample data)
uv run batch_evaluate.py

# Custom input/output
uv run batch_evaluate.py \
    --input ./my-data/predictions.jsonl \
    --output-dir ./results \
    --ref-field reference \
    --hyp-field hypothesis

# With a domain config file
uv run batch_evaluate.py \
    --input data/predictions.jsonl \
    --domain-config config/legal_terms.txt
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

### Output Files

- `evaluation-summary.txt` — formatted aggregate metrics table
- `evaluation-detailed.jsonl` — per-sample breakdown (see below)

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
