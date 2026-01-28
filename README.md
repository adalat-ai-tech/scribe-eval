# DictErrors - Dictation Error Analysis Tool [WIP]

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

DictErrors is a specialized tool for analyzing and evaluating speech recognition transcription errors, with particular focus on Indic languages such as Malayalam and Kannada. The tool provides fine-grained error analysis by categorizing errors into word, punctuation, and numeral-specific categories.

## Features

- **Advanced Token Alignment**: Utilizes dynamic programming with token-specific scoring to optimally align reference and hypothesis texts
  - High negative score for substituting punctuations with words or numbers.
  - Character aware substitutions
- **Specialized Error Rates**:
  - **Word Error Rate (WER)**: Measures errors in general word tokens
  - **Legal Error Rate (LER)**: Tracks errors in English legal abbreviations (u/s, r/w, sec., etc.)
  - **Numeral Error Rate (NER)**: Focuses on numerical token errors
  - **Punctuation Error Rate (PER)**: Specifically analyzes punctuation errors
- **Normalized Error Reporting**: Uses combined denominator across all categories to provide contextually meaningful error rates that account for class imbalance
- **Detailed Error Reports**: Generates comprehensive reports with substitutions, insertions, and deletions for each category
- **Language-Specific Tokenization**: Handles Indic scripts with English legal entity detection

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

Tokens are classified into four categories:
- **WORD**: General words (both Indic and English)
- **LEGAL**: English legal abbreviations (u/s, r/w, w.p., o.s., sec., art., v., vs., PW, CW)
- **NUMERAL**: Numeric tokens including dates, times, and currency (123, 10:30, 22.05.2023)
- **PUNCT**: Punctuation marks

### Normalized Error Rates

Error rates are calculated using a combined denominator (sum of all token categories) to provide contextually meaningful metrics. This prevents misleading error rates for sparse categories (e.g., a single legal entity error doesn't show as 100% error rate).

**Formula:** Error Rate = (Category Errors) / (Total WORD + LEGAL + NUMERAL + PUNCT tokens)

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
- Token categorization (WORD, LEGAL, NUMERAL, PUNCT)
- English legal abbreviation detection (u/s, r/w, sec., etc.)
- Normalized error rates with combined denominator
- Sandhi correction tracking (merged/split words)
- Interactive visualization with Streamlit
- Batch evaluation with dataset-level aggregation
- Comprehensive test suite

### 🚧 TODO
- Indic language legal entity detection (धारा, आईपीसी, अनुच्छेद, etc.)
- Generic tokenizer with configurable language-specific features
- Language code parameter for tokenizer
- Extended legal entity patterns (case citations, acts, regulations)
- Character Error Rate (CER) reporting for substitutions


## Acknowledgements

This tool is developed as part of the Adalat AI initiative focusing on Indic language technologies.