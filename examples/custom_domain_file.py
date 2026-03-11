#!/usr/bin/env python3
"""
Demonstrates file-based domain configuration.

Shows three approaches:
1. Factory methods for bundled configs
2. Loading from custom files
3. Inline custom domains
"""
from dicterrors import text_error_rates, DomainConfig

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

# Use bundled financial domain (for demonstration with financial text)
ref_fin = "paid $100 and €50 for total of ₹10,500"
hyp_fin = "paid $100 and euro 50 for total of rupees 10,500"
financial_domain = DomainConfig.financial()
report_fin = text_error_rates(ref_fin, hyp_fin, financial_domain)
print(f"\nFinancial Domain - CER: {report_fin['CURRENCY']['error_rate']:.2%}")
print(f"  Currency terms: {report_fin['CURRENCY']['substitutions']} substitutions")

print("\n" + "=" * 80)
print("APPROACH 2: Custom File-Based Config")
print("=" * 80)

# Load from a user-supplied custom file using DomainConfig.from_file()
# Example: custom_domain = DomainConfig.from_file("path/to/my_legal_terms.txt")
# For now, demonstrate with the bundled legal config used as a custom variant
custom_domain = DomainConfig.legal()
report_custom = text_error_rates(ref, hyp, custom_domain)
print(f"\nCustom Legal Domain (via factory) - {custom_domain.label}: {report_custom[custom_domain.category]['error_rate']:.2%}")
print(f"  Configuration: category={custom_domain.category}, label={custom_domain.label}")
print("  (To use a custom file: DomainConfig.from_file('path/to/my_legal_terms.txt'))")

print("\n" + "=" * 80)
print("APPROACH 3: Inline Custom Domain")
print("=" * 80)

# Create custom domain inline
custom_inline = DomainConfig(
    "financial_custom",
    ["$", "€", "₹", "Rs.", "rupees"],
    category="CURRENCY",
    label="CER"
)
report_inline = text_error_rates(ref, hyp, custom_inline)
print(f"\nInline Financial Domain - CER: {report_inline['CURRENCY']['error_rate']:.2%}")
print(f"  Currency substitutions: {report_inline['CURRENCY']['substitutions']}")
print(f"  (Detects 'Rs.' → 'rupees' and similar variations)")

print("\n" + "=" * 80)
print("\nKey Takeaways:")
print("- Use factory methods (DomainConfig.legal()) for quick start")
print("- Use file-based configs (DomainConfig.from_file()) for customization")
print("- Use inline configs (DomainConfig(...)) for experiments")
print("=" * 80)
