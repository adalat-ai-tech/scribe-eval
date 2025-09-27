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
cd dicterrors

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

## Usage

### Basic Error Rate Calculation

```python
from src.measure import text_error_rates

# Calculate error rates between reference and hypothesis texts
ref_text = "10 ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ।"
hyp_text = "ಹತ್ತು ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ."

wer, per, ner, report = text_error_rates(ref_text, hyp_text)
print(f"Word Error Rate: {wer*100:.2f}%")
print(f"Punctuation Error Rate: {per*100:.2f}%")
print(f"Numeral Error Rate: {ner*100:.2f}%")
```

### Batch Evaluation

```python
from src.evaluate import evaluate_predictions

# Evaluate multiple predictions from a JSONL file
results = evaluate_predictions("predictions.jsonl", "evaluation_results.json")
```

### Custom Token Alignment

```python
from src.align import align_arrays
from src.tokenize import malayalam_tokenizer

# Tokenize text
text1 = "ഇന്ന് 9 ാം തീയതിയാണ്, സമയം 9:60 വന്നു ഞാ പോയി"
text2 = "ഇന്ന് 9 ആം തീയതിയാണ് സമയം, 9:30 ഞാൻ ഞാങ്ങോട്ട് പോയി"

arr1 = malayalam_tokenizer(text1)
arr2 = malayalam_tokenizer(text2)

# Align tokens
aligned1, aligned2, score = align_arrays(arr1, arr2)
print(f"Alignment score: {score}")
```

## Project Structure

```
.
├── pyproject.toml       # Project metadata and dependencies
├── main.py             # Main entry point
├── src/
│   ├── align.py        # Token alignment algorithms
│   ├── evaluate.py     # Batch evaluation functionality
│   ├── measure.py      # Error rate calculation
│   ├── tokenize.py     # Language-specific tokenization
│   └── predictions.jsonl # Sample prediction data
└── README.md           # This file
```

## Input Format

The tool expects prediction data in JSONL format with the following structure:

```json
{
  "file_path": "test/audio/sample_00008825.wav",
  "transcript_cleaned": "10 ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ।",
  "duration": 6.208,
  "source_dataset": "adalat-ai/indicvoices",
  "original_split": "train",
  "prediction": "ಹತ್ತು ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ."
}
```

## Output Format

The evaluation results are saved in JSON format with detailed error analysis:

```json
{
  "file_path": "test/audio/sample_00008825.wav",
  "ref_text": "10 ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ।",
  "hyp_text": "ಹತ್ತು ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ.",
  "WER": 12.5,
  "PER": 100.0,
  "NER": 100.0,
  "detailed_report": {
    "word": { /* word error details */ },
    "punctuation": { /* punctuation error details */ },
    "numeral": { /* numeral error details */ }
  }
}
```

## Algorithm Overview

The alignment algorithm uses a modified version of the Needleman-Wunsch algorithm with specialized scoring functions to handle different token types (words, punctuation, and numbers) in Indic languages. The error rates are calculated by comparing the aligned tokens and categorizing them based on token type.

## Dependencies

- Python 3.11+
- Levenshtein 0.27.1+ (for string distance calculations)

## Acknowledgements

This tool was developed as part of the Adalat AI initiative focusing on Indic language technologies.