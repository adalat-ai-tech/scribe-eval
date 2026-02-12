"""
Domain configuration for domain-aware tokenization.

Allows users to specify domain-critical terminology that should be
treated as atomic tokens and tracked separately for error analysis.
"""
import re
from typing import List, Union, Optional


class DomainConfig:
    """Configuration for a domain-specific terminology set."""

    def __init__(
        self,
        name: str,
        patterns: Union[str, List[str]],
        category: Optional[str] = None,
        label: Optional[str] = None,
        case_sensitive: bool = False
    ):
        """
        Initialize domain configuration.

        Args:
            name: Domain name (e.g., "legal", "medical", "financial")
            patterns: Either a regex pattern string or list of domain terms
            category: Category name for tokens (default: "DOMAIN_{NAME}")
            label: Short label for error rate (default: "{NAME}ER")
            case_sensitive: Whether pattern matching is case-sensitive

        Examples:
            >>> # Using list of terms
            >>> legal = DomainConfig("legal", ["u/s", "r/w", "sec."])

            >>> # Using regex
            >>> medical = DomainConfig("medical", r'mg|ml|cc|\d+mg')

            >>> # Custom category and label
            >>> financial = DomainConfig("financial",
            ...     ["$", "€", "₹"],
            ...     category="CURRENCY",
            ...     label="CER")
        """
        self.name = name
        self.case_sensitive = case_sensitive

        # Convert patterns to regex
        if isinstance(patterns, str):
            self.pattern_regex = patterns
        elif isinstance(patterns, list):
            if not patterns:
                raise ValueError("patterns list cannot be empty")
            # Escape special regex characters in each term
            escaped = [re.escape(term) for term in patterns]
            self.pattern_regex = '|'.join(escaped)
        else:
            raise TypeError("patterns must be str (regex) or list (terms)")

        # Set category and label with sensible defaults
        self.category = category or f"DOMAIN_{name.upper()}"
        self.label = label or f"{name.upper()}ER"

        # Compile regex for efficiency
        flags = 0 if case_sensitive else re.IGNORECASE
        self.compiled_pattern = re.compile(self.pattern_regex, flags=flags)

    def matches(self, text: str) -> bool:
        """Check if text matches this domain pattern."""
        return bool(self.compiled_pattern.match(text))

    def __repr__(self):
        return f"DomainConfig(name='{self.name}', category='{self.category}', label='{self.label}')"


# Pre-defined domain configurations for common use cases
# Users can use these or create their own

LEGAL_DOMAIN = DomainConfig(
    name="legal",
    patterns=[
        "u/s", "r/w", "w.p.", "o.s.", "no.",
        "v.", "vs.", "art.", "sec.", "PW", "CW", "Ext."
    ],
    category="LEGAL",
    label="LER",
    case_sensitive=False
)

MEDICAL_DOMAIN = DomainConfig(
    name="medical",
    patterns=r'mg|ml|cc|mcg|\d+mg|\d+ml',
    category="MEDICAL",
    label="MER",
    case_sensitive=False
)
