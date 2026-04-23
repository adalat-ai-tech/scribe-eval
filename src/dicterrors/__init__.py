"""
DictErrors: A specialized evaluation framework for Indic language ASR
with support for domain-aware entity shielding and Sandhi-aware alignment.
"""

# --- Categories & Constants ---
# --- Alignment Logic ---
from .align import DEFAULT_WEIGHTS as DEFAULT_WEIGHTS
from .align import align_arrays as align_arrays

# --- Analysis & Insights ---
from .analysis import (
    compute_category_contributions as compute_category_contributions,
)
from .analysis import (
    compute_error_summary as compute_error_summary,
)
from .analysis import (
    compute_error_type_distribution as compute_error_type_distribution,
)
from .analysis import (
    compute_frequent_deletions as compute_frequent_deletions,
)
from .analysis import (
    compute_frequent_insertions as compute_frequent_insertions,
)
from .analysis import (
    compute_frequent_substitutions as compute_frequent_substitutions,
)
from .analysis import (
    compute_total_error_rate as compute_total_error_rate,
)
from .constants import (
    CAT_NUMERAL as CAT_NUMERAL,
)
from .constants import (
    CAT_PUNCT as CAT_PUNCT,
)
from .constants import (
    CAT_WORD as CAT_WORD,
)
from .constants import (
    CATEGORIES as CATEGORIES,
)
from .constants import (
    get_categories as get_categories,
)

# --- Domain Configuration ---
from .domain_config import DomainConfig as DomainConfig

# --- Measurement & Error Rates ---
from .measure import (
    text_error_details as text_error_details,
)
from .measure import (
    text_error_rates as text_error_rates,
)
from .measure import (
    token_error_details as token_error_details,
)
from .measure import (
    token_error_rates as token_error_rates,
)

# --- Batch Processing & Reporting ---
from .measure_batch import (
    aggregate_error_details as aggregate_error_details,
)
from .measure_batch import (
    compute_aggregate_metrics as compute_aggregate_metrics,
)
from .measure_batch import (
    compute_sample_errors as compute_sample_errors,
)
from .measure_batch import (
    print_evaluation_summary as print_evaluation_summary,
)

# --- Normalization ---
from .normalize import (
    normalize_currency as normalize_currency,
)
from .normalize import (
    normalize_date as normalize_date,
)
from .normalize import (
    normalize_numeral as normalize_numeral,
)
from .normalize import (
    normalize_token as normalize_token,
)

# --- Report Formatting ---
from .reporting import (
    extract_error_rates as extract_error_rates,
)
from .reporting import (
    format_alignment_dict as format_alignment_dict,
)
from .reporting import (
    format_alignment_table as format_alignment_table,
)
from .reporting import (
    format_contribution_table as format_contribution_table,
)
from .reporting import (
    format_dataset_table as format_dataset_table,
)
from .reporting import (
    format_error_counts_table as format_error_counts_table,
)
from .reporting import (
    format_frequent_errors_table as format_frequent_errors_table,
)
from .reporting import (
    format_metrics_dict as format_metrics_dict,
)
from .reporting import (
    write_summary_to_file as write_summary_to_file,
)

# --- Tokenization ---
from .tokenize import domain_aware_tokenizer as domain_aware_tokenizer
