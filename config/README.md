# Domain Configuration Files

This directory contains example domain configuration files for the DictErrors library. These are reference examples - actual bundled configs are in `src/dicterrors/config/`.

## Quick Start

Copy a bundled config and customize for your project:

```bash
# Extract bundled config to customize
python -c "
import shutil
from pathlib import Path
from dicterrors.domain_config import DomainConfig
config_path = Path(DomainConfig.legal.__code__.co_filename).parent / 'config' / 'legal_terms.txt'
shutil.copy(config_path, 'my_custom_legal.txt')
print(f'Copied to my_custom_legal.txt')
"

# Or create from scratch using template below
```

## File Format

Domain configuration files use a simple line-based format:

```
# Comments start with hash (full-line or inline)
@name: domain_name          # Domain identifier
@category: CATEGORY_NAME    # Token category name
@label: XER                 # Short error rate label (e.g., LER, MER, CER)
@case_sensitive: false      # true/false/yes/no/1/0

# Literal terms (one per line, automatically escaped)
term1
term2
u/s     # inline comments supported

# Regex patterns (prefix with REGEX:, used directly)
REGEX: pattern1|pattern2
REGEX: PW[-\s]*\d+    # flexible spacing patterns
```

### Metadata Fields (all optional)

| Field | Description | Default |
|-------|-------------|---------|
| `@name` | Domain identifier | `"domain"` |
| `@category` | Token category name | `"DOMAIN_{NAME}"` |
| `@label` | Error rate label | `"{NAME}ER"` |
| `@case_sensitive` | Case matching | `false` |

### Pattern Types

**Literal Terms:**
- One term per line
- Automatically escaped with `re.escape()` for regex safety
- Example: `u/s` becomes `u\/s` in regex (slash is escaped)
- Safe for special characters: `.`, `*`, `+`, `?`, `[`, `]`, `{`, `}`, `(`, `)`, `|`, `\`, `^`, `$`

**Regex Patterns:**
- Prefix line with `REGEX:`
- Used directly without escaping
- Supports full Python regex syntax (`re` module)
- Example: `REGEX: PW[-\s]*\d+` matches PW1, PW-1, PW 1, PW  1

**Comments:**
- Full-line comments: `# This is a comment`
- Inline comments: `u/s  # under section`
- Empty lines ignored

## Template

Copy this template to create new domain configs:

```
# My Custom Domain Configuration
@name: my_domain
@category: MY_CATEGORY
@label: MER
@case_sensitive: false

# Add literal terms below (one per line)
# These are automatically escaped for regex safety
term1
term2

# Add regex patterns below (prefix with REGEX:)
# These support full regex syntax
REGEX: pattern1|pattern2
REGEX: \d+\s*units?    # matches "5 unit", "10 units", "5unit"
```

## Examples

### Legal Domain
```
@name: legal
@category: LEGAL
@label: LER

# Literal terms
u/s
r/w
sec.
art.

# Flexible patterns for witness designations
REGEX: PW[-\s]*\d+     # PW1, PW-1, PW 1
REGEX: CW[-\s]*\d+     # CW1, CW-1, CW 1
REGEX: Ext\.[-\s]*[A-Z]\d*  # Ext.A, Ext. B2
```

### Medical Domain
```
@name: medical
@category: MEDICAL
@label: MER

# Literal units
mg
ml
cc
IU

# Dosage patterns
REGEX: \d+\s*mg
REGEX: \d+\s*ml
REGEX: \d+\s*mg/ml
```

### Financial Domain
```
@name: financial
@category: CURRENCY
@label: CER

# Currency symbols
$
€
₹

# Amount patterns with comma separators
REGEX: \$\d+(?:,\d{3})*(?:\.\d{2})?
REGEX: €\d+(?:,\d{3})*(?:\.\d{2})?
REGEX: ₹\d+(?:,\d{3})*(?:\.\d{2})?
```

## Loading Configs

### From Python
```python
from dicterrors import DomainConfig, text_error_rates

# Load custom config
domain = DomainConfig.from_file("path/to/my_config.txt")
report = text_error_rates(ref, hyp, domain)
```

### From CLI (batch_evaluate.py)
```bash
python examples/batch_evaluate.py \
    --input data/predictions.jsonl \
    --domain-config path/to/my_config.txt
```

## Error Handling

The `from_file()` method validates configs and raises helpful errors:

| Error | Cause | Fix |
|-------|-------|-----|
| `FileNotFoundError` | File doesn't exist | Check file path |
| `PermissionError` | File not readable | Check file permissions |
| `ValueError: No patterns found` | File has no terms or patterns | Add at least one term or REGEX pattern |
| `ValueError: Invalid metadata format` | Metadata line missing colon | Use format `@key: value` |
| `ValueError: Invalid regex pattern` | Regex syntax error | Check regex syntax with online tester |

## Tips

1. **Start simple**: Begin with literal terms, add regex patterns only when needed
2. **Test patterns**: Use [regex101.com](https://regex101.com/) to validate regex patterns
3. **Case sensitivity**: Most domains should use `@case_sensitive: false` unless acronyms matter (like API vs api)
4. **Version control**: Store domain configs in git alongside your evaluation scripts
5. **Document patterns**: Use inline comments to explain complex regex patterns

## Bundled Configs

DictErrors includes four bundled configs accessible via factory methods:
- `DomainConfig.legal()` - Indian legal terminology
- `DomainConfig.medical()` - Medical units and dosages
- `DomainConfig.financial()` - Currency and amounts
- `DomainConfig.technical()` - Technical abbreviations (case-sensitive)

These are maintained by library authors and updated with releases. For custom terminology, create your own config files.
