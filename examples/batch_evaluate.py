#!/usr/bin/env python3
"""
Batch evaluation script with CLI arguments and proper error handling.

Processes JSONL files containing reference and hypothesis pairs, computes
error metrics (WER/LER/NER/PER), and outputs detailed per-sample reports
and aggregate summaries. With --analysis, provides additional insights:
total error rate, category contributions, and frequent error patterns.
"""

import argparse
import os
import sys
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


def print_analysis(summary, domain_config, top_n):
    """Print detailed error analysis to console."""
    print("\n" + "=" * 85)
    print("DETAILED ERROR ANALYSIS")
    print("=" * 85)

    # 1. Overall rates
    ter = summary["total_error_rate"]
    correct_pct = summary["total_correct_pct"]
    print(f"\nOverall: {correct_pct:.1f}% correct | {ter:.2%} TER")

    # 2. Category Breakdown (correct/sub/del/ins per category)
    print("\n--- Token Breakdown by Category ---")
    contrib_rows = format_contribution_table(summary["contributions"], domain_config)
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

    print("\n" + "=" * 85)


def save_analysis_to_file(summary, output_path, domain_config, top_n):
    """Save analysis report to a text file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("DETAILED ERROR ANALYSIS\n")
        f.write("=" * 85 + "\n")

        ter = summary["total_error_rate"]
        correct_pct = summary["total_correct_pct"]
        f.write(f"\nOverall: {correct_pct:.1f}% correct | {ter:.2%} TER\n")

        f.write("\n--- Token Breakdown by Category ---\n")
        contrib_rows = format_contribution_table(summary["contributions"], domain_config)
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

        f.write("\n" + "=" * 85 + "\n")


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Batch evaluation of ASR predictions with detailed error analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use defaults (reads ./predictions.jsonl, writes to ./output/)
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
        default="./predictions.jsonl",
        help="Input JSONL file with predictions (default: ./predictions.jsonl)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="./output",
        help="Output directory for results (default: ./output)",
    )
    parser.add_argument(
        "--ref-field",
        default="transcript_cleaned",
        help="Field name for reference text (default: transcript_cleaned)",
    )
    parser.add_argument(
        "--hyp-field",
        default="prediction",
        help="Field name for hypothesis text (default: prediction)",
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
        "--domain-config",
        default=None,
        help="Path to domain config file (e.g., config/legal_terms.txt). "
        "If not provided, uses DomainConfig.legal().",
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

    args = parser.parse_args()

    try:
        # 1. Validate input file
        print(f"Validating input file: {args.input}")
        input_path = validate_input_file(args.input)

        # 2. Load domain configuration
        domain_config = DomainConfig.legal()  # Default
        if args.domain_config:
            try:
                print(f"Loading domain config from: {args.domain_config}")
                domain_config = DomainConfig.from_file(args.domain_config)
                print(
                    f"Loaded domain config: {domain_config.name} "
                    f"(category: {domain_config.category}, label: {domain_config.label})"
                )
            except FileNotFoundError:
                print(
                    f"Error: Domain config file not found: {args.domain_config}",
                    file=sys.stderr,
                )
                sys.exit(1)
            except (ValueError, Exception) as e:
                print(f"Error loading domain config: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(
                f"Using default domain config: {domain_config.name} "
                f"(category: {domain_config.category})"
            )

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
        results = compute_sample_errors(
            str(input_path),
            output_file=str(detailed_output),
            ref_field=args.ref_field,
            hyp_field=args.hyp_field,
            source_dataset_field=args.dataset_field,
            domain_config=domain_config,
            normalize=not args.no_normalize,
            collect_error_details=args.analysis,
        )

        # 6. Aggregate metrics with dataset splits
        print("Computing aggregate metrics...")
        metrics = compute_aggregate_metrics(results, domain_config=domain_config)

        # 7. Output to console
        print("\n" + "=" * 85)
        print("EVALUATION SUMMARY")
        print("=" * 85)
        print_evaluation_summary(metrics, domain_config=domain_config)

        # 8. Save summary to file
        print(f"\nSaving summary to: {summary_output}")
        write_summary_to_file(metrics, str(summary_output), domain_config=domain_config)

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

        print("\nEvaluation complete!")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
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
