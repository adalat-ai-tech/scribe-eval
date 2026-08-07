# Domain Configuration

scribe-eval supports flexible domain-aware tokenization via the `DomainConfig` class. Domain entities are extracted before general tokenization to prevent incorrect splitting (e.g., `u/s` stays as one token) and are tracked separately in error metrics.

## Factory Methods (Bundled Domains)

Three pre-configured domains are bundled with the package:

```python
from scribe import DomainConfig, text_error_rates

domain = DomainConfig.legal()      # Indian legal terminology
domain = DomainConfig.medical()    # Medical units and dosages
domain = DomainConfig.technical()  # Technical abbreviations (case-sensitive)

report = text_error_rates(ref, hyp, domain)
```

| Factory Method | Category | Label | Includes |
|---|---|---|---|
| `DomainConfig.legal()` | LEGAL | ER_DOMAIN | u/s, r/w, sec., art., v., vs., PW1/PW-1, CW1, Ext.A |
| `DomainConfig.medical()` | MEDICAL | ER_DOMAIN | mg, ml, cc, mcg, IU, 500mg, 10ml |
| `DomainConfig.technical()` | TECH | ER_DOMAIN | API, SDK, CLI, JSON, HTTP, v1.0 |

## File-Based Configuration

Load domain configs from files for version control and team sharing:

```python
domain = DomainConfig.from_file("examples/sample_legal.txt")
report = text_error_rates(ref, hyp, domain)
```

### File Format

```
# Domain configuration file
@name: legal
@category: LEGAL
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
| `@case_sensitive` | `false` | Accepts `true`/`false`/`yes`/`no`/`1`/`0` |

**Pattern types:**
- **Literal terms**: One per line, automatically escaped with `re.escape()`
- **Regex patterns**: Prefix with `REGEX:`, supports full regex syntax
- **Comments**: Lines starting with `#`, or inline text after `#`

### Bundled Domains

Three domains ship inside the package and are selected by name — via the
factories (`DomainConfig.legal()`, `.medical()`, `.technical()`) or the
CLI (`--domain legal|medical|technical`); their files are internal and
never referenced by path:

- **legal** — Indian legal terminology
- **medical** — Medical units and dosages
- **technical** — Technical abbreviations (case-sensitive)

To write your own domain, copy `examples/sample_legal.txt` (a fully
commented format example) and pass its path to `--domain` or
`DomainConfig.from_file()`.

### Overriding Parameters at Runtime

```python
# Override specific parameters when loading from file
custom = DomainConfig.from_file(
    "examples/sample_legal.txt",
    category="LEGAL_CUSTOM",
    case_sensitive=True
)
```

## Inline Custom Domains

```python
from scribe import DomainConfig

# List-based patterns (automatically escaped)
custom = DomainConfig("custom", ["u/s", "r/w"], category="CUSTOM")

# Regex pattern (used directly)
technical = DomainConfig("tech", r'API|SDK|CLI|v\d+\.\d+', category="TECH")

# Use in evaluation
report = text_error_rates(ref, hyp, custom)
```

## No Domain

Pass `None` to use base categories only (LEXICAL, NUMERAL, PUNCT):

```python
report = text_error_rates(ref, hyp, None)
```

## File Location Conventions

Suggestions for organizing *your own* custom domain files in *your*
evaluation project (SCRIBE reads whatever path you pass; nothing here is
required or auto-discovered):

- **Project configs**: a `config/` directory in your project for domain files shared across datasets
- **Dataset-specific configs**: alongside the dataset in its data directory
- **Personal configs**: any stable location works (e.g. `~/.config/scribe-eval/`) — plain files, passed by path

```
my-asr-eval/
├── config/
│   ├── court_terms.txt         # (bundled legal/medical need no file — use --domain legal)
│   └── station_names.txt
├── data/
│   ├── court-transcripts/
│   │   ├── predictions.jsonl
│   │   └── court_terms.txt    # Dataset-specific overrides
│   └── medical-records/
│       └── predictions.jsonl
```

## Pattern Matching Examples

All three of these produce a `LEGAL` tag:

```python
legal = DomainConfig.from_file("examples/sample_legal.txt")

tokens1, tags1 = domain_aware_tokenizer("witness PW1 testified", legal)
tokens2, tags2 = domain_aware_tokenizer("witness PW 1 testified", legal)   # space
tokens3, tags3 = domain_aware_tokenizer("witness PW-1 testified", legal)   # hyphen

assert "LEGAL" in tags1
assert "LEGAL" in tags2
assert "LEGAL" in tags3
```
