# SCRIBE — Diagnostic Evaluation for Indic & Domain-Specific ASR

[![PyPI](https://img.shields.io/pypi/v/scribe-eval.svg)](https://pypi.org/project/scribe-eval/)
[![Python](https://img.shields.io/pypi/pyversions/scribe-eval.svg)](https://pypi.org/project/scribe-eval/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

`scribe-eval` is the open-source evaluation framework introduced in the SCRIBE
paper (*Diagnostic Evaluation and Rich Transcription Models for Indic ASR*,
under review at Interspeech 2026). It provides fine-grained error metrics for
ASR systems on Indic languages (Malayalam, Kannada, Hindi, ...) and on
domain-specific transcription (legal, medical, technical).

Token categories are decomposed into base classes (WORD, NUMERAL, PUNCT) and
optional domain classes (LEGAL, MEDICAL, TECH, or custom). Domain-critical
terminology is shielded from incorrect splitting and tracked separately — so a
single misrecognized legal term doesn't inflate your general WER.

## Installation

```bash
pip install scribe-eval                # core library
pip install 'scribe-eval[visualizer]'  # adds Streamlit UI
pip install 'scribe-eval[charts]'      # adds matplotlib charts
```

## Quick Start

```python
from scribe import text_error_rates, DomainConfig

ref = "charged u/s 302 IPC on 22.05.2023"
hyp = "charged u/s 303 IPC on 22.05.2023"

report = text_error_rates(ref, hyp, DomainConfig.legal())

print(f"WER: {report['WORD']['error_rate']:.2%}")
print(f"LER: {report['LEGAL']['error_rate']:.2%}")
print(f"NER: {report['NUMERAL']['error_rate']:.2%}")
```

## Features

- **Domain-aware tokenization** — shield domain terms from punctuation splitting; track errors separately
- **Sandhi correction detection** — identifies merged/split words common in Indic ASR
- **Normalized error rates** — combined denominator prevents misleading metrics for sparse categories
- **Batch evaluation** — process JSONL files with per-sample detail and dataset-level aggregation
- **Interactive visualizer** — Streamlit UI with color-coded alignment, TER/Accuracy metric tiles, category breakdown chart, frequent-error tables, and per-sample drill-down

## Token Categories

| Category | Type | Label | Description |
|---|---|---|---|
| WORD | base | WER | General words (Indic and English) |
| NUMERAL | base | NER | Numbers, dates, times (302, 22.05.2023, 10:30) |
| PUNCT | base | PER | Punctuation marks |
| LEGAL | domain | LER | Indian legal terminology (u/s, r/w, PW1, Ext.A) |
| MEDICAL | domain | MER | Medical units and dosages (mg, ml, 500mg) |
| TECH | domain | TchER | Technical abbreviations (API, SDK, v1.0) |
| Custom | domain | configurable | Define your own with lists or regex patterns |

## Domain Configuration

Factory methods for bundled domains: `DomainConfig.legal()`, `DomainConfig.medical()`, `DomainConfig.technical()`

File-based and custom inline configs are also supported. See [docs/domain-configuration.md](docs/domain-configuration.md).

## Examples

Runnable scripts under [`examples/`](examples/) demonstrate alignment,
single-sample reports, domain-config patterns, and full batch evaluation.
See [`examples/README.md`](examples/README.md) for the full index.

## Batch Processing

```bash
uv run examples/batch_evaluate.py --analysis --chart
```

See [docs/batch-processing.md](docs/batch-processing.md) for the Python API, CLI arguments, and output schema.

## Interactive Visualizer

```bash
pip install 'scribe-eval[visualizer]'
scribe-visualizer
```

See [docs/visualizer.md](docs/visualizer.md).

## Dependencies

Core: `jiwer>=4.0.0`, `levenshtein>=0.27.1`, `tabulate>=0.9.0`

Optional extras: `matplotlib` (for `[charts]`), `streamlit` and `pandas` (for `[visualizer]`).

## Development

```bash
git clone https://github.com/adalat-ai-tech/scribe-eval.git
cd scribe-eval
uv sync --all-extras --dev    # core + [charts] + [visualizer] + [dev]

uv run pytest                 # full test suite (tests/)
uv run pytest --cov=scribe    # with coverage
uv run ruff check src tests examples    # lint
uv run ruff format src tests examples   # auto-format
```

Tests are organised one file per library module under [`tests/`](tests/), plus
[`tests/test_paper_cases.py`](tests/test_paper_cases.py) for end-to-end golden
cases from the SCRIBE paper. See [`docs/architecture.md`](docs/architecture.md)
for the module map and a glossary of project-specific terminology
(sandhi, combined denominator, TER, Accuracy, ...).

## Citation

The SCRIBE paper is currently under anonymous review at Interspeech 2026. A
BibTeX entry will be added here once the proceedings or arXiv preprint are
publicly available. Until then, please cite this repository directly via the
"Cite this repository" button on GitHub.

## License

Licensed under the [Apache License 2.0](LICENSE).

## Acknowledgements

Developed as part of the [Adalat AI](https://adalat.ai) initiative for Indic language technologies.
