import re
from typing import Optional, Tuple, List
from .constants import CAT_WORD, CAT_PUNCT, CAT_NUMERAL
from .domain_config import DomainConfig


def domain_aware_tokenizer(
    text: str,
    domain_config: Optional[DomainConfig] = None
) -> Tuple[List[str], List[str]]:
    """
    Tokenize text with domain-aware entity shielding.

    Domain-critical terms (e.g., legal abbreviations, medical terms)
    are identified and protected from punctuation splitting, then
    tagged with their domain category for separate error tracking.

    Args:
        text: Input text to tokenize
        domain_config: Domain configuration (None to disable domain handling)

    Returns:
        Tuple of (tokens, tags) where tags are category labels

    Examples:
        >>> # Legal domain
        >>> from .domain_config import LEGAL_DOMAIN
        >>> tokens, tags = domain_aware_tokenizer("charged u/s 302 IPC", LEGAL_DOMAIN)
        >>> # tokens: ["charged", "u/s", "302", "IPC"]
        >>> # tags: ["WORD", "LEGAL", "NUMERAL", "WORD"]

        >>> # Medical domain
        >>> from .domain_config import MEDICAL_DOMAIN
        >>> tokens, tags = domain_aware_tokenizer("Take 500mg daily", MEDICAL_DOMAIN)

        >>> # No domain handling
        >>> tokens, tags = domain_aware_tokenizer("Just regular text", None)
    """
    if not text:
        return [], []

    # Define numeral patterns (always protected)
    num_inner = r'\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}:\d{2}|\d+(?:,\d+)*(?:\.\d+)?'

    # Build protected pattern with named groups
    if domain_config:
        # Combine domain and numeral patterns
        protected_pattern = f'(?P<domain>{domain_config.pattern_regex})|(?P<numeral>{num_inner})'
    else:
        # Only numeral patterns
        protected_pattern = f'(?P<numeral>{num_inner})'

    # Extract and replace entities
    entities = []
    flags = 0 if (domain_config and domain_config.case_sensitive) else re.IGNORECASE

    for match in re.finditer(protected_pattern, text, flags=flags):
        if domain_config and match.lastgroup == 'domain':
            entities.append(('domain', match.group('domain')))
        elif match.lastgroup == 'numeral':
            entities.append(('numeral', match.group('numeral')))

    # Replace entities with placeholder
    placeholder_text = re.sub(protected_pattern, " __ENTITY__ ", text, flags=flags)

    # Separate punctuation
    punctuation_chars = r"[.,?!;:\-\/\"'()\[\]{}—–+*=<>|@#%^&₹$]"
    placeholder_text = re.sub(f"({punctuation_chars})", r" \1 ", placeholder_text)

    # Split into raw tokens
    raw_tokens = placeholder_text.split()

    # Split and classify tokens
    tokens = []
    tags = []
    entity_idx = 0

    for t in raw_tokens:
        if t == "__ENTITY__":
            if entity_idx < len(entities):
                entity_type, entity_val = entities[entity_idx]
                tokens.append(entity_val)

                if entity_type == 'domain':
                    tags.append(domain_config.category)
                else:  # numeral
                    tags.append(CAT_NUMERAL)

                entity_idx += 1
        else:
            # Check if it's a word or punctuation
            if any(c.isalnum() for c in t):
                tokens.append(t)
                tags.append(CAT_WORD)
            else:
                tokens.append(t)
                tags.append(CAT_PUNCT)

    return tokens, tags

# TEST CASE
if __name__ == "__main__":
    from .domain_config import LEGAL_DOMAIN

    sample = "U/S 302 of IPC on 22.05.2023 at 10:30, for Rs. 10,500. ഈ 3-ഓ 4-ഓ വയസ്സുള്ള കുട്ടിക്ക് 9 ാം തീയതി , 9:30-ന് ഫോൺ കിട്ടിയോ? 1,500 rupees abc123def. 19-രംദു & 19-രംദു"

    # Test with legal domain
    print("=== Legal Domain ===")
    tokens, tags = domain_aware_tokenizer(sample, LEGAL_DOMAIN)
    for tok, tag in zip(tokens, tags):
        print(f"{tok:<15} | {tag}")

    # Test without domain
    print("\n=== No Domain ===")
    tokens, tags = domain_aware_tokenizer(sample, None)
    for tok, tag in zip(tokens, tags):
        print(f"{tok:<15} | {tag}")