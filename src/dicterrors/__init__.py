"""
DictErrors: A specialized evaluation framework for Indic language ASR
with support for domain-aware entity shielding and Sandhi-aware alignment.
"""

# --- Categories & Constants ---
from .constants import (
    CAT_WORD,
    CAT_PUNCT,
    CAT_NUMERAL,
    CATEGORIES,
    get_categories
)

# --- Domain Configuration ---
from .domain_config import (
    DomainConfig,
    LEGAL_DOMAIN,
    MEDICAL_DOMAIN
)

# --- Tokenization ---
from .tokenize import (
    domain_aware_tokenizer
)

# --- Normalization ---
from .normalize import (
    normalize_token,
    normalize_date,
    normalize_currency,
    normalize_numeral
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
    format_alignment_table,
    extract_error_rates,
    write_summary_to_file,
    format_alignment_dict
)

