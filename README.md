# DictErrors - Dictation Error Analysis Tool [WIP]

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

DictErrors is a specialized tool for analyzing and evaluating speech recognition transcription errors, with particular focus on Indic languages such as Malayalam and Kannada. The tool provides fine-grained error analysis by categorizing errors into word, punctuation, and numeral-specific categories.

## Features

- **Advanced Token Alignment**: Utilizes dynamic programming with language-specific scoring to optimally align reference and hypothesis texts
- **Specialized Error Rates**:
  - **Word Error Rate (WER)**: Measures errors in word tokens
  - **Punctuation Error Rate (PER)**: Specifically analyzes punctuation errors
  - **Numeral Error Rate (NER)**: Focuses on numerical token errors
- **Detailed Error Reports**: Generates comprehensive reports with substitutions, insertions, and deletions for each category
- **Language-Specific Tokenization**: Provides specialized tokenizers for Indic languages

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

## Algorithm Overview

The alignment algorithm uses a modified version of the Needleman-Wunsch algorithm with specialized scoring functions to handle different token types (words, punctuation, and numbers) in Indic languages. The error rates are calculated by comparing the aligned tokens and categorizing them based on token type.

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

Alignment (score: 19.0):
Text 1:         10 |    ವರ್ಷವಾದ |   ಮಕ್ಕಳಿಗೆ |        ಅದರ |       ಒಂದು |     ಸ್ವಲ್ಪ |      ಜ್ಞಾನ |    ಮನವರಿಕೆ |       ಒಂದು |    ಪ್ರಾರಂಭ |  ಆಗುತ್ತದೆ। |         **
Match:           ✗ |          ✓ |          ✓ |          ✓ |          ✓ |          ✓ |          ✓ |          ✓ |          ✓ |          ✓ |          ✗ |           
Text 2:      ಹತ್ತು |    ವರ್ಷವಾದ |   ಮಕ್ಕಳಿಗೆ |        ಅದರ |       ಒಂದು |     ಸ್ವಲ್ಪ |      ಜ್ಞಾನ |    ಮನವರಿಕೆ |       ಒಂದು |    ಪ್ರಾರಂಭ |   ಆಗುತ್ತದೆ |          .



=== ENGLISH EXAMPLE ===
Original texts:
Text 1: The brown quick fox jumps over the lazy dog.
Text 2: The bron fox jumps over a lazy, dog

Alignment (score: 6.5):
Text 1:        The |      brown |      quick |        fox |      jumps |       over |        the |       lazy |         ** |        dogs|          .
Match:           ✓ |          ✗ |            |          ✓ |          ✓ |          ✓ |          ✗ |          ✓ |            |            |           
Text 2:        The |       bron |         ** |        fox |      jumps |       over |          a |       lazy |          , |        dog |         **



=== ENGLISH EXAMPLE ===
Original texts:
Text 1: The quick brown fox jumps over the lazy dog.
Text 2: The bron fox jumps over a lazy dog

Alignment (score: 7.5):
Text 1:        The |      quick |      brown |        fox |      jumps |       over |        the |       lazy |        dog |          .
Match:           ✓ |            |          ✗ |          ✓ |          ✓ |          ✓ |          ✗ |          ✓ |          ✓ |           
Text 2:        The |         ** |       bron |        fox |      jumps |       over |          a |       lazy |        dog |         **


### Error Analysis

```
cd examples/
uv run error_report.py
```

### Batch Evaluation

```
cd examples/
uv run evaluate.py
```


## Acknowledgements

This tool is developed as part of the Adalat AI initiative focusing on Indic language technologies.