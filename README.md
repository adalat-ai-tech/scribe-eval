# SCRIBE — Diagnostic Evaluation for Indic & Domain-Specific ASR

[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
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

`scribe-eval` is not yet on PyPI — install from source for now (`pip install scribe-eval` will work once published):

```bash
git clone https://github.com/adalat-ai-tech/scribe-eval.git
cd scribe-eval
pip install -e .                 # core library
pip install -e '.[visualizer]'   # adds Streamlit UI
pip install -e '.[charts]'       # adds matplotlib charts
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
See [docs/domain-configuration.md](docs/domain-configuration.md).

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
[Sandhi detection: scope and limitations](docs/architecture.md#sandhi-detection-scope-and-limitations)
before relying on sandhi counts.

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
scribe-visualizer    # requires the [visualizer] extra (see Installation)
```

See [docs/visualizer.md](docs/visualizer.md).

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

Tests are organised one file per library module under [`tests/`](tests/), plus
[`tests/test_paper_cases.py`](tests/test_paper_cases.py) for end-to-end golden
cases from the SCRIBE paper. `pytest` itself is part of the `dev` dependency
group, which `uv sync` installs by default.

### Lint and format

```bash
uv run ruff check src tests examples       # lint
uv run ruff format src tests examples      # auto-format
```

See [`docs/architecture.md`](docs/architecture.md) for the module map and a
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
(see [CITATION.cff](CITATION.cff)) or the Zenodo DOI:
[10.5281/zenodo.20765419](https://doi.org/10.5281/zenodo.20765419).

## License

Licensed under the [Apache License 2.0](LICENSE).

## Acknowledgements

Developed as part of the [Adalat AI](https://adalat.ai) initiative for Indic language technologies.
