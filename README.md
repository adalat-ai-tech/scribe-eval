# DictErrors - Dictation Error Analysis Tool [WIP]

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

DictErrors is a specialized tool for analyzing and evaluating speech recognition transcription errors, with particular focus on Indic languages such as Malayalam and Kannada. The tool provides fine-grained error analysis by categorizing errors into word, punctuation, and numeral-specific categories.

## Features

- **Advanced Token Alignment**: Utilizes dynamic programming with token-specific scoring to optimally align reference and hypothesis texts
  - High negative score for substituting punctuations with words or numbers.
  - Character aware substitutions
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

For the Hindi strings:

```
text1 = "भारत एक महान राष्ट्र है"
text2 = "भारत, महान राष्ट्र है"
```

Regular alignemnet algorithms in [jiwer](https://github.com/jitsi/jiwer) and [kaldialign](https://github.com/rhasspy/kaldi-align) gives the alignment as:

```
Array 1:       भारत |         एक |      महान |    राष्ट्र |         है
Match:            ✓ |          ✗ |           ✓ |          ✓ |          ✓
Array 2:       भारत |          , |        महान |    राष्ट्र |         है
```

Our algorithm gives the alignment as:
```
Array 1:       भारत |         ** |         एक |       महान |    राष्ट्र |         है
Match:            ✓ |          ✗ |          ✗ |          ✓ |          ✓ |          ✓
Array 2:       भारत |          , |         ** |       महान |    राष्ट्र |         है
```

This aloows to evaluate the word error rates independent of punctuation errors and also specific error rates for punctuation and numeral errors.

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

```bash
cd examples
uv run evaluate.py
```

The evaluate.py script will generate a report in the `dictation-eval` directory.

## TODO
- Define a generic tokenizer with language specific features
- Add language code as a parameter to tokenizer
- Add a token-type tag to each token <word>, <punctuation>, <numeral> <abbreviation> etc
- Improve the token-type based scoring function
- Interactive front-end for alignment visualization and WER/PER/NER analysis

## Acknowledgements

This tool is developed as part of the Adalat AI initiative focusing on Indic language technologies.