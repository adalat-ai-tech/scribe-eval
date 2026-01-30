"""
DictErrors: A specialized evaluation framework for Indic language ASR 
with support for legal-domain entity shielding and Sandhi-aware alignment.
"""

# --- Categories & Tokenization ---
from .tokenize import (
    legal_aware_tokenizer,
    CAT_WORD,
    CAT_PUNCT,
    CAT_NUMERAL,
    CAT_LEGAL
)

# --- Alignment Logic ---
from .align import (
    align_arrays, 
    DEFAULT_WEIGHTS
)

# --- Measurement & Error Rates ---
from .measure import (
    token_error_rates, 
    text_error_rates
)

# --- Batch Processing & Reporting ---
from .measure_batch import (
    compute_sample_errors,
    compute_aggregate_metrics,
    print_evaluation_summary
)

# --- Report Formatting ---
from .reporting import (
    format_metrics_dict,
    format_dataset_table,
    format_error_counts_table,
    format_alignment_table
)

