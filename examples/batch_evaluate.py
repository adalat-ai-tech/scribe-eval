#!/usr/bin/env python3
"""
Batch evaluation script with CLI arguments and proper error handling.

Processes JSONL files containing reference and hypothesis pairs, computes
error metrics (WER/LER/NER/PER), and outputs detailed per-sample reports
and aggregate summaries.
"""
import os
import sys
import argparse
from pathlib import Path
from dicterrors import (
    compute_sample_errors,
    compute_aggregate_metrics,
    print_evaluation_summary,
    write_summary_to_file
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


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Batch evaluation of ASR predictions with detailed error analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use defaults (expects ./dictation-eval/predictions.jsonl)
  python batch_evaluate.py

  # Custom input file and output directory
  python batch_evaluate.py -i data/test.jsonl -o results/

  # Custom field names
  python batch_evaluate.py --ref-field reference --hyp-field hypothesis
        """
    )

    parser.add_argument(
        "-i", "--input",
        default="./dictation-eval/predictions.jsonl",
        help="Input JSONL file with predictions (default: ./dictation-eval/predictions.jsonl)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="./dictation-eval",
        help="Output directory for results (default: ./dictation-eval)"
    )
    parser.add_argument(
        "--ref-field",
        default="transcript_cleaned",
        help="Field name for reference text (default: transcript_cleaned)"
    )
    parser.add_argument(
        "--hyp-field",
        default="prediction",
        help="Field name for hypothesis text (default: prediction)"
    )
    parser.add_argument(
        "--dataset-field",
        default="source_dataset",
        help="Field name for dataset identifier (default: source_dataset)"
    )

    args = parser.parse_args()

    try:
        # 1. Validate input file
        print(f"Validating input file: {args.input}")
        input_path = validate_input_file(args.input)

        # 2. Create output directory
        output_dir = Path(args.output_dir)
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory: {output_dir}")

        # 3. Define output paths
        detailed_output = output_dir / "evaluation-detailed.jsonl"
        summary_output = output_dir / "summary_report.txt"

        # 4. Run analysis with optional field names
        print(f"\nProcessing {input_path.name}...")
        results = compute_sample_errors(
            str(input_path),
            output_file=str(detailed_output),
            ref_field=args.ref_field,
            hyp_field=args.hyp_field,
            source_dataset_field=args.dataset_field
        )

        # 5. Aggregate metrics with dataset splits
        print("Computing aggregate metrics...")
        metrics = compute_aggregate_metrics(results)

        # 6. Output to console
        print("\n" + "=" * 85)
        print("EVALUATION SUMMARY")
        print("=" * 85)
        print_evaluation_summary(metrics)

        # 7. Save summary to file (replaces unsafe stdout redirection)
        print(f"\nSaving summary to: {summary_output}")
        write_summary_to_file(metrics, str(summary_output))

        print(f"Detailed results saved to: {detailed_output}")
        print("\nEvaluation complete!")

    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"❌ Error: Missing required field in input data: {e}", file=sys.stderr)
        print(f"   Make sure your JSONL contains '{args.ref_field}' and '{args.hyp_field}' fields", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
