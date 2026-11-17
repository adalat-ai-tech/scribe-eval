"""Command-line batch evaluation, installed as the ``scribe-batch`` script.

Reads a JSONL file of reference/hypothesis pairs, writes the aggregate
summary and per-sample reports, and (with ``--analysis``) the composite
WER_SCRIBE, category contributions, frequent error patterns and an
optional category-breakdown chart.

``python -m scribe.batch_cli`` runs the same entry point; the repository's
``examples/batch_evaluate.py`` wraps it with the bundled sample data as
the default input.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from tabulate import tabulate

from . import __version__
from .analysis import compute_error_summary
from .domain_config import DomainConfig
from .measure_batch import (
    aggregate_error_details,
    compute_aggregate_metrics,
    compute_sample_errors,
    print_evaluation_summary,
)
from .reporting import (
    format_contribution_table,
    format_frequent_errors_table,
    write_summary_to_file,
)

DEFAULT_OUTPUT_DIR = "scribe-output"
SUMMARY_REPORT_NAME = "summary_report.txt"
DETAILED_OUTPUT_NAME = "evaluation-detailed.jsonl"
ANALYSIS_REPORT_NAME = "analysis_report.txt"
CHART_NAME = "category_breakdown.png"

# With ``--top-n all`` the report file holds every row; the console echo
# is capped so a long frequent-error table does not scroll the summary away.
CONSOLE_ROW_CAP = 20

_RULE = "=" * 85


# --------------------------------------------------------------------------
# Argument helpers
# --------------------------------------------------------------------------


def validate_input_file(input_file: str) -> Path:
    """Return the input path, or raise if it is missing or empty."""
    path = Path(input_file)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    if path.stat().st_size == 0:
        raise ValueError(f"Input file is empty: {input_file}")
    return path


BUNDLED_DOMAINS = {
    "legal": DomainConfig.legal,
    "medical": DomainConfig.medical,
    "technical": DomainConfig.technical,
    "none": lambda: None,
}


def resolve_domain(value: str):
    """Resolve ``--domain``: a bundled name (case-insensitive) wins, anything
    else must be a domain config file path. Returns None for ``none``."""
    key = value.lower()
    if key in BUNDLED_DOMAINS:
        return BUNDLED_DOMAINS[key]()
    if os.path.exists(value):
        return DomainConfig.from_file(value)
    raise ValueError(
        f"--domain {value!r} is neither a bundled domain "
        f"({', '.join(sorted(BUNDLED_DOMAINS))}) nor an existing config file"
    )


def parse_top_n(value: str) -> Optional[int]:
    """``--top-n`` argument type: a positive integer, or ``all`` -> None."""
    if value.lower() == "all":
        return None
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a positive integer or 'all', got {value!r}")
    if n < 1:
        raise argparse.ArgumentTypeError(f"expected a positive integer or 'all', got {value!r}")
    return n


def parse_workers(value: str) -> Optional[int]:
    """``--workers`` argument type: a positive integer, or ``auto`` -> None."""
    if value.lower() == "auto":
        return None
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a positive integer or 'auto', got {value!r}")
    if n < 1:
        raise argparse.ArgumentTypeError(f"expected a positive integer or 'auto', got {value!r}")
    return n


def usable_cpu_count() -> int:
    """CPUs this process may run on.

    ``os.sched_getaffinity`` honours cgroup/container and ``taskset`` limits
    (the convention pytest-xdist and joblib follow); it is Linux-only, so
    fall back to ``os.cpu_count()`` elsewhere.
    """
    getaffinity = getattr(os, "sched_getaffinity", None)
    if getaffinity is not None:
        try:
            return max(1, len(getaffinity(0)))
        except OSError:
            pass
    return os.cpu_count() or 1


def resolve_workers(requested: Optional[int], n_samples: int) -> int:
    """Turn ``--workers`` into a process count.

    ``auto`` (None) uses every usable CPU, but never more workers than
    samples: a worker without a sample to evaluate only costs start-up time.
    An explicit integer is passed through unchanged.
    """
    if requested is not None:
        return requested
    return max(1, min(usable_cpu_count(), n_samples))


def count_records(path: Path) -> int:
    """Number of non-blank lines, i.e. the maximum useful worker count."""
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


# --------------------------------------------------------------------------
# Analysis report
# --------------------------------------------------------------------------

_FREQUENT_SECTIONS = (
    ("frequent_substitutions", "substitution", "Substitutions"),
    ("frequent_deletions", "deletion", "Deletions"),
    ("frequent_insertions", "insertion", "Insertions"),
    ("frequent_sandhi_merges", "sandhi_merge", "Sandhi Merges"),
    ("frequent_sandhi_splits", "sandhi_split", "Sandhi Splits"),
)


def _frequent_section(
    rows: List[Dict], label: str, top_n: Optional[int], console_cap: Optional[int]
) -> List[str]:
    """Lines for one frequent-error table; empty when there are no rows.

    ``rows`` already respects ``top_n`` (None = every row). ``console_cap``
    trims the echo and notes how many rows the report file holds.
    """
    if not rows:
        return []
    shown = rows if console_cap is None else rows[:console_cap]
    hidden = len(rows) - len(shown)
    # "All N" only when the table really is complete: no --top-n cut and
    # nothing held back by the console cap.
    heading = f"All {len(rows)}" if top_n is None and hidden == 0 else f"Top {len(shown)}"
    lines = [
        f"\n--- {heading} Frequent {label} ---",
        tabulate(shown, headers="keys", tablefmt="simple"),
    ]
    if hidden > 0:
        lines.append(f"({hidden} more rows in {ANALYSIS_REPORT_NAME})")
    return lines


def format_analysis_report(
    summary: Dict,
    top_n: Optional[int],
    cer_scribe: Optional[float] = None,
    *,
    console_cap: Optional[int] = None,
) -> str:
    """Render the detailed error analysis as text.

    Args:
        summary: Output of ``compute_error_summary()``.
        top_n: Frequent-error rows per table; None means every row.
        cer_scribe: Overall CER_SCRIBE to show beside WER_SCRIBE.
        console_cap: When set, each frequent-error table is cut to this many
            rows and a note says how many more the report file contains.

    Returns:
        The report text, ending with a newline.
    """
    lines = ["DETAILED ERROR ANALYSIS", _RULE]

    overall = (
        f"\nOverall: {summary['total_correct_pct']:.1f}% correct | "
        f"{summary['wer_scribe']:.2%} WER_SCRIBE"
    )
    if cer_scribe is not None:
        overall += f" | {cer_scribe:.2%} CER_SCRIBE"
    lines.append(overall)

    lines.append("\n--- Token Breakdown by Category ---")
    contrib_rows = format_contribution_table(summary["contributions"])
    lines.append(tabulate(contrib_rows, headers="keys", tablefmt="simple"))

    for key, error_type, label in _FREQUENT_SECTIONS:
        rows = format_frequent_errors_table(summary[key], error_type, top_n)
        lines.extend(_frequent_section(rows, label, top_n, console_cap))

    lines.append("\n" + _RULE)
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser(
    default_input: Optional[str] = None,
    default_output: str = DEFAULT_OUTPUT_DIR,
) -> argparse.ArgumentParser:
    """Build the argument parser.

    ``--input`` is required unless ``default_input`` is given (the examples
    wrapper passes the bundled sample file).
    """
    parser = argparse.ArgumentParser(
        prog="scribe-batch",
        description="Batch evaluation of ASR predictions with detailed error analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reproducible research run: summary, per-sample JSONL, full analysis, chart
  scribe-batch --input predictions.jsonl --output-dir results \\
      --domain legal --analysis --chart

  # Custom field names, sandhi detection off (non-agglutinative languages)
  scribe-batch -i predictions.jsonl -o results \\
      --ref-field reference --hyp-field hypothesis --no-sandhi --analysis

  # Shorter tables and a fixed worker count
  scribe-batch -i predictions.jsonl -o results --analysis --top-n 15 --workers 4

Output files (in --output-dir): summary_report.txt, evaluation-detailed.jsonl,
and with --analysis: analysis_report.txt, plus category_breakdown.png with --chart.
        """,
    )

    parser.add_argument(
        "-i",
        "--input",
        default=default_input,
        required=default_input is None,
        help="Input JSONL file with predictions"
        + (f" (default: {default_input})" if default_input else ""),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=default_output,
        help=f"Output directory for results (default: {default_output})",
    )
    parser.add_argument(
        "--ref-field",
        default="text",
        help="Field name for reference text (default: text, NeMo manifest convention)",
    )
    parser.add_argument(
        "--hyp-field",
        default="pred_text",
        help="Field name for hypothesis text (default: pred_text)",
    )
    parser.add_argument(
        "--group-by",
        dest="group_by",
        default="source_dataset",
        metavar="FIELD",
        help="Record field whose value splits the per-group metrics "
        "(default: source_dataset; any field works, e.g. speaker)",
    )
    parser.add_argument(
        "--domain",
        default="legal",
        help="Bundled domain name (legal, medical, technical, none) or "
        "path to a domain config file (default: legal). A file whose "
        "name collides with a bundled name can be forced with a path "
        "prefix, e.g. ./legal",
    )
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Disable token normalization (strict matching)",
    )
    parser.add_argument(
        "--no-sandhi",
        action="store_true",
        help="Disable Sandhi merge/split detection (for non-agglutinative languages; "
        "merged or split compounds then count as ordinary errors)",
    )
    parser.add_argument(
        "--analysis",
        action="store_true",
        help="Enable detailed error analysis (contribution breakdown, frequent errors)",
    )
    parser.add_argument(
        "--top-n",
        type=parse_top_n,
        default=None,
        metavar="N|all",
        help=f"Frequent-error rows per table in {ANALYSIS_REPORT_NAME} "
        f"(default: all; the console shows at most {CONSOLE_ROW_CAP} per table)",
    )
    parser.add_argument(
        "--chart",
        action="store_true",
        help=f"Save the category breakdown chart as {CHART_NAME} (requires --analysis)",
    )
    parser.add_argument(
        "--workers",
        type=parse_workers,
        default=None,
        metavar="N|auto",
        help="Worker processes for parallel evaluation (default: auto = one per "
        "usable CPU, capped at the number of samples; results are identical "
        "whatever the count)",
    )
    parser.add_argument(
        "--skip-bad-records",
        action="store_true",
        help=(
            "Skip invalid JSONL lines and records with missing/null/non-string "
            "text fields (with a warning each) instead of stopping at the "
            "first bad one"
        ),
    )
    return parser


def _run(args: argparse.Namespace) -> int:
    print(f"Validating input file: {args.input}")
    input_path = validate_input_file(args.input)

    domain_config = resolve_domain(args.domain)
    if domain_config is None:
        print("Domain: none (base categories only)")
    else:
        print(f"Domain: {domain_config.name} (category: {domain_config.category})")

    output_dir = Path(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")

    detailed_output = output_dir / DETAILED_OUTPUT_NAME
    summary_output = output_dir / SUMMARY_REPORT_NAME

    n_records = count_records(input_path)
    workers = resolve_workers(args.workers, n_records)
    use_sandhi = not args.no_sandhi
    top_n_label = "all" if args.top_n is None else str(args.top_n)

    if args.chart and not args.analysis:
        print("Warning: --chart needs --analysis; no chart will be written.", file=sys.stderr)

    print(f"\nProcessing {input_path.name} ({n_records} records)...")
    print(f"Token normalization: {'disabled' if args.no_normalize else 'enabled'}")
    print(f"Sandhi detection: {'disabled' if args.no_sandhi else 'enabled'}")
    print(f"Workers: {workers}" + (" (auto)" if args.workers is None else ""))

    eval_start = time.perf_counter()
    results = compute_sample_errors(
        str(input_path),
        output_file=str(detailed_output),
        ref_field=args.ref_field,
        hyp_field=args.hyp_field,
        group_by=args.group_by,
        domain_config=domain_config,
        normalize=not args.no_normalize,
        use_sandhi=use_sandhi,
        collect_error_details=args.analysis,
        workers=workers,
        skip_bad_records=args.skip_bad_records,
    )
    eval_seconds = time.perf_counter() - eval_start

    # An all-skipped batch must not masquerade as a perfect evaluation
    # (0.00% summary, exit 0).
    if not results:
        print(
            "Error: no valid records evaluated — every record was skipped. "
            "Metrics were not computed.",
            file=sys.stderr,
        )
        return 1

    print("Computing aggregate metrics...")
    metrics = compute_aggregate_metrics(results)

    print("\n" + _RULE)
    print("EVALUATION SUMMARY")
    print(_RULE)
    print_evaluation_summary(metrics)

    run_info = (
        f"Evaluation completed in {eval_seconds:.1f}s "
        f"({len(results)} samples, workers={workers}, "
        f"sandhi={'on' if use_sandhi else 'off'}, "
        f"normalize={'off' if args.no_normalize else 'on'}, "
        f"domain={'none' if domain_config is None else domain_config.name}, "
        f"top_n={top_n_label}, scribe-eval {__version__})"
    )

    print(f"\nSaving summary to: {summary_output}")
    write_summary_to_file(metrics, str(summary_output))
    with open(summary_output, "a", encoding="utf-8") as f:
        f.write("\n" + run_info + "\n")
    print(f"Detailed results saved to: {detailed_output}")

    if args.analysis:
        all_error_details = aggregate_error_details(results)
        summary = compute_error_summary(metrics["overall"], all_error_details, top_n=args.top_n)
        overall_cer = metrics.get("cer_scribe", {}).get("overall", {}).get("cer_scribe")

        print()
        print(
            format_analysis_report(
                summary, args.top_n, cer_scribe=overall_cer, console_cap=CONSOLE_ROW_CAP
            ),
            end="",
        )

        analysis_output = output_dir / ANALYSIS_REPORT_NAME
        with open(analysis_output, "w", encoding="utf-8") as f:
            f.write(format_analysis_report(summary, args.top_n, cer_scribe=overall_cer))
        print(f"Analysis report saved to: {analysis_output}")

        if args.chart:
            try:
                from .charts import category_breakdown_chart

                chart_path = str(output_dir / CHART_NAME)
                category_breakdown_chart(
                    summary["contributions"], output_path=chart_path, cer_scribe=overall_cer
                )
                print(f"Category breakdown chart saved to: {chart_path}")
            except ImportError:
                print(
                    "Warning: matplotlib not installed, skipping chart generation.",
                    file=sys.stderr,
                )

    print("\n" + run_info)
    return 0


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    default_input: Optional[str] = None,
    default_output: str = DEFAULT_OUTPUT_DIR,
) -> int:
    """Entry point for ``scribe-batch``; returns the process exit code."""
    parser = build_parser(default_input=default_input, default_output=default_output)
    args = parser.parse_args(argv)

    try:
        return _run(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        if "skip_bad_records=True" in str(e):
            print("Hint: from this CLI, pass --skip-bad-records", file=sys.stderr)
        return 1
    except KeyError as e:
        print(f"Error: Missing required field in input data: {e}", file=sys.stderr)
        print(
            f"   Make sure your JSONL contains '{args.ref_field}' and '{args.hyp_field}' fields",
            file=sys.stderr,
        )
        return 1
    except Exception as e:  # keep the traceback for genuinely unexpected failures
        import traceback

        print(f"Unexpected error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
