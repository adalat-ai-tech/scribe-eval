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

**Domain Categories (configurable):**
- **LEGAL**: English legal abbreviations (u/s, r/w, w.p., o.s., sec., art., v., vs., PW, CW)
- **MEDICAL**: Medical terms (mg, ml, cc, mcg, IU, units)
- **Custom**: Define your own domain with list or regex patterns

### Domain Configuration

DictErrors supports flexible domain-aware tokenization:

```python
from dicterrors import DomainConfig, domain_aware_tokenizer, text_error_rates

# Use pre-defined legal domain
from dicterrors import LEGAL_DOMAIN
tokens, tags = domain_aware_tokenizer("charged u/s 302 IPC", LEGAL_DOMAIN)
# tokens: ["charged", "u/s", "302", "IPC"]
# tags: ["WORD", "LEGAL", "NUMERAL", "WORD"]

# Use pre-defined medical domain
from dicterrors import MEDICAL_DOMAIN
tokens, tags = domain_aware_tokenizer("Take 500mg daily", MEDICAL_DOMAIN)
# tokens: ["Take", "500mg", "daily"]
# tags: ["WORD", "MEDICAL", "WORD"]

# Create custom domain with list of terms
financial = DomainConfig("financial", ["$", "€", "₹"], category="CURRENCY", label="CER")
tokens, tags = domain_aware_tokenizer("Pay $100", financial)
# tokens: ["Pay", "$", "100"]
# tags: ["WORD", "CURRENCY", "NUMERAL"]

# Create custom domain with regex
technical = DomainConfig("tech", r'API|SDK|CLI|JSON|HTTP[S]?', category="TECH", label="TER")

# No domain (only base categories)
tokens, tags = domain_aware_tokenizer("Regular text", None)
# tags will only be: ["WORD", "WORD"]
```

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
from dicterrors import text_error_rates, LEGAL_DOMAIN

# Analyze legal transcription
ref = "charged u/s 302 IPC on 22.05.2023"
hyp = "charged u/s 303 IPC on 22.05.2023"
report = text_error_rates(ref, hyp, LEGAL_DOMAIN)

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
from dicterrors import compute_sample_errors, compute_aggregate_metrics, LEGAL_DOMAIN

# Process JSONL file
results = compute_sample_errors(
    "predictions.jsonl",
    output_file="detailed_results.jsonl",
    domain_config=LEGAL_DOMAIN
)

# Get aggregate metrics
metrics = compute_aggregate_metrics(results, domain_config=LEGAL_DOMAIN)

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
=== MALAYALAM EXAMPLE ===
Original texts:
Text 1: പണം അക്കൗണ്ടിൽ എത്തിയപ്പോൾ ആദ്യ, ഗഡുവായി 180000 രൂപയായി നൽകിയത്.
Text 2: പണം അക്കൗണ്ടിൽ എത്തിയപ്പോൾ, ആദ്യ ഘടുവായി 180000 രൂപയാണ് നൽകിയത്:

Alignment (score: 9.0):
Text 1:        പണം | അക്കൗണ്ടിൽ | എത്തിയപ്പോൾ |         ** |       ആദ്യ |          , |    ഗഡുവായി |     180000 |    രൂപയായി |    നൽകിയത് |          .
Match:           ✓ |          ✓ |          ✓ |            |          ✓ |            |          ✗ |          ✓ |          ✗ |          ✓ |          ✗
Text 2:        പണം | അക്കൗണ്ടിൽ | എത്തിയപ്പോൾ |          , |       ആദ്യ |         ** |    ഘടുവായി |     180000 |    രൂപയാണ് |    നൽകിയത് |          :



=== KANNADA EXAMPLE ===
Original texts:
Text 1: 10 ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ।
Text 2: ಹತ್ತು ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ.

Alignment (score: 19.5):
Text 1:         ** |         10 |    ವರ್ಷವಾದ |   ಮಕ್ಕಳಿಗೆ |        ಅದರ |       ಒಂದು |     ಸ್ವಲ್ಪ |      ಜ್ಞಾನ |    ಮನವರಿಕೆ |       ಒಂದು |    ಪ್ರಾರಂಭ |  ಆಗುತ್ತದೆ। |         **
Match:             |            |          ✓ |          ✓ |          ✓ |          ✓ |          ✓ |          ✓ |          ✓ |          ✓ |          ✓ |          ✗ |           
Text 2:      ಹತ್ತು |         ** |    ವರ್ಷವಾದ |   ಮಕ್ಕಳಿಗೆ |        ಅದರ |       ಒಂದು |     ಸ್ವಲ್ಪ |      ಜ್ಞಾನ |    ಮನವರಿಕೆ |       ಒಂದು |    ಪ್ರಾರಂಭ |   ಆಗುತ್ತದೆ |          .





=== ENGLISH EXAMPLE ===
Original texts:
Text 1: The brown quick fox jumps over the lazy dogs.
Text 2: The bron fox jumps over a lazy, dog

Alignment (score: 1.5):
Text 1:        The |      brown |      quick |        fox |      jumps |       over |        the |       lazy |         ** |       dogs |          .
Match:           ✓ |          ✗ |            |          ✓ |          ✓ |          ✓ |          ✗ |          ✓ |            |          ✗ |           
Text 2:        The |       bron |         ** |        fox |      jumps |       over |          a |       lazy |          , |        dog |         **



=== ENGLISH EXAMPLE ===
Original texts:
Text 1: The quick brown fox jumps over the lazy dog.
Text 2: The bron fox jumps over a lazy dog

Alignment (score: 7.5):
Text 1:        The |      quick |      brown |        fox |      jumps |       over |        the |       lazy |        dog |          .
Match:           ✓ |            |          ✗ |          ✓ |          ✓ |          ✓ |          ✗ |          ✓ |          ✓ |           
Text 2:        The |         ** |       bron |        fox |      jumps |       over |          a |       lazy |        dog |         **

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

## Testing

The project includes comprehensive test suites to verify correctness:

### Basic Functionality Test

```bash
python test_combined_denominator.py
```

Verifies that error rates are calculated correctly with known test values. Tests the core calculation logic with a controlled example (100 WORD, 1 LEGAL, 10 NUMERAL, 15 PUNCT tokens).

### Edge Case Tests

```bash
python test_edge_cases.py
```

Validates the system handles corner cases correctly:
- Zero tokens in some categories (e.g., no legal entities in text)
- Only one category has tokens
- Empty samples (no tokens at all)
- Large class imbalance (10,000:1:5:50 ratio)
- Insertions and deletions

### Batch Aggregation Test

```bash
python test_batch_aggregation.py
```

Ensures that metrics aggregate correctly across multiple samples and datasets, verifying both overall and per-dataset statistics use the combined denominator approach.

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
- Pre-defined domains: Legal (LER) and Medical (MER)
- Custom domain creation with `DomainConfig` class
- Token categorization (WORD, NUMERAL, PUNCT, + domain categories)
- Normalized error rates with combined denominator
- Sandhi correction tracking (merged/split words in Indic text)
- Interactive visualization with Streamlit
- Batch evaluation with dataset-level aggregation
- Comprehensive test suite
- Clean, flexible API without backward compatibility baggage

### 🚧 TODO
- Indic language legal entity detection (धारा, आईपीसी, अनुच्छेद, etc.) as pre-defined domain
- Extended legal entity patterns (case citations, acts, regulations)
- Character Error Rate (CER) reporting for substitutions
- Multi-domain support (track multiple domains simultaneously)
- Domain pattern suggestions based on corpus analysis


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

### Pre-defined Domains

**`LEGAL_DOMAIN`**: English legal abbreviations (u/s, r/w, sec., art., v., vs., PW, CW, Ext.)

**`MEDICAL_DOMAIN`**: Medical measurements (mg, ml, cc, mcg, plus numeric patterns like 500mg)

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