#!/usr/bin/env python3
"""
Batch evaluation script with CLI arguments and proper error handling.

Processes JSONL files containing reference and hypothesis pairs, computes
error metrics (ER_LEX/ER_DOMAIN/ER_NUM/ER_PUNCT), and outputs detailed per-sample reports
and aggregate summaries. With --analysis, provides additional insights:
the composite WER_SCRIBE, category contributions, and frequent error patterns.
"""

import argparse
import os
import sys
import time
from pathlib import Path

from tabulate import tabulate

from scribe import (
    DomainConfig,
    aggregate_error_details,
    compute_aggregate_metrics,
    compute_error_summary,
    compute_sample_errors,
    format_contribution_table,
    format_frequent_errors_table,
    print_evaluation_summary,
    write_summary_to_file,
)


def validate_input_file(input_file: str) -> Path:
    """
    Validate input file exists and is readable.

    Args:
        input_file: Path to input JSONL file

    Returns:
        Path object for the validated file

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is empty
    """
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
    """Resolve --domain: a bundled name (case-insensitive) wins, anything
    else must be a domain config file path. Returns None for 'none'."""
    key = value.lower()
    if key in BUNDLED_DOMAINS:
        return BUNDLED_DOMAINS[key]()
    if os.path.exists(value):
        return DomainConfig.from_file(value)
    raise ValueError(
        f"--domain {value!r} is neither a bundled domain "
        f"({', '.join(sorted(BUNDLED_DOMAINS))}) nor an existing config file"
    )


def print_analysis(summary, domain_config, top_n):
    """Print detailed error analysis to console."""
    print("\n" + "=" * 85)
    print("DETAILED ERROR ANALYSIS")
    print("=" * 85)

    # 1. Overall rates
    wer_scribe = summary["wer_scribe"]
    correct_pct = summary["total_correct_pct"]
    print(f"\nOverall: {correct_pct:.1f}% correct | {wer_scribe:.2%} WER_SCRIBE")

    # 2. Category Breakdown (correct/sub/del/ins per category)
    print("\n--- Token Breakdown by Category ---")
    contrib_rows = format_contribution_table(summary["contributions"])
    print(tabulate(contrib_rows, headers="keys", tablefmt="simple"))

    # 4. Frequent Substitutions
    freq_subs = summary["frequent_substitutions"]
    sub_rows = format_frequent_errors_table(freq_subs, "substitution", top_n)
    if sub_rows:
        print(f"\n--- Top {min(top_n, len(sub_rows))} Frequent Substitutions ---")
        print(tabulate(sub_rows, headers="keys", tablefmt="simple"))

    # 5. Frequent Deletions
    freq_dels = summary["frequent_deletions"]
    del_rows = format_frequent_errors_table(freq_dels, "deletion", top_n)
    if del_rows:
        print(f"\n--- Top {min(top_n, len(del_rows))} Frequent Deletions ---")
        print(tabulate(del_rows, headers="keys", tablefmt="simple"))

    # 6. Frequent Insertions
    freq_ins = summary["frequent_insertions"]
    ins_rows = format_frequent_errors_table(freq_ins, "insertion", top_n)
    if ins_rows:
        print(f"\n--- Top {min(top_n, len(ins_rows))} Frequent Insertions ---")
        print(tabulate(ins_rows, headers="keys", tablefmt="simple"))

    # 7. Frequent Sandhi Merges
    freq_merges = summary["frequent_sandhi_merges"]
    merge_rows = format_frequent_errors_table(freq_merges, "sandhi_merge", top_n)
    if merge_rows:
        print(f"\n--- Top {min(top_n, len(merge_rows))} Frequent Sandhi Merges ---")
        print(tabulate(merge_rows, headers="keys", tablefmt="simple"))

    # 8. Frequent Sandhi Splits
    freq_splits = summary["frequent_sandhi_splits"]
    split_rows = format_frequent_errors_table(freq_splits, "sandhi_split", top_n)
    if split_rows:
        print(f"\n--- Top {min(top_n, len(split_rows))} Frequent Sandhi Splits ---")
        print(tabulate(split_rows, headers="keys", tablefmt="simple"))

    print("\n" + "=" * 85)


def save_analysis_to_file(summary, output_path, domain_config, top_n):
    """Save analysis report to a text file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("DETAILED ERROR ANALYSIS\n")
        f.write("=" * 85 + "\n")

        wer_scribe = summary["wer_scribe"]
        correct_pct = summary["total_correct_pct"]
        f.write(f"\nOverall: {correct_pct:.1f}% correct | {wer_scribe:.2%} WER_SCRIBE\n")

        f.write("\n--- Token Breakdown by Category ---\n")
        contrib_rows = format_contribution_table(summary["contributions"])
        f.write(tabulate(contrib_rows, headers="keys", tablefmt="simple") + "\n")

        freq_subs = summary["frequent_substitutions"]
        sub_rows = format_frequent_errors_table(freq_subs, "substitution", top_n)
        if sub_rows:
            f.write(f"\n--- Top {min(top_n, len(sub_rows))} Frequent Substitutions ---\n")
            f.write(tabulate(sub_rows, headers="keys", tablefmt="simple") + "\n")

        freq_dels = summary["frequent_deletions"]
        del_rows = format_frequent_errors_table(freq_dels, "deletion", top_n)
        if del_rows:
            f.write(f"\n--- Top {min(top_n, len(del_rows))} Frequent Deletions ---\n")
            f.write(tabulate(del_rows, headers="keys", tablefmt="simple") + "\n")

        freq_ins = summary["frequent_insertions"]
        ins_rows = format_frequent_errors_table(freq_ins, "insertion", top_n)
        if ins_rows:
            f.write(f"\n--- Top {min(top_n, len(ins_rows))} Frequent Insertions ---\n")
            f.write(tabulate(ins_rows, headers="keys", tablefmt="simple") + "\n")

        freq_merges = summary["frequent_sandhi_merges"]
        merge_rows = format_frequent_errors_table(freq_merges, "sandhi_merge", top_n)
        if merge_rows:
            f.write(f"\n--- Top {min(top_n, len(merge_rows))} Frequent Sandhi Merges ---\n")
            f.write(tabulate(merge_rows, headers="keys", tablefmt="simple") + "\n")

        freq_splits = summary["frequent_sandhi_splits"]
        split_rows = format_frequent_errors_table(freq_splits, "sandhi_split", top_n)
        if split_rows:
            f.write(f"\n--- Top {min(top_n, len(split_rows))} Frequent Sandhi Splits ---\n")
            f.write(tabulate(split_rows, headers="keys", tablefmt="simple") + "\n")

        f.write("\n" + "=" * 85 + "\n")


def main():
    """Main entry point with CLI argument parsing."""
    # Default input and output sit alongside the script; resolve relative
    # to __file__ so the demo runs from any cwd (`uv run examples/batch_evaluate.py`
    # from the repo root works the same as `cd examples && uv run ...`).
    script_dir = Path(__file__).parent
    default_input = str(script_dir / "predictions.jsonl")
    default_output = str(script_dir / "output")

    parser = argparse.ArgumentParser(
        description="Batch evaluation of ASR predictions with detailed error analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use defaults (bundled sample data, writes to ./output/)
  python batch_evaluate.py

  # Custom input file and output directory
  python batch_evaluate.py -i data/test.jsonl -o results/

  # With detailed error analysis
  python batch_evaluate.py --analysis --top-n 15

  # Save charts alongside analysis
  python batch_evaluate.py --analysis --chart
        """,
    )

    parser.add_argument(
        "-i",
        "--input",
        default=default_input,
        help="Input JSONL file with predictions (default: bundled sample alongside this script)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=default_output,
        help="Output directory for results (default: examples/output/ alongside this script)",
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
        "--dataset-field",
        default="source_dataset",
        help="Field name for dataset identifier (default: source_dataset)",
    )
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Disable token normalization (strict matching)",
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
        "--analysis",
        action="store_true",
        help="Enable detailed error analysis (contribution breakdown, frequent errors)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top frequent errors to display (default: 10)",
    )
    parser.add_argument(
        "--chart",
        action="store_true",
        help="Save category breakdown chart as PNG (requires --analysis)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Worker processes for parallel evaluation (default: 1, sequential)",
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

    args = parser.parse_args()

    try:
        # 1. Validate input file
        print(f"Validating input file: {args.input}")
        input_path = validate_input_file(args.input)

        # 2. Resolve the domain: bundled name first, then file path
        try:
            domain_config = resolve_domain(args.domain)
        except (ValueError, Exception) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        if domain_config is None:
            print("Domain: none (base categories only)")
        else:
            print(f"Domain: {domain_config.name} (category: {domain_config.category})")

        # 3. Create output directory
        output_dir = Path(args.output_dir)
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory: {output_dir}")

        # 4. Define output paths
        detailed_output = output_dir / "evaluation-detailed.jsonl"
        summary_output = output_dir / "summary_report.txt"

        # 5. Run analysis with optional field names
        print(f"\nProcessing {input_path.name}...")
        print(f"Token normalization: {'disabled' if args.no_normalize else 'enabled'}")
        eval_start = time.perf_counter()
        results = compute_sample_errors(
            str(input_path),
            output_file=str(detailed_output),
            ref_field=args.ref_field,
            hyp_field=args.hyp_field,
            source_dataset_field=args.dataset_field,
            domain_config=domain_config,
            normalize=not args.no_normalize,
            collect_error_details=args.analysis,
            workers=args.workers,
            skip_bad_records=args.skip_bad_records,
        )
        eval_seconds = time.perf_counter() - eval_start

        # An all-skipped batch must not masquerade as a perfect
        # evaluation (0.00% summary, exit 0).
        if not results:
            print(
                "Error: no valid records evaluated — every record was skipped. "
                "Metrics were not computed.",
                file=sys.stderr,
            )
            sys.exit(1)

        # 6. Aggregate metrics with dataset splits
        print("Computing aggregate metrics...")
        metrics = compute_aggregate_metrics(results)

        # 7. Output to console
        print("\n" + "=" * 85)
        print("EVALUATION SUMMARY")
        print("=" * 85)
        print_evaluation_summary(metrics)

        # 8. Save summary to file
        print(f"\nSaving summary to: {summary_output}")
        write_summary_to_file(metrics, str(summary_output))

        print(f"Detailed results saved to: {detailed_output}")

        # 9. Detailed error analysis (when --analysis is active)
        if args.analysis:
            all_error_details = aggregate_error_details(results)
            summary = compute_error_summary(metrics["overall"], all_error_details, top_n=args.top_n)

            # Print to console
            print_analysis(summary, domain_config, args.top_n)

            # Save analysis report
            analysis_output = output_dir / "analysis_report.txt"
            save_analysis_to_file(summary, str(analysis_output), domain_config, args.top_n)
            print(f"Analysis report saved to: {analysis_output}")

            # Save charts if requested
            if args.chart:
                try:
                    from scribe.charts import category_breakdown_chart

                    breakdown_path = str(output_dir / "category_breakdown.png")
                    category_breakdown_chart(summary["contributions"], output_path=breakdown_path)
                    print(f"Category breakdown chart saved to: {breakdown_path}")

                except ImportError:
                    print(
                        "Warning: matplotlib not installed, skipping chart generation.",
                        file=sys.stderr,
                    )

        print(
            f"\nEvaluation completed in {eval_seconds:.1f}s "
            f"({len(results)} samples, workers={args.workers})"
        )

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        if "skip_bad_records=True" in str(e):
            print("Hint: from this CLI, pass --skip-bad-records", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing required field in input data: {e}", file=sys.stderr)
        print(
            f"   Make sure your JSONL contains '{args.ref_field}' and '{args.hyp_field}' fields",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
