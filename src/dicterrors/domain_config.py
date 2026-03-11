"""
Domain configuration for domain-aware tokenization.

Allows users to specify domain-critical terminology that should be
treated as atomic tokens and tracked separately for error analysis.
"""
import re
from pathlib import Path
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
        r"""
        Initialize domain configuration.

        Args:
            name: Domain name (e.g., "legal", "medical", "technical")
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
            >>> custom = DomainConfig("custom", ["u/s", "r/w"], category="CUSTOM", label="CuER")
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

    @classmethod
    def from_file(
        cls,
        file_path: str,
        name: Optional[str] = None,
        category: Optional[str] = None,
        label: Optional[str] = None,
        case_sensitive: Optional[bool] = None
    ) -> 'DomainConfig':
        r"""
        Load domain configuration from a text file.

        File format:
            # Comments start with hash
            @name: legal
            @category: LEGAL
            @label: LER
            @case_sensitive: false

            # Literal terms (one per line, will be regex-escaped)
            u/s
            r/w

            # Regex patterns (prefix with REGEX:, used directly)
            REGEX: PW[-\s]*\d+

        Args:
            file_path: Path to configuration file (absolute or relative)
            name: Override domain name from file
            category: Override category from file
            label: Override label from file
            case_sensitive: Override case sensitivity from file

        Returns:
            DomainConfig instance loaded from file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is empty, has no patterns, or invalid metadata
            PermissionError: If file is not readable
            re.error: If regex pattern is invalid

        Examples:
            >>> # Load from file with defaults
            >>> legal = DomainConfig.from_file("config/legal_terms.txt")

            >>> # Override category at runtime
            >>> legal = DomainConfig.from_file(
            ...     "config/legal_terms.txt",
            ...     category="LEGAL_CUSTOM"
            ... )

            >>> # Use in CLI
            >>> import sys
            >>> config = DomainConfig.from_file(sys.argv[1])
        """
        # Validate file exists and is readable
        import os
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"Configuration file not readable: {file_path}")

        # Parse file
        metadata = {}
        literal_terms = []
        regex_patterns = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                # Strip whitespace
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Parse metadata lines (@key: value)
                if line.startswith('@'):
                    if ':' not in line:
                        raise ValueError(
                            f"Invalid metadata format at line {line_num}: {line}\n"
                            f"Expected format: @key: value"
                        )
                    key, value = line[1:].split(':', 1)
                    metadata[key.strip()] = value.strip()
                    continue

                # Parse regex patterns (REGEX: pattern)
                if line.startswith('REGEX:'):
                    pattern = line[6:].strip()
                    # Remove inline comments
                    if '#' in pattern:
                        pattern = pattern.split('#')[0].strip()
                    if pattern:
                        regex_patterns.append(pattern)
                    continue

                # Otherwise, it's a literal term
                # Remove inline comments
                if '#' in line:
                    line = line.split('#')[0].strip()
                if line:
                    literal_terms.append(line)

        # Validate we have at least some patterns
        if not literal_terms and not regex_patterns:
            raise ValueError(
                f"No patterns found in {file_path}. "
                f"File must contain at least one literal term or REGEX: pattern"
            )

        # Build combined pattern
        all_patterns = []

        # Add escaped literal terms
        if literal_terms:
            escaped = [re.escape(term) for term in literal_terms]
            all_patterns.extend(escaped)

        # Add regex patterns (not escaped)
        if regex_patterns:
            # Validate each regex pattern compiles
            for i, pattern in enumerate(regex_patterns):
                try:
                    re.compile(pattern)
                except re.error as e:
                    raise ValueError(
                        f"Invalid regex pattern in {file_path}: {pattern}\n"
                        f"Error: {e}"
                    ) from e
            all_patterns.extend(regex_patterns)

        # Combine all patterns with |
        combined_pattern = '|'.join(all_patterns)

        # Extract metadata with parameter overrides
        final_name = name or metadata.get('name', 'domain')
        final_category = category or metadata.get('category')
        final_label = label or metadata.get('label')

        # Parse case_sensitive from metadata
        if case_sensitive is not None:
            final_case_sensitive = case_sensitive
        else:
            cs_str = metadata.get('case_sensitive', 'false').lower()
            final_case_sensitive = cs_str in ('true', 'yes', '1')

        # Create and return DomainConfig instance
        return cls(
            name=final_name,
            patterns=combined_pattern,
            category=final_category,
            label=final_label,
            case_sensitive=final_case_sensitive
        )

    @classmethod
    def legal(cls) -> 'DomainConfig':
        """Load pre-defined legal domain from bundled config.

        Includes Indian legal terminology: u/s, r/w, sec., art., v., vs.,
        PW1/PW-1/PW 1 patterns, CW1 patterns, Ext.A patterns.

        Returns:
            DomainConfig instance for legal terminology with category='LEGAL', label='LER'

        Examples:
            >>> from dicterrors import DomainConfig, text_error_rates
            >>> domain = DomainConfig.legal()
            >>> report = text_error_rates(ref, hyp, domain)
        """
        config_path = Path(__file__).parent / "config" / "legal_terms.txt"
        return cls.from_file(str(config_path))

    @classmethod
    def medical(cls) -> 'DomainConfig':
        """Load pre-defined medical domain from bundled config.

        Includes medical units and dosages: mg, ml, cc, mcg, IU,
        numeric patterns like 500mg, 10ml.

        Returns:
            DomainConfig instance for medical terminology with category='MEDICAL', label='MER'

        Examples:
            >>> from dicterrors import DomainConfig, text_error_rates
            >>> domain = DomainConfig.medical()
            >>> report = text_error_rates(ref, hyp, domain)
        """
        config_path = Path(__file__).parent / "config" / "medical_terms.txt"
        return cls.from_file(str(config_path))

    @classmethod
    def technical(cls) -> 'DomainConfig':
        """Load pre-defined technical domain from bundled config.

        Includes technical abbreviations (case-sensitive): API, SDK, CLI,
        JSON, HTTP, version patterns like v1.0, v2.3.4.

        Returns:
            DomainConfig instance for technical terminology with category='TECH', label='TER'

        Examples:
            >>> from dicterrors import DomainConfig, text_error_rates
            >>> domain = DomainConfig.technical()
            >>> report = text_error_rates(ref, hyp, domain)
        """
        config_path = Path(__file__).parent / "config" / "technical_terms.txt"
        return cls.from_file(str(config_path))
