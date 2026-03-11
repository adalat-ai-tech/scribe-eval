# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DictErrors is a specialized ASR (Automatic Speech Recognition) error analysis tool for Indic languages (Malayalam, Kannada) with domain-aware tokenization. It provides fine-grained error metrics by categorizing tokens into base categories (WORD, NUMERAL, PUNCT) plus optional domain-specific categories (LEGAL, MEDICAL, or custom domains). Domain-critical terminology is protected from incorrect splitting and tracked separately for error analysis.

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

# Text alignment visualization
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

# Test file-based domain configuration
python test_domain_config_file.py
```

### Interactive Visualization
```bash
streamlit run visualizer.py
```

The visualizer provides:
- **Manual Inspection Tab**: Single-sample text alignment and error analysis
- **Batch Dataset Analysis**: Upload JSONL files for aggregate metrics across datasets
- **Detailed Error Counts**: Expandable section showing substitutions, insertions, deletions by category
- **Individual Record Inspection**: Drill down into specific samples from batch results
- **Session State**: Maintains last 100 batch results with field name persistence
- **Sandhi Detection Toggle**: Sidebar checkbox to enable/disable Sandhi split/merge detection
- **Normalize Toggle**: Sidebar checkbox for token normalization (date/currency format variations)

## Architecture

### Core Pipeline Flow

1. **Tokenization** (`src/dicterrors/tokenize.py`, `src/dicterrors/domain_config.py`)
   - `domain_aware_tokenizer(text, domain_config=None)`: Main tokenization function
   - Base categories: WORD, NUMERAL, PUNCT (always present)
   - Optional domain categories via `DomainConfig` class
   - Factory methods for bundled domains: `DomainConfig.legal()`, `DomainConfig.medical()`, `DomainConfig.technical()`
   - File-based configuration: `DomainConfig.from_file('config/custom.txt')`
   - Custom domains: list-based patterns or regex patterns
   - Domain entities are protected from punctuation splitting and tracked separately
   - Numeral patterns: dates (DD-MM-YYYY), times (HH:MM), currency with commas

2. **Alignment** (`src/dicterrors/align.py`)
   - Modified Needleman-Wunsch algorithm with token-type-aware scoring
   - Cross-category substitution penalties (high penalty for punct ↔ word swaps)
   - Character-aware edit distance using Levenshtein for within-category errors
   - Sandhi correction detection (merged/split words in Indic text); toggled via `use_sandhi: bool = True`
   - Configurable weights via DEFAULT_WEIGHTS dict

3. **Measurement** (`src/dicterrors/measure.py`)
   - `token_error_rates(aligned_ref, aligned_hyp, domain_config=None, normalize=True, use_sandhi=True)`: Computes category-specific error rates from aligned tokens
   - `text_error_rates(ref_text, hyp_text, domain_config=None, normalize=True, use_sandhi=True)`: End-to-end pipeline from raw text to error metrics
   - `use_sandhi=False` disables Sandhi split/merge detection — useful for non-agglutinative languages
   - **Normalized error rates**: Uses combined denominator (sum of all category totals) across all categories to prevent misleading sparse-category metrics
   - **Domain-aware metrics**: WER (Word Error Rate), NER (Numeral Error Rate), PER (Punctuation Error Rate), plus domain-specific rates (e.g., LER for legal, MER for medical)
   - Tracks substitutions, insertions, deletions, and Sandhi corrections per category

4. **Batch Processing** (`src/dicterrors/measure_batch.py`)
   - `compute_sample_errors(input_file, output_file=None, domain_config=None, normalize=True, use_sandhi=True, ...)`: Process JSONL files with multiple samples
   - Optional `domain_config` parameter enables domain-specific error tracking
   - Optional `output_file` parameter saves detailed per-sample error reports as JSONL
   - Each detailed report includes category-wise breakdown (base + domain categories) with error rates, substitutions, insertions, deletions, correct counts, and Sandhi hits
   - `compute_aggregate_metrics(sample_results, domain_config=None)`: Dataset-level and overall aggregation
   - `print_evaluation_summary()`: Formatted output table with WER/NER/PER plus domain-specific rates (e.g., LER, MER)

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

**Domain Entity Shielding**: Domain-critical terminology (legal, medical, custom) is extracted before general tokenization to prevent incorrect splitting (e.g., "u/s" stays as one token, not "u", "/", "s"). Configurable via `DomainConfig` class with list or regex patterns.

**Category-Specific Gap Penalties**: Punctuation errors receive lighter penalties than word/legal/numeral errors in the alignment scoring, reflecting their lower semantic importance.

**Shared Reporting Module**: The `reporting.py` module eliminates code duplication between CLI tools and the Streamlit web UI by providing common formatting functions. This ensures consistent output presentation across all interfaces.

**Session State Persistence (Visualizer)**: The Streamlit visualizer stores field names (`ref_col`, `hyp_col`) alongside evaluation results in session state. This prevents NameError crashes when Streamlit re-runs the script (e.g., when clicking the file uploader). Field names are retrieved with `.get()` and fallback defaults ('reference', 'hypothesis') for robustness.

## File Organization

- `src/dicterrors/`: Core library modules
  - `__init__.py`: Public API exports
  - `config/`: Bundled domain configuration files (distributed with package)
    - `__init__.py`
    - `legal_terms.txt`: Indian legal terminology
    - `medical_terms.txt`: Medical units and dosages
    - `technical_terms.txt`: Technical abbreviations (case-sensitive)
  - `domain_config.py`: DomainConfig class with factory methods (`legal()`, `medical()`, `technical()`)
  - `tokenize.py`: Domain-aware token extraction and categorization
  - `align.py`: Alignment algorithm and scoring
  - `measure.py`: Single-sample error rate calculation
  - `measure_batch.py`: Multi-sample aggregation
  - `reporting.py`: Shared formatting functions for CLI and web UI
  - `constants.py`: Category constants and helper functions
- `config/`: User-facing example configs (not bundled)
  - `README.md`: Documentation and templates for custom domain configs
  - `*.txt`: Example configuration files for reference
- `examples/`: Sample scripts and evaluation datasets
  - `text_alignment.py`: Visual alignment demonstration
  - `error_report.py`: Single-sample error report generation
  - `custom_domain_file.py`: Demonstrates factory methods, file-based, and inline domain configs
  - `batch_evaluate.py`: Batch evaluation with detailed JSONL output
- `test_*.py`: Test suites (root level, not tracked in git)
- `visualizer.py`: Streamlit interactive UI (root level)
- `pyproject.toml`: Package configuration with uv

## Token Categories

**Base Categories (always present):**
- **WORD**: General words (Indic and English text)
- **NUMERAL**: Numbers, dates (22.05.2023), times (10:30), currency (10,500)
- **PUNCT**: Punctuation marks

**Domain Categories (configurable via DomainConfig):**
- **LEGAL**: Indian legal terminology (u/s, r/w, sec., art., v., vs., PW1/PW-1, CW1, Ext.A with flexible patterns)
- **MEDICAL**: Medical measurements and units (mg, ml, cc, mcg, IU, 500mg, 10ml)
- **TECH**: Technical abbreviations (API, SDK, CLI, JSON, HTTP, v1.0 - case-sensitive)
- **Custom**: Define your own domain with list or regex patterns

**Usage:**
```python
from dicterrors import domain_aware_tokenizer, DomainConfig

# Use factory method for bundled domain
legal_domain = DomainConfig.legal()
tokens, tags = domain_aware_tokenizer("charged u/s 302 IPC", legal_domain)

# Load from custom file
custom_domain = DomainConfig.from_file("config/my_legal.txt")
tokens, tags = domain_aware_tokenizer("my text", custom_domain)

# No domain (base categories only)
tokens, tags = domain_aware_tokenizer("regular text", None)

# Custom domain
custom = DomainConfig("custom", ["u/s", "r/w"], category="CUSTOM", label="CuER")
tokens, tags = domain_aware_tokenizer("charged u/s 302", custom)
```

## Loading Domain Patterns from Files

Domain-specific terminology can be loaded from text files, making it easy to maintain and share domain configurations without modifying code.

### File Format

Configuration files use a simple line-based format:

```
# Comments start with hash
@name: legal
@category: LEGAL
@label: LER
@case_sensitive: false

# Literal terms (one per line, automatically escaped for regex safety)
u/s
r/w
sec.

# Regex patterns (prefix with REGEX:, used directly without escaping)
REGEX: PW[-\s]*\d+     # Matches PW1, PW 1, PW-1
REGEX: CW[-\s]*\d+     # Matches CW1, CW 1, CW-1
```

**Format details:**
- **Metadata lines**: `@key: value` format (optional, uses sensible defaults if missing)
  - `@name`: Domain name (default: "domain")
  - `@category`: Category name for tokens (default: "DOMAIN_{NAME}")
  - `@label`: Short label for error rate (default: "{NAME}ER")
  - `@case_sensitive`: true/false (default: false)
- **Literal terms**: Plain text, one per line (automatically escaped with `re.escape()`)
- **Regex patterns**: Prefix with `REGEX:`, used directly without escaping
- **Comments**: Lines starting with `#` are ignored
- **Inline comments**: Text after `#` on any line is removed

### Loading from Python

```python
from dicterrors import DomainConfig, text_error_rates

# Load from file (uses all metadata from file)
legal_config = DomainConfig.from_file("config/legal_terms.txt")

# Override specific parameters at runtime
custom_config = DomainConfig.from_file(
    "config/legal_terms.txt",
    category="LEGAL_CUSTOM",
    case_sensitive=True
)

# Use in analysis
report = text_error_rates(ref, hyp, legal_config)
```

### Loading from CLI

The `batch_evaluate.py` script supports loading domain configs from files:

```bash
# Use file-based domain config
python batch_evaluate.py \
    --input data/predictions.jsonl \
    --domain-config config/legal_terms.txt

# Without --domain-config, uses DomainConfig.legal() by default
python batch_evaluate.py --input data/predictions.jsonl
```

### Sample Configuration Files

The `config/` directory contains pre-made configuration files:

- **`legal_terms.txt`**: Indian legal terminology with flexible witness designation patterns
  - Literal terms: u/s, r/w, sec., art., v., vs., etc.
  - Regex patterns: `PW[-\s]*\d+` matches PW1, PW 1, PW-1 (prosecution witness)
  - Regex patterns: `CW[-\s]*\d+` matches CW1, CW 1, CW-1 (court witness)
  - Regex patterns: `Ext\.[-\s]*[A-Z]\d*` matches Ext.A, Ext. A1, Ext-B2 (exhibits)

- **`medical_terms.txt`**: Medical units and dosages
  - Literal terms: mg, ml, cc, mcg, IU, kg, gm
  - Regex patterns: `\d+\s*mg` matches 500mg, 500 mg


- **`technical_terms.txt`**: Technical abbreviations (case-sensitive)
  - Literal terms: API, SDK, CLI, JSON, HTTP, HTTPS
  - Regex patterns: `v\d+\.\d+(?:\.\d+)?` matches v1.0, v2.3.4

### Pattern Matching Examples

The file format enables flexible pattern matching that handles spacing and formatting variations:

```python
from dicterrors import DomainConfig, domain_aware_tokenizer

# Load legal config with witness patterns
legal = DomainConfig.from_file("config/legal_terms.txt")

# All of these are recognized as LEGAL category:
tokens1, tags1 = domain_aware_tokenizer("witness PW1 testified", legal)
tokens2, tags2 = domain_aware_tokenizer("witness PW 1 testified", legal)  # Space between
tokens3, tags3 = domain_aware_tokenizer("witness PW-1 testified", legal)  # Hyphen

# All produce LEGAL tags
assert "LEGAL" in tags1
assert "LEGAL" in tags2
assert "LEGAL" in tags3
```

### File Location Conventions

- **Project configs**: Store in `config/` directory at repository root
- **User configs**: Store in `~/.config/dicterrors/` for personal configurations
- **Dataset-specific configs**: Store alongside dataset in data directory

Example directory structure:
```
project/
├── config/                     # Shared domain configs
│   ├── legal_terms.txt
│   ├── medical_terms.txt
│   └── custom_domain.txt
├── data/
│   ├── court-transcripts/
│   │   ├── predictions.jsonl
│   │   └── legal_terms.txt    # Dataset-specific overrides
│   └── medical-records/
│       └── predictions.jsonl
└── examples/
    └── batch_evaluate.py
```

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
--domain-config          Path to domain config file (e.g., config/legal_terms.txt)
--no-normalize           Disable token normalization (strict matching)
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
