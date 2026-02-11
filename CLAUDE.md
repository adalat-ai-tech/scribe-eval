# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DictErrors is a specialized ASR (Automatic Speech Recognition) error analysis tool focused on Indic languages (Malayalam, Kannada) with legal domain specialization. It provides fine-grained error metrics by categorizing tokens into WORD, LEGAL (English legal abbreviations), NUMERAL, and PUNCT categories.

## Commands

### Environment Setup
```bash
# Install dependencies with uv
uv sync

# Install package in development mode
uv pip install -e .
```

### Running Examples
```bash
cd examples/

# Text alignment visualization with match indicators
uv run text_alignment.py

# Single-sample error report generation
uv run error_report.py

# Batch evaluation with detailed per-sample JSONL output
uv run batch_evaluate.py

# Batch evaluation with custom arguments
uv run batch_evaluate.py \
    --input ./my-data/predictions.jsonl \
    --output-dir ./results \
    --ref-field reference \
    --hyp-field hypothesis

# Generates: evaluation-summary.txt and evaluation-detailed.jsonl
```

### Testing
```bash
# Note: Test files (test_*.py) are kept locally for development
# but are not tracked in git. Run tests from the repository root:

# Run basic functionality test
python test_combined_denominator.py

# Test edge cases
python test_edge_cases.py

# Test batch aggregation
python test_batch_aggregation.py

# Test reporting functions
python test_reporting.py
```

### Interactive Visualization
```bash
streamlit run visualizer.py
```

The visualizer provides:
- Manual inspection tab for single-sample analysis
- Batch dataset analysis with per-dataset breakdown
- **Detailed Error Counts** expandable section showing substitutions, insertions, deletions, and correct counts by category
- **Individual Record Inspection** section for analyzing specific records from batch results
- Session state management (limits to 100 most recent results)
  - Stores detailed results, global jiwer score, and field names (ref_col, hyp_col)
  - Field names persist across Streamlit re-runs to prevent NameError when file uploader is clicked
- Clear Session Data button for manual cleanup (removes all session state including field names)

## Architecture

### Core Pipeline Flow

1. **Tokenization** (`src/dicterrors/tokenize.py`)
   - Extracts and categorizes tokens into 4 categories: WORD, LEGAL, NUMERAL, PUNCT
   - Legal entity detection: u/s, r/w, sec., art., v., vs., PW, CW, etc.
   - Numeral patterns: dates (DD-MM-YYYY), times (HH:MM), currency with commas
   - Punctuation separation while preserving legal entities

2. **Alignment** (`src/dicterrors/align.py`)
   - Modified Needleman-Wunsch algorithm with token-type-aware scoring
   - Cross-category substitution penalties (high penalty for punct ↔ word swaps)
   - Character-aware edit distance using Levenshtein for within-category errors
   - Sandhi correction detection (merged/split words in Indic text)
   - Configurable weights via DEFAULT_WEIGHTS dict

3. **Measurement** (`src/dicterrors/measure.py`)
   - `token_error_rates()`: Computes category-specific error rates from aligned tokens
   - `text_error_rates()`: End-to-end pipeline from raw text to error metrics
   - **Normalized error rates**: Uses combined denominator (sum of all category totals) across all categories to prevent misleading sparse-category metrics
   - Tracks substitutions, insertions, deletions, and Sandhi corrections per category

4. **Batch Processing** (`src/dicterrors/measure_batch.py`)
   - `compute_sample_errors()`: Process JSONL files with multiple samples
   - Optional `output_file` parameter saves detailed per-sample error reports as JSONL
   - Each detailed report includes category-wise breakdown (WORD/LEGAL/NUMERAL/PUNCT) with error rates, substitutions, insertions, deletions, correct counts, and Sandhi hits
   - `compute_aggregate_metrics()`: Dataset-level and overall aggregation
   - `print_evaluation_summary()`: Formatted output table with WER/LER/NER/PER

5. **Reporting** (`src/dicterrors/reporting.py`)
   - Shared formatting functions used across CLI and web UI
   - `format_metrics_dict()`: Convert error metrics to formatted dictionary (returns formatted strings)
   - `extract_error_rates()`: Extract raw numeric error rates (WER/LER/NER/PER/Sandhi) for UI components
   - `format_dataset_table()`: Create dataset-level summary tables
   - `format_error_counts_table()`: Format error counts by category
   - `format_alignment_table()`: Visual alignment display with match indicators
   - `format_alignment_dict()`: Shared error detection logic returning structured data
   - `write_summary_to_file()`: Safe file writing for evaluation summaries

### Key Design Decisions

**Combined Denominator Approach**: Error rates are calculated as `(Category Errors) / (Total ALL tokens)` instead of `(Category Errors) / (Category tokens)`. This prevents misleading percentages when a category has very few instances (e.g., 1 legal entity error shouldn't show as 100% LER).

**Sandhi Awareness**: The alignment algorithm detects when Indic words are incorrectly merged or split by ASR systems. These are tracked separately as they represent different error types than pure substitutions.

**Legal Entity Shielding**: Legal abbreviations are extracted before general tokenization to prevent them from being split incorrectly (e.g., "u/s" stays as one token, not "u", "/", "s").

**Category-Specific Gap Penalties**: Punctuation errors receive lighter penalties than word/legal/numeral errors in the alignment scoring, reflecting their lower semantic importance.

**Shared Reporting Module**: The `reporting.py` module eliminates code duplication between CLI tools and the Streamlit web UI by providing common formatting functions. This ensures consistent output presentation across all interfaces.

**Session State Persistence (Visualizer)**: The Streamlit visualizer stores field names (`ref_col`, `hyp_col`) alongside evaluation results in session state. This prevents NameError crashes when Streamlit re-runs the script (e.g., when clicking the file uploader). Field names are retrieved with `.get()` and fallback defaults ('reference', 'hypothesis') for robustness.

## File Organization

- `src/dicterrors/`: Core library modules
  - `__init__.py`: Public API exports
  - `tokenize.py`: Token extraction and categorization
  - `align.py`: Alignment algorithm and scoring
  - `measure.py`: Single-sample error rate calculation
  - `measure_batch.py`: Multi-sample aggregation
  - `reporting.py`: Shared formatting functions for CLI and web UI
- `examples/`: Sample scripts and evaluation datasets
  - `text_alignment.py`: Visual alignment demonstration
  - `error_report.py`: Single-sample error report generation
  - `batch_evaluate.py`: Batch evaluation with detailed JSONL output
- `test_*.py`: Test suites (root level, not tracked in git)
- `visualizer.py`: Streamlit interactive UI (root level)
- `pyproject.toml`: Package configuration with uv

## Token Categories

- **WORD**: General words (Indic and English text)
- **LEGAL**: English legal abbreviations (u/s, r/w, w.p., o.s., sec., art., v., vs., PW, CW)
- **NUMERAL**: Numbers, dates (22.05.2023), times (10:30), currency (10,500)
- **PUNCT**: Punctuation marks

## JSONL Input Format

Batch evaluation expects JSONL files with these fields:
- `transcript_cleaned`: Reference text (ground truth)
- `prediction`: Hypothesis text (ASR output)
- `source_dataset`: Dataset identifier (optional, defaults to "unknown")

### Batch Evaluation CLI Arguments

The `batch_evaluate.py` script supports flexible configuration via command-line arguments:

```bash
# Show help
python batch_evaluate.py --help

# Common options:
-i, --input              Input JSONL file path (default: ./dictation-eval/predictions.jsonl)
-o, --output-dir         Output directory for results (default: ./dictation-eval)
--ref-field              Field name for reference text (default: transcript_cleaned)
--hyp-field              Field name for hypothesis text (default: prediction)
--dataset-field          Field name for dataset identifier (default: source_dataset)
```

The script includes:
- Input file validation (existence, readability, non-empty)
- Comprehensive error handling with friendly error messages
- Automatic output directory creation
- Safe file writing without stdout redirection

## Detailed JSONL Output Format

When using `batch_evaluate.py` with the `output_file` parameter, detailed per-sample reports are saved as JSONL. Each line contains:
- `sample_id`: Sequential sample number
- `source_dataset`: Dataset identifier
- `reference`: Original reference text
- `hypothesis`: Original hypothesis text
- `WORD`, `LEGAL`, `NUMERAL`, `PUNCT`: Category-specific dictionaries with:
  - `error_rate`: Normalized error rate (errors / total tokens)
  - `substitutions`: Number of substitution errors
  - `insertions`: Number of insertion errors
  - `deletions`: Number of deletion errors
  - `correct`: Number of correctly recognized tokens
  - `sandhi_hits`: Number of Sandhi corrections detected (for WORD category)

## Dependencies

This project uses `uv` for dependency management. Core dependencies:
- `levenshtein>=0.27.1`: Character-level edit distance
- `jiwer>=4.0.0`: Baseline WER comparison
- `streamlit>=1.53.0`: Interactive visualization
- `tabulate>=0.9.0`: Formatted table output

## Visualizer Implementation Details

### Session State Management

The Streamlit visualizer (`visualizer.py`) uses session state to preserve results across script re-runs. Key implementation details:

**Stored in session state:**
- `detailed_results`: List of per-sample error dictionaries (limited to 100 most recent)
- `global_jiwer`: Overall jiwer WER score for the batch
- `ref_col`: Field name used for reference text (e.g., "transcript_cleaned")
- `hyp_col`: Field name used for hypothesis text (e.g., "prediction")

**Why store field names:**
- Streamlit re-runs the entire script on every user interaction (including clicking file uploader)
- Field names (`ref_col`, `hyp_col`) are only defined when records are loaded
- Individual Record Inspection section needs these names to display stored results
- Without session storage, accessing stored results after clicking uploader causes NameError

**Implementation pattern:**
```python
# Store when saving results (visualizer.py:289-294)
st.session_state['detailed_results'] = res_detailed[-MAX_STORED_RESULTS:]
st.session_state['global_jiwer'] = jiwer_wer
st.session_state['ref_col'] = ref_col
st.session_state['hyp_col'] = hyp_col

# Retrieve when displaying individual records (visualizer.py:302-310)
saved_ref_col = st.session_state.get('ref_col', 'reference')
saved_hyp_col = st.session_state.get('hyp_col', 'hypothesis')
```

**Safety features:**
- Uses `.get()` with fallback defaults to handle edge cases
- Clear Session Data button removes all session state keys
- Prevents KeyError if session state is corrupted or manually modified
