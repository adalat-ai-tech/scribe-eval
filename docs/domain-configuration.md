# Domain Configuration

DictErrors supports flexible domain-aware tokenization via the `DomainConfig` class. Domain entities are extracted before general tokenization to prevent incorrect splitting (e.g., `u/s` stays as one token) and are tracked separately in error metrics.

## Factory Methods (Bundled Domains)

Three pre-configured domains are bundled with the package:

```python
from dicterrors import DomainConfig, text_error_rates

domain = DomainConfig.legal()      # Indian legal terminology
domain = DomainConfig.medical()    # Medical units and dosages
domain = DomainConfig.technical()  # Technical abbreviations (case-sensitive)

report = text_error_rates(ref, hyp, domain)
```

| Factory Method | Category | Label | Includes |
|---|---|---|---|
| `DomainConfig.legal()` | LEGAL | LER | u/s, r/w, sec., art., v., vs., PW1/PW-1, CW1, Ext.A |
| `DomainConfig.medical()` | MEDICAL | MER | mg, ml, cc, mcg, IU, 500mg, 10ml |
| `DomainConfig.technical()` | TECH | TER | API, SDK, CLI, JSON, HTTP, v1.0 |

## File-Based Configuration

Load domain configs from files for version control and team sharing:

```python
domain = DomainConfig.from_file("config/custom_legal.txt")
report = text_error_rates(ref, hyp, domain)
```

### File Format

```
# Domain configuration file
@name: legal
@category: LEGAL
@label: LER
@case_sensitive: false

# Literal terms (automatically escaped for regex safety)
u/s
r/w
sec.

# Regex patterns (prefix with REGEX:, used directly)
REGEX: PW[-\s]*\d+       # Matches PW1, PW 1, PW-1
REGEX: CW[-\s]*\d+       # Matches CW1, CW 1, CW-1
REGEX: Ext\.[-\s]*[A-Z]\d*  # Matches Ext.A, Ext. B2
```

**Metadata fields** (all optional):

| Field | Default | Description |
|---|---|---|
| `@name` | `"domain"` | Domain identifier |
| `@category` | `"DOMAIN_{NAME}"` | Token category name |
| `@label` | `"{NAME}ER"` | Short label for error rate metric |
| `@case_sensitive` | `false` | Accepts `true`/`false`/`yes`/`no`/`1`/`0` |

**Pattern types:**
- **Literal terms**: One per line, automatically escaped with `re.escape()`
- **Regex patterns**: Prefix with `REGEX:`, supports full regex syntax
- **Comments**: Lines starting with `#`, or inline text after `#`

### Bundled Config Files

Sample config files are included in `src/dicterrors/config/`:
- `legal_terms.txt` — Indian legal terminology
- `medical_terms.txt` — Medical units and dosages
- `technical_terms.txt` — Technical abbreviations (case-sensitive)

Copy and modify these for your projects. The `config/` directory at the repo root contains additional example files with inline documentation.

### Overriding Parameters at Runtime

```python
# Override specific parameters when loading from file
custom = DomainConfig.from_file(
    "config/legal_terms.txt",
    category="LEGAL_CUSTOM",
    case_sensitive=True
)
```

## Inline Custom Domains

```python
from dicterrors import DomainConfig

# List-based patterns (automatically escaped)
custom = DomainConfig("custom", ["u/s", "r/w"], category="CUSTOM", label="CuER")

# Regex pattern (used directly)
technical = DomainConfig("tech", r'API|SDK|CLI|v\d+\.\d+', category="TECH", label="TER")

# Use in evaluation
report = text_error_rates(ref, hyp, custom)
```

## No Domain

Pass `None` to use base categories only (WORD, NUMERAL, PUNCT):

```python
report = text_error_rates(ref, hyp, None)
```

## File Location Conventions

- **Project configs**: `config/` directory at the repository root
- **Personal configs**: `~/.config/dicterrors/`
- **Dataset-specific configs**: Alongside the dataset in the data directory

```
project/
├── config/
│   ├── legal_terms.txt
│   └── medical_terms.txt
├── data/
│   ├── court-transcripts/
│   │   ├── predictions.jsonl
│   │   └── legal_terms.txt    # Dataset-specific overrides
│   └── medical-records/
│       └── predictions.jsonl
```

## Pattern Matching Examples

All three of these produce a `LEGAL` tag:

```python
legal = DomainConfig.from_file("config/legal_terms.txt")

tokens1, tags1 = domain_aware_tokenizer("witness PW1 testified", legal)
tokens2, tags2 = domain_aware_tokenizer("witness PW 1 testified", legal)   # space
tokens3, tags3 = domain_aware_tokenizer("witness PW-1 testified", legal)   # hyphen

assert "LEGAL" in tags1
assert "LEGAL" in tags2
assert "LEGAL" in tags3
```
