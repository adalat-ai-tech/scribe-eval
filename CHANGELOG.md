# Changelog

All notable changes to scribe-eval are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-17

### Added
- `scribe-batch` console script: batch evaluation installed with the
  package (`python -m scribe.batch_cli` is equivalent). New flags
  `--no-sandhi`, `--top-n N|all` (default `all`; console capped at 20 rows
  per table), `--workers N|auto` (default `auto`: usable CPUs honouring
  affinity, cgroup CPU quotas and the 61-worker Windows limit, capped at
  the sample count) and `--group-by FIELD`. A run-info line (samples,
  workers, sandhi, normalization, domain, top-n, version) is printed and
  appended to `summary_report.txt`. (#44)
- `[all]` extra bundling every optional component. (#44)
- `NUMERAL_REGEX:` lines in domain config files declare domain-specific
  numeral formats (`5(1)(a)`, `1679/2015`) that stay one NUMERAL token.
- Bundled legal config: anchors (Section, Order, Rule, case-type numbers,
  PW, Exhibit), Act and court names, titles, dotted acronyms, versus forms
  and Latin phrases as single LEGAL tokens; spaced statute references kept
  whole. (#41)
- `docs/development.md` and a "Reproducible research run" recipe in
  `docs/batch-processing.md`.

### Changed
- **Breaking:** the dataset split is now a generic group-by. API parameter
  `source_dataset_field=` is replaced by `group_by=` (default
  `"source_dataset"`), the per-record output key `source_dataset` by
  `group`, the aggregate key `by_dataset` by `by_group`,
  `format_dataset_table()` by `format_group_table()`, the summary header
  `DATASET` by `GROUP`, and the CLI flag `--dataset-field` by
  `--group-by`. (#42)
- **Breaking:** `examples/batch_evaluate.py` is a thin wrapper over
  `scribe.batch_cli`; `--top-n` defaults to `all` and `--workers` to
  `auto` instead of 10 and 1. (#44)
- matplotlib is a core dependency, so `--chart` works with the base
  install; the `[charts]` extra is removed. (#44)
- Domain terms glued to numbers are split by the tokenizer (`PW1` ->
  `PW | 1`, `Cr.No.353` -> `Cr.No. | 353`).
- README rewritten as a CLI-first PyPI page; detailed usage moved to
  `docs/`. Paper citation now points to the ISCA Archive DOI. (#44)

### Fixed
- `--workers auto` no longer oversubscribes inside containers with a CPU
  quota or exceeds the process-pool limit on Windows. (#44)

## [0.1.1] - 2026-09-23

See the [GitHub release](https://github.com/adalat-ai-tech/scribe-eval/releases/tag/v0.1.1).

## [0.1.0] - 2026-06-19

First public release. See the [GitHub release](https://github.com/adalat-ai-tech/scribe-eval/releases/tag/v0.1.0).

[0.2.0]: https://github.com/adalat-ai-tech/scribe-eval/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/adalat-ai-tech/scribe-eval/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/adalat-ai-tech/scribe-eval/releases/tag/v0.1.0
