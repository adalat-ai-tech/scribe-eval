# DictErrors - Dictation Error Analysis Tool [WIP]

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

DictErrors is a specialized tool for analyzing and evaluating speech recognition transcription errors, with particular focus on Indic languages such as Malayalam and Kannada. The tool provides fine-grained error analysis by categorizing errors into word, punctuation, numeral, and domain-specific categories.

**Key Innovation:** Domain-aware tokenization allows you to shield domain-critical terminology (legal, medical, financial, etc.) from incorrect splitting and track their errors separately.

## Features

- **Domain-Aware Tokenization**: Configure domain-critical terminology (legal, medical, financial, etc.) that should be:
  - Protected from punctuation splitting (e.g., "u/s" stays as one token)
  - Tagged with their domain category for separate error tracking
  - Supports both list-based patterns and regex patterns
  - Pre-defined configurations for legal and medical domains
  - Create custom domains for your specific use case

- **Advanced Token Alignment**: Utilizes dynamic programming with token-specific scoring to optimally align reference and hypothesis texts
  - High negative score for substituting punctuations with words or numbers
  - Character-aware substitutions using Levenshtein distance
  - Sandhi correction detection (merged/split words in Indic text)

- **Specialized Error Rates**:
  - **Word Error Rate (WER)**: Measures errors in general word tokens
  - **Domain Error Rate (DER)**: Tracks errors in domain-specific terminology (e.g., LER for legal, MER for medical)
  - **Numeral Error Rate (NER)**: Focuses on numerical token errors
  - **Punctuation Error Rate (PER)**: Specifically analyzes punctuation errors

- **Normalized Error Reporting**: Uses combined denominator across all categories to provide contextually meaningful error rates that account for class imbalance

- **Detailed Error Reports**: Generates comprehensive reports with substitutions, insertions, and deletions for each category

- **Flexible Configuration**: Works with any domain or no domain at all - adapts to your specific evaluation needs

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd dict-errors

# Create and activate a virtual environment using uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package using uv
uv pip install -e .
```

## Key Concepts

### Token Categories

Tokens are classified into base categories plus optional domain categories:

**Base Categories (always present):**
- **WORD**: General words (both Indic and English)
- **NUMERAL**: Numeric tokens including dates, times, and currency (123, 10:30, 22.05.2023)
- **PUNCT**: Punctuation marks

**Domain Categories (configurable via DomainConfig):**
- **LEGAL**: Indian legal terminology (u/s, r/w, sec., art., v., vs., PW1/PW-1, CW1, Ext.A)
- **MEDICAL**: Medical units and dosages (mg, ml, cc, mcg, IU, 500mg, 10ml)
- **CURRENCY**: Financial terms ($, €, ₹, USD, EUR, INR, $1,234.56)
- **TECH**: Technical abbreviations (API, SDK, CLI, JSON, HTTP, v1.0)
- **Custom**: Define your own domain with list or regex patterns

## Domain Configuration

DictErrors supports flexible domain-aware tokenization. Choose the approach that fits your workflow:

### Quick Start: Factory Methods

Use factory methods to load bundled domain configurations:

```python
from dicterrors import DomainConfig, text_error_rates

# Legal terminology (u/s, r/w, sec., PW1, CW2, Ext.A, etc.)
domain = DomainConfig.legal()
report = text_error_rates(ref, hyp, domain)

# Medical measurements (mg, ml, 500mg, 10ml, etc.)
domain = DomainConfig.medical()

# Financial terms ($, €, ₹, $1,234.56, etc.)
domain = DomainConfig.financial()

# Technical abbreviations (API, SDK, v1.0, etc.)
domain = DomainConfig.technical()
```

### Production: File-Based Configuration

Load custom domain configs from files for version control and team sharing:

```python
from dicterrors import DomainConfig, text_error_rates

# Load from your project's config file
domain = DomainConfig.from_file("config/custom_legal.txt")
report = text_error_rates(ref, hyp, domain)
```

**File Format** (`config/custom_legal.txt`):
```
# Domain configuration file
@name: legal
@category: LEGAL
@label: LER
@case_sensitive: false

# Literal terms (automatically escaped for regex safety)
u/s
r/w
sec.

# Regex patterns (prefix with REGEX:, used directly)
REGEX: PW[-\s]*\d+     # Matches PW1, PW 1, PW-1
REGEX: CW[-\s]*\d+     # Matches CW1, CW 1, CW-1
REGEX: Ext\.[-\s]*[A-Z]\d*  # Matches Ext.A, Ext. B2
```

**Metadata fields** (all optional with sensible defaults):
- `@name`: Domain identifier (default: "domain")
- `@category`: Token category name (default: "DOMAIN_{NAME}")
- `@label`: Short label for error rate metric (default: "{NAME}ER")
- `@case_sensitive`: Case-sensitive matching (default: false, accepts true/false/yes/no/1/0)

**Pattern types:**
- **Literal terms**: One per line, automatically escaped with `re.escape()` for safety
- **Regex patterns**: Prefix with `REGEX:`, used directly without escaping, supports full regex syntax
- **Comments**: Lines starting with `#` or text after `#` on any line

**Sample config files** are bundled with the package in `src/dicterrors/config/`:
- `legal_terms.txt` - Indian legal terminology
- `medical_terms.txt` - Medical units and dosages
- `financial_terms.txt` - Currency symbols and amounts
- `technical_terms.txt` - Technical abbreviations (case-sensitive)

You can copy and modify these for your projects. See `config/README.md` for detailed file format documentation.

### Custom Inline Domains

Create domains inline for quick experiments:

```python
from dicterrors import DomainConfig

# List-based patterns (automatically escaped)
financial = DomainConfig("financial", ["$", "€", "₹"], category="CURRENCY", label="CER")

# Regex patterns (used directly)
technical = DomainConfig("tech", r'API|SDK|CLI|v\d+\.\d+', category="TECH", label="TER")

# Use in evaluation
report = text_error_rates(ref, hyp, financial)
```

### No Domain

Use base categories only (WORD, NUMERAL, PUNCT) by passing `None`:

```python
# Explicit opt-out of domain tracking
report = text_error_rates(ref, hyp, None)
```

### Bundled Domain Configurations

DictErrors includes four pre-configured domains accessible via factory methods:

| Factory Method | Category | Label | Description |
|----------------|----------|-------|-------------|
| `DomainConfig.legal()` | LEGAL | LER | Indian legal terminology (u/s, r/w, sec., art., v., vs., PW1, CW2, Ext.A) with flexible witness/exhibit patterns |
| `DomainConfig.medical()` | MEDICAL | MER | Medical units and dosages (mg, ml, cc, mcg, IU, 500mg, 10ml patterns) |
| `DomainConfig.financial()` | CURRENCY | CER | Currency symbols and amounts ($, €, ₹, USD, EUR, INR, $1,234.56 patterns) |
| `DomainConfig.technical()` | TECH | TER | Technical abbreviations (API, SDK, CLI, JSON, HTTP, v1.0 patterns) - case-sensitive |

**Note:** Factory methods load from bundled config files. For customization, use `DomainConfig.from_file()` with your own files.

### Normalized Error Rates

Error rates are calculated using a combined denominator (sum of all token categories) to provide contextually meaningful metrics. This prevents misleading error rates for sparse categories (e.g., a single domain entity error doesn't show as 100% error rate).

**Formula:** Error Rate = (Category Errors) / (Total tokens across all categories)

For example, with legal domain:
- Error Rate = (Category Errors) / (WORD + NUMERAL + PUNCT + LEGAL tokens)

### Alignment Algorithm

Uses a modified Needleman-Wunsch algorithm with:
- Token-type-aware scoring (high penalties for cross-category substitutions)
- Character-aware edit distance for within-category substitutions
- Support for Sandhi correction tracking (merged/split word handling)

## Dependencies

- Python 3.11+
- Levenshtein 0.27.1+ (for string distance calculations)

### Managing Dependencies

This project uses uv for dependency management. To synchronize dependencies with the lockfile:

```bash
# Update dependencies according to the lockfile
uv sync

# Add a new dependency
uv pip install <package-name>

# Update the lockfile with new dependencies
uv pip freeze > requirements.txt
```


## Quick Start

### Basic Usage

```python
from dicterrors import text_error_rates, DomainConfig

# Analyze legal transcription
ref = "charged u/s 302 IPC on 22.05.2023"
hyp = "charged u/s 303 IPC on 22.05.2023"
domain = DomainConfig.legal()
report = text_error_rates(ref, hyp, domain)

# Access error rates
print(f"Word Error Rate: {report['WORD']['error_rate']:.2%}")
print(f"Legal Error Rate: {report['LEGAL']['error_rate']:.2%}")
print(f"Numeral Error Rate: {report['NUMERAL']['error_rate']:.2%}")
```

### Custom Domain

```python
from dicterrors import DomainConfig, text_error_rates

# Define medical domain
medical = DomainConfig("medical", ["mg", "ml", "cc", "IU"], label="MER")

# Analyze medical transcription
ref = "Administer 500mg twice daily"
hyp = "Administer 500 mg twice daily"
report = text_error_rates(ref, hyp, medical)

print(f"Medical Error Rate: {report['MEDICAL']['error_rate']:.2%}")
```

### Batch Processing

```python
from dicterrors import compute_sample_errors, compute_aggregate_metrics, DomainConfig

# Process JSONL file
domain = DomainConfig.legal()
results = compute_sample_errors(
    "predictions.jsonl",
    output_file="detailed_results.jsonl",
    domain_config=domain
)

# Get aggregate metrics
metrics = compute_aggregate_metrics(results, domain_config=domain)

# Access overall metrics
print(metrics['overall']['WORD']['error_rate'])
print(metrics['overall']['LEGAL']['error_rate'])

# Access per-dataset metrics
for dataset, data in metrics['by_dataset'].items():
    print(f"{dataset}: WER={data['WORD']['error_rate']:.2%}")
```

## Usage

### Text Alignment

```
cd examples/
uv run text_alignment.py
```

```bash
No text arguments provided. Using default examples...

=== MALAYALAM EXAMPLE 1 ===
Original texts:
Text 1: ആദ്യഗഡുവായി 180000 രൂപയായി നൽകിയത്.
Text 2: ആദ്യ ഗഡുവായി 180000 രൂപയായി നൽകിയത്:

Alignment (score: 12.5):
Text 1:     ആദ്യഗഡുവായി |          180000 |         രൂപയായി |         നൽകിയത് |               .
Text 2: SPLIT:ആദ്യ ഗഡുവായി |          180000 |         രൂപയായി |         നൽകിയത് |               :
```

### Error Analysis

```bash
cd examples/
uv run error_report.py
```

### Batch Evaluation

```bash
cd examples
uv run batch_evaluate.py
```

Processes multiple samples from a JSONL file and outputs aggregate metrics:

```
=====================================================================================
DATASET                   |      WER |      LER |      NER |      PER | SANDHI
-------------------------------------------------------------------------------------
OVERALL                   |    4.30% |    0.32% |    1.03% |    2.94% |      7
-------------------------------------------------------------------------------------
adalat-ai/Kathbath        |   10.53% |    0.00% |    0.00% |   14.04% |      2
adalat-ai/ulca-ml         |    3.23% |    0.00% |    0.00% |    6.45% |      3
master-audio              |    3.72% |    0.50% |    1.36% |    1.98% |      0
...
=====================================================================================
```

## Interactive Visualization

```bash
streamlit run visualizer.py
```

Launches a web-based interface with two main tabs:

### 1. Manual Inspection Tab

- Enter reference and hypothesis text directly
- View color-coded token alignment:
  - ✅ Green: Correct matches
  - ❌ Red: Errors (substitutions, insertions, deletions)
  - 🔄 Blue: Sandhi corrections (merged/split words)
- See category-specific error rates (WER, LER, NER, PER)
- Compare with baseline jiwer WER

### 2. Batch Dataset Analysis Tab

Upload a JSONL file with multiple samples to get:

**Overall Metrics:**
- Aggregate error rates across entire dataset
- Visual comparison with baseline WER
- Category-specific breakdown with Sandhi hit counts

**Per-Dataset Breakdown:**
- Table showing WER, LER, NER, PER for each source dataset
- Sandhi correction statistics

**Individual Record Inspection:**
- Dropdown to select specific samples
- Detailed alignment visualization for each record
- Error analysis at token level

**Features:**
- Color-coded alignment visualization
- Token category highlighting (WORD, LEGAL, NUMERAL, PUNCT)
- Error type indicators (substitution, insertion, deletion)
- Sandhi correction tracking


## Current Status

### ✅ Implemented
- **Domain-aware tokenization** with configurable patterns (list or regex)
- **File-based domain configuration** with bundled configs
- **Factory methods for pre-defined domains** (legal, medical, financial, technical)
- Pre-defined domains: Legal (LER), Medical (MER), Financial (CER), Technical (TER)
- Custom domain creation with `DomainConfig` class
- Token categorization (WORD, NUMERAL, PUNCT, + domain categories)
- Normalized error rates with combined denominator
- Sandhi correction tracking (merged/split words in Indic text)
- Interactive visualization with Streamlit
- Batch evaluation with dataset-level aggregation
- Comprehensive test suite
- Clean, flexible API

### 🚧 TODO
- Indic language legal entity detection (धारा, आईपीसी, अनुच्छेद, etc.) as pre-defined domain
- Extended legal entity patterns (case citations, acts, regulations)
- Character Error Rate (CER) reporting for substitutions
- Multi-domain support (track multiple domains simultaneously)

## API Reference

### Core Functions

**`domain_aware_tokenizer(text, domain_config=None)`**
- Tokenizes text with optional domain-aware entity shielding
- Returns: `(tokens, tags)` tuple

**`text_error_rates(ref_text, hyp_text, domain_config=None)`**
- End-to-end error rate calculation from raw text
- Returns: Dictionary with error metrics for each category

**`token_error_rates(aligned_ref, aligned_hyp, domain_config=None)`**
- Calculate error rates from pre-aligned tokens
- Returns: Dictionary with error metrics for each category

**`compute_sample_errors(input_file, output_file=None, domain_config=None, ...)`**
- Process JSONL file with multiple samples
- Returns: List of results with detailed reports

**`compute_aggregate_metrics(sample_results, domain_config=None)`**
- Aggregate metrics across samples
- Returns: Dictionary with 'overall' and 'by_dataset' metrics

### DomainConfig Factory Methods

Factory methods load bundled domain configurations from package resources:

**`DomainConfig.legal() -> DomainConfig`**
- Load bundled legal domain configuration
- Category: LEGAL, Label: LER
- Includes: u/s, r/w, sec., art., v., vs., PW1/PW-1/PW 1, CW1, Ext.A patterns

**`DomainConfig.medical() -> DomainConfig`**
- Load bundled medical domain configuration
- Category: MEDICAL, Label: MER
- Includes: mg, ml, cc, mcg, IU, 500mg, 10ml patterns

**`DomainConfig.financial() -> DomainConfig`**
- Load bundled financial domain configuration
- Category: CURRENCY, Label: CER
- Includes: $, €, ₹, USD, EUR, INR, $1,234.56 patterns

**`DomainConfig.technical() -> DomainConfig`**
- Load bundled technical domain configuration (case-sensitive)
- Category: TECH, Label: TER
- Includes: API, SDK, CLI, JSON, HTTP, v1.0 patterns

**`DomainConfig.from_file(file_path, ...) -> DomainConfig`**
- Load custom domain configuration from file
- See "Domain Configuration" section for file format details

### DomainConfig Class

```python
DomainConfig(
    name: str,                    # Domain name (e.g., "legal", "medical")
    patterns: Union[str, List[str]],  # Regex string or list of terms
    category: Optional[str] = None,   # Category name (default: "DOMAIN_{NAME}")
    label: Optional[str] = None,      # Error rate label (default: "{NAME}ER")
    case_sensitive: bool = False      # Case-sensitive matching
)
```

## Acknowledgements

This tool is developed as part of the Adalat AI initiative focusing on Indic language technologies.