#!/usr/bin/env python3
"""
Demonstrates file-based domain configuration.

Shows three approaches:
1. Factory methods for bundled configs
2. Loading from custom files
3. Inline custom domains
"""

from pathlib import Path

from scribe import DomainConfig, text_error_rates

SAMPLE_LEGAL_FILE = Path(__file__).parent / "sample_legal.txt"

# Sample texts
ref = "charged u/s 302 IPC on 22.05.2023 for Rs. 10,500"
hyp = "charged under section 302 IPC on 22.05.2023 for rupees 10,500"

print("=" * 80)
print("APPROACH 1: Factory Methods (Bundled Configs)")
print("=" * 80)

# Use bundled legal domain
legal_domain = DomainConfig.legal()
report = text_error_rates(ref, hyp, legal_domain)
print(f"\nLegal Domain - LER: {report['LEGAL']['error_rate']:.2%}")
print(f"  Substitutions: {report['LEGAL']['substitutions']}")
print(f"  Insertions: {report['LEGAL']['insertions']}")
print(f"  Deletions: {report['LEGAL']['deletions']}")

# Use bundled medical domain (for demonstration with medical text)
ref_med = "prescribed 500mg aspirin and 10ml cough syrup"
hyp_med = "prescribed 500mg aspirin and 10ml cough syrup"
medical_domain = DomainConfig.medical()
report_med = text_error_rates(ref_med, hyp_med, medical_domain)
print(f"\nMedical Domain - MER: {report_med['MEDICAL']['error_rate']:.2%}")
print(f"  Medical terms found: {report_med['MEDICAL']['correct']} correct")

print("\n" + "=" * 80)
print("APPROACH 2: Custom File-Based Config")
print("=" * 80)

# Load from a real config file shipped alongside this script.
# Open examples/sample_legal.txt to see the file format.
custom_domain = DomainConfig.from_file(str(SAMPLE_LEGAL_FILE))
report_custom = text_error_rates(ref, hyp, custom_domain)
print(f"\nLoaded from: {SAMPLE_LEGAL_FILE.name}")
print(f"  {custom_domain.label}: {report_custom[custom_domain.category]['error_rate']:.2%}")
print(
    f"  Configuration: name={custom_domain.name}, "
    f"category={custom_domain.category}, label={custom_domain.label}"
)

print("\n" + "=" * 80)
print("APPROACH 3: Inline Custom Domain")
print("=" * 80)

# Create custom domain inline
custom_inline = DomainConfig(
    "custom", ["u/s", "r/w", "sec.", "art."], category="CUSTOM", label="CuER"
)
report_inline = text_error_rates(ref, hyp, custom_inline)
print(f"\nInline Custom Domain - CuER: {report_inline['CUSTOM']['error_rate']:.2%}")
print(f"  Custom term substitutions: {report_inline['CUSTOM']['substitutions']}")
print("  (Detects 'u/s' → 'under section' and similar variations)")

print("\n" + "=" * 80)
print("\nKey Takeaways:")
print("- Use factory methods (DomainConfig.legal()) for quick start")
print("- Use file-based configs (DomainConfig.from_file()) for customization")
print("- Use inline configs (DomainConfig(...)) for experiments")
print("=" * 80)
