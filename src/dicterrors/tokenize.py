import re

# Categories
CAT_WORD = "WORD"
CAT_PUNCT = "PUNCT"
CAT_NUMERAL = "NUMERAL"
CAT_LEGAL = "LEGAL"

def legal_aware_tokenizer(text: str):
    if not text:
        return [], []

    # 1. Define patterns using non-capturing groups (?:...) 
    # This ensures re.findall returns the whole match as a string, not a tuple.
    legal_inner = r'u/s|r/w|w\.p\.|o\.s\.|no\.|v\.|vs\.|art\.|sec\.'
    num_inner = r'\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}:\d{2}|\d+(?:,\d+)*(?:\.\d+)?'
    
    # We create separate patterns for classification later
    legal_regex = re.compile(f'^{legal_inner}$', re.IGNORECASE)
    
    # The protected pattern for extraction (capturing group around the whole thing)
    protected_pattern = f'((?:{legal_inner})|(?:{num_inner}))'

    # 2. Extract and Placeholder using the flag in the function call
    entities = re.findall(protected_pattern, text, flags=re.IGNORECASE)
    
    # Use a unique placeholder that won't appear in text
    placeholder_text = re.sub(protected_pattern, " __ENTITY__ ", text, flags=re.IGNORECASE)
    
    # 3. Standard punctuation handling for the prose
    # Separate punctuations with spaces
    punctuation_chars = r"[.,?!;:\-\/\"'()\[\]{}—–+*=<>|@#%^&₹$]"
    placeholder_text = re.sub(f"({punctuation_chars})", r" \1 ", placeholder_text)
    
    # Split into raw tokens
    raw_tokens = placeholder_text.split()
    
    tokens = []
    tags = []
    entity_idx = 0
    
    for t in raw_tokens:
        if t == "__ENTITY__":
            if entity_idx < len(entities):
                val = entities[entity_idx]
                entity_idx += 1
                # Classify: Is it Legal or Numeral?
                if legal_regex.match(val):
                    tokens.append(val)
                    tags.append(CAT_LEGAL)
                else:
                    tokens.append(val)
                    tags.append(CAT_NUMERAL)
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
    sample = "U/S 302 of IPC on 22.05.2023 at 10:30, for Rs. 10,500. ഈ 3-ഓ 4-ഓ വയസ്സുള്ള കുട്ടിക്ക് 9 ാം തീയതി , 9:30-ന് ഫോൺ കിട്ടിയോ? 1,500 rupees abc123def. 19-രംദു & 19-രംദു"
    tokens, tags = legal_aware_tokenizer(sample)
    for tok, tag in zip(tokens, tags):
        print(f"{tok:<15} | {tag}")