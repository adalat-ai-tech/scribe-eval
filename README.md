# DictErrors — Dictation Error Analysis for Indic Languages

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

DictErrors is a specialized tool for analyzing ASR (Automatic Speech Recognition) transcription errors in Indic languages (Malayalam, Kannada). It provides fine-grained error metrics by categorizing tokens into base categories (WORD, NUMERAL, PUNCT) and optional domain-specific categories (LEGAL, MEDICAL, TECH, or custom).

Domain-critical terminology is shielded from incorrect splitting and tracked separately — so a single misrecognized legal term doesn't inflate your general WER.

## Installation

```bash
git clone https://github.com/adalat-ai-tech/dict-errors.git
cd dict-errors
uv sync && uv pip install -e .
```

## Quick Start

```python
from dicterrors import text_error_rates, DomainConfig

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
- **Interactive visualizer** — Streamlit UI with color-coded alignment and per-sample drill-down

## Token Categories

| Category | Type | Label | Description |
|---|---|---|---|
| WORD | base | WER | General words (Indic and English) |
| NUMERAL | base | NER | Numbers, dates, times (302, 22.05.2023, 10:30) |
| PUNCT | base | PER | Punctuation marks |
| LEGAL | domain | LER | Indian legal terminology (u/s, r/w, PW1, Ext.A) |
| MEDICAL | domain | MER | Medical units and dosages (mg, ml, 500mg) |
| TECH | domain | TER | Technical abbreviations (API, SDK, v1.0) |
| Custom | domain | configurable | Define your own with lists or regex patterns |

## Domain Configuration

Factory methods for bundled domains: `DomainConfig.legal()`, `DomainConfig.medical()`, `DomainConfig.technical()`

File-based and custom inline configs are also supported. See [docs/domain-configuration.md](docs/domain-configuration.md).

## Batch Processing

```bash
cd examples/
uv run batch_evaluate.py --input predictions.jsonl --domain-config config/legal_terms.txt
```

See [docs/batch-processing.md](docs/batch-processing.md) for the Python API, CLI arguments, and output schema.

## Interactive Visualizer

```bash
streamlit run visualizer.py
```

See [docs/visualizer.md](docs/visualizer.md).

## Dependencies

- `levenshtein>=0.27.1`, `jiwer>=4.0.0`, `streamlit>=1.53.0`, `tabulate>=0.9.0`

## Acknowledgements

Developed as part of the [Adalat AI](https://adalat.ai) initiative for Indic language technologies.
