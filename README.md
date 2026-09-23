# SCRIBE — Diagnostic Evaluation for Indic & Domain-Specific ASR

[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/adalat-ai-tech/scribe-eval/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20765419.svg)](https://doi.org/10.5281/zenodo.20765419)

`scribe-eval` is the open-source evaluation framework introduced in the SCRIBE
paper (*Diagnostic Evaluation and Rich Transcription Models for Indic ASR*,
accepted at Interspeech 2026). It provides fine-grained error metrics for
ASR systems on Indic languages (Malayalam, Kannada, Hindi, ...) and on
domain-specific transcription (legal, medical, technical).

Token categories are decomposed into base classes (LEXICAL, NUMERAL, PUNCT) and
optional domain classes (LEGAL, MEDICAL, TECH, or custom). Domain-critical
terminology is shielded from incorrect splitting and tracked separately — so a
single misrecognized legal term doesn't inflate your general lexical
error rate (ER_LEX).

## Installation

```bash
pip install scribe-eval                 # core library
pip install 'scribe-eval[visualizer]'   # adds Streamlit UI
pip install 'scribe-eval[charts]'       # adds matplotlib charts
```

The core library depends only on `levenshtein` and `tabulate`. The extras are
optional and independent of each other.

To work on SCRIBE itself, install from source instead:

```bash
git clone https://github.com/adalat-ai-tech/scribe-eval.git
cd scribe-eval
pip install -e '.[visualizer,charts]'
```

## Quick Start

```python
from scribe import compute_cer_scribe, text_error_rates, DomainConfig

ref = "charged u/s 302 IPC on 22.05.2023"
hyp = "charged u/s 303 IPC on 22.05.2023"

report = text_error_rates(ref, hyp, DomainConfig.legal())

print(f"ER_LEX: {report['LEXICAL']['error_rate']:.2%}")
print(f"ER_DOMAIN: {report['LEGAL']['error_rate']:.2%}")
print(f"ER_NUM: {report['NUMERAL']['error_rate']:.2%}")

cer = compute_cer_scribe(ref, hyp, DomainConfig.legal())
print(f"CER_SCRIBE: {cer['cer_scribe']:.2%}")
```

## Features

- **Domain-aware tokenization** — shield domain terms from punctuation splitting; track errors separately
- **Sandhi correction detection** — identifies merged/split words common in Indic ASR
- **Normalized error rates** — combined denominator prevents misleading metrics for sparse categories
- **CER_SCRIBE** — character error rate on normalized token streams; format variants cost nothing, and it needs no sandhi machinery to be robust to agglutination
- **Batch evaluation** — evaluate in-memory records (`evaluate_records`) or JSONL files with per-sample detail and dataset-level aggregation
- **Interactive visualizer** — Streamlit UI with color-coded alignment, WER_SCRIBE/CER_SCRIBE/Accuracy metric tiles, category breakdown chart, frequent-error tables, and per-sample drill-down

## Token Categories

| Category | Type | Label | Description |
|---|---|---|---|
| LEXICAL | base | ER_LEX | General words (Indic and English) |
| NUMERAL | base | ER_NUM | Numbers, dates, times (302, 22.05.2023, 10:30) |
| PUNCT | base | ER_PUNCT | Punctuation marks |
| LEGAL / MEDICAL / TECH / custom | domain | ER_DOMAIN | Domain terminology — bundled or your own |

One domain is active per evaluation: pass a single `DomainConfig`
(a bundled factory like `DomainConfig.legal()` or your own file via
`DomainConfig.from_file`); its error rate always reports as **ER_DOMAIN**.
See [docs/domain-configuration.md](https://github.com/adalat-ai-tech/scribe-eval/blob/main/docs/domain-configuration.md).

## Sandhi Awareness

Agglutination makes word boundaries unstable in Indic text: the same
speech can be written as one word or two. SCRIBE detects such two-word
merges and splits at alignment time and scores them as matches instead
of errors.
Real examples from evaluation data (each would count as 100% WER on its
phrase without detection):

| Language | Reference | Hypothesis | Junction |
|---|---|---|---|
| Malayalam | അന്യായ പട്ടിക | അന്യായപ്പട്ടിക | gemination |
| Malayalam | എനിക്ക് അറിയാം | എനിക്കറിയാം | vowel elision |
| Kannada | ಪ್ರಧಾನ ಮಂತ್ರಿಗಳ | ಪ್ರಧಾನಮಂತ್ರಿಗಳ | compound merge |
| Kannada | ಮಿತ್ರರಾಷ್ಟ್ರಗಳು | ಮಿತ್ರ ರಾಷ್ಟ್ರಗಳು | compound split |
| Hindi | भाई साहब | भाईसाहब | compound spacing |
| Hindi | उस में | उसमें | postposition merge |

On an internal benchmark of 48 Malayalam legal dictations (private
data, not distributed with this repository), sandhi detection recovers
**3.0 percentage points of WER_SCRIBE** across 377 events that would
otherwise masquerade as recognition errors. The paired examples above
are directly reproducible: score any row with `use_sandhi=True` vs
`use_sandhi=False` in `text_error_rates`.

Detection is an orthographic heuristic, not a linguistic analysis — it
is deliberately lenient and admits some false positives. See
[Sandhi detection: scope and limitations](https://github.com/adalat-ai-tech/scribe-eval/blob/main/docs/architecture.md#sandhi-detection-scope-and-limitations)
before relying on sandhi counts.

## Domain Configuration

Factory methods for bundled domains: `DomainConfig.legal()`, `DomainConfig.medical()`, `DomainConfig.technical()`

File-based and custom inline configs are also supported. See [docs/domain-configuration.md](https://github.com/adalat-ai-tech/scribe-eval/blob/main/docs/domain-configuration.md).

## Batch Processing

Evaluate a dataset from JSONL, one record per line:

```jsonl
{"text": "charged u/s 302 IPC on 22.05.2023", "pred_text": "charged u/s 303 IPC on 22-05-2023", "source_dataset": "legal-dictation"}
{"text": "witness PW1 deposed before the court", "pred_text": "witness PW 1 deposed before court", "source_dataset": "legal-dictation"}
{"text": "എനിക്ക് അറിയാം", "pred_text": "എനിക്കറിയാം", "source_dataset": "malayalam-read"}
```

```python
from scribe import compute_sample_errors, compute_aggregate_metrics, print_evaluation_summary, DomainConfig

results = compute_sample_errors(
    "predictions.jsonl", domain_config=DomainConfig.legal(), collect_error_details=True
)
print_evaluation_summary(compute_aggregate_metrics(results))
```

```
DATASET                   |     ER_LEX |  ER_DOMAIN |     ER_NUM |   ER_PUNCT | WER_SCRIBE | CER_SCRIBE | SANDHI
OVERALL                   |      7.14% |      7.14% |      7.14% |        N/A |     21.43% |     10.84% |      1
legal-dictation           |      8.33% |      8.33% |      8.33% |        N/A |     25.00% |      8.70% |      0
malayalam-read            |      0.00% |        N/A |        N/A |        N/A |      0.00% |     21.43% |      1
```

The Malayalam hypothesis merges a two-word compound; it is counted as a Sandhi
match, not as errors. `N/A` marks a category with no reference tokens and no
errors.

`evaluate_records()` accepts a list of dicts instead of a file path.
`output_file=` writes per-sample reports as JSONL. `workers=N` evaluates
samples in parallel.

### Charts

Continuing from `results` above, with the `[charts]` extra installed:

```python
from scribe import aggregate_error_details, compute_error_summary
from scribe.charts import category_breakdown_chart

summary = compute_error_summary(
    compute_aggregate_metrics(results)["overall"], aggregate_error_details(results), top_n=10
)
category_breakdown_chart(summary["contributions"], output_path="breakdown.png")
```

![Category breakdown chart](https://raw.githubusercontent.com/adalat-ai-tech/scribe-eval/main/docs/images/category-breakdown.png)

One row per category: a normalized outcome bar, an accuracy figure, and that
category's contribution to WER_SCRIBE. Punctuation is marked "nothing to
measure" because the reference carries no punctuation tokens.

## Examples

Runnable scripts live in the repository under
[`examples/`](https://github.com/adalat-ai-tech/scribe-eval/tree/main/examples),
covering alignment, single-sample reports, domain configs, and a batch
command-line tool. They are not installed with the package, so clone the
repository to use them. See
[docs/batch-processing.md](https://github.com/adalat-ai-tech/scribe-eval/blob/main/docs/batch-processing.md)
for the full batch API and output schema.

## Interactive Visualizer

```bash
scribe-visualizer    # requires the [visualizer] extra (see Installation)
```

See [docs/visualizer.md](https://github.com/adalat-ai-tech/scribe-eval/blob/main/docs/visualizer.md).

## Dependencies

Core: `levenshtein>=0.27.1`, `tabulate>=0.9.0`

Optional extras: `matplotlib` (for `[charts]`), `streamlit`, `pandas`, `matplotlib`, and `jiwer` (for `[visualizer]` — jiwer powers the baseline WER/CER comparison tile).

## Development

```bash
git clone https://github.com/adalat-ai-tech/scribe-eval.git
cd scribe-eval
uv sync --all-extras    # core + [charts] + [visualizer] + dev tooling
```

### Running tests

```bash
uv run pytest                              # full suite
uv run pytest tests/test_analysis.py       # one file
uv run pytest -k sandhi                    # name pattern (-k matches by substring)
uv run pytest -v                           # verbose, with each test name
uv run pytest --cov=scribe                 # with coverage
```

Tests are organised one file per library module under [`tests/`](https://github.com/adalat-ai-tech/scribe-eval/blob/main/tests/), plus
[`tests/test_paper_cases.py`](https://github.com/adalat-ai-tech/scribe-eval/blob/main/tests/test_paper_cases.py) for end-to-end golden
cases from the SCRIBE paper. `pytest` itself is part of the `dev` dependency
group, which `uv sync` installs by default.

### Lint and format

```bash
uv run ruff check src tests examples       # lint
uv run ruff format src tests examples      # auto-format
```

See [`docs/architecture.md`](https://github.com/adalat-ai-tech/scribe-eval/blob/main/docs/architecture.md) for the module map and a
glossary of project-specific terminology (sandhi, combined denominator, WER_SCRIBE, CER_SCRIBE,
Accuracy, ...).

## Citation

The SCRIBE paper is accepted at Interspeech 2026. A preprint is available on
arXiv: <https://arxiv.org/abs/2605.20712>

```bibtex
@article{manohar2026scribe,
  title={SCRIBE: Diagnostic Evaluation and Rich Transcription Models for Indic ASR},
  author={Manohar, Kavya and Bhattacharya, Arghya and Juvekar, Kush and Nethil, Kumarmanas},
  journal={arXiv preprint arXiv:2605.20712},
  year={2026}
}
```

To cite the software itself, use the "Cite this repository" button on GitHub
(see [CITATION.cff](https://github.com/adalat-ai-tech/scribe-eval/blob/main/CITATION.cff)) or the Zenodo DOI:
[10.5281/zenodo.20765419](https://doi.org/10.5281/zenodo.20765419).

## License

Licensed under the [Apache License 2.0](https://github.com/adalat-ai-tech/scribe-eval/blob/main/LICENSE).

## Acknowledgements

Developed as part of the [Adalat AI](https://adalat.ai) initiative for Indic language technologies.
