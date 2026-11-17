# Development

## Setup

```bash
git clone https://github.com/adalat-ai-tech/scribe-eval.git
cd scribe-eval
uv sync --all-extras    # core + [visualizer] + dev tooling
```

`uv sync` installs the `dev` dependency group (pytest, ruff, mypy, build,
twine) by default; `--all-extras` adds the visualizer so its smoke test and
`scribe-visualizer` work from the checkout.

## Running tests

```bash
uv run pytest                              # full suite
uv run pytest tests/test_analysis.py       # one file
uv run pytest -k sandhi                    # name pattern (-k matches by substring)
uv run pytest -v                           # verbose, with each test name
uv run pytest --cov=scribe                 # with coverage
```

Tests are organised one file per library module under
[`tests/`](../tests/), plus
[`tests/test_paper_cases.py`](../tests/test_paper_cases.py) for end-to-end
golden cases from the SCRIBE paper and
[`tests/test_batch_cli.py`](../tests/test_batch_cli.py) for the
`scribe-batch` command.

## Lint and format

```bash
uv run ruff check src tests examples       # lint
uv run ruff format src tests examples      # auto-format
```

## Running the tools from a checkout

```bash
uv run scribe-batch --input examples/predictions.jsonl --output-dir examples/output --analysis
uv run examples/batch_evaluate.py --analysis     # same command, bundled sample as default input
uv run scribe-visualizer
```

## Where things live

See [architecture.md](architecture.md) for the pipeline, the module map, a
"where to make a change" table and a glossary of project-specific terms
(sandhi, combined denominator, WER_SCRIBE, CER_SCRIBE, Accuracy, ...).
