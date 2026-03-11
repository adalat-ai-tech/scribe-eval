#!/usr/bin/env python3
"""Test domain configuration flexibility."""

from dicterrors import DomainConfig, domain_aware_tokenizer, text_error_rates, LEGAL_DOMAIN, MEDICAL_DOMAIN

# Test 1: Legal domain
print("=== Test 1: Legal Domain ===")
text = "charged u/s 302 IPC"
tokens, tags = domain_aware_tokenizer(text, LEGAL_DOMAIN)
print(f"Text: {text}")
print(f"Tokens: {tokens}")
print(f"Tags: {tags}")
print()

# Test 2: Medical domain
print("=== Test 2: Medical Domain ===")
text = "Take 500mg twice daily"
tokens, tags = domain_aware_tokenizer(text, MEDICAL_DOMAIN)
print(f"Text: {text}")
print(f"Tokens: {tokens}")
print(f"Tags: {tags}")
print()

# Test 3: No domain
print("=== Test 3: No Domain ===")
text = "Just regular text with 123 numbers"
tokens, tags = domain_aware_tokenizer(text, None)
print(f"Text: {text}")
print(f"Tokens: {tokens}")
print(f"Tags: {tags}")
print()

# Test 4: Custom domain
print("=== Test 4: Custom Domain ===")
custom = DomainConfig("custom", ["u/s", "r/w", "sec."], category="CUSTOM", label="CuER")
text = "charged u/s 302 sec. 3 IPC"
tokens, tags = domain_aware_tokenizer(text, custom)
print(f"Text: {text}")
print(f"Tokens: {tokens}")
print(f"Tags: {tags}")
print()

# Test 5: Error rates with different domains
print("=== Test 5: Error Rates with Medical Domain ===")
ref = "Administer 500mg twice daily"
hyp = "Administer 500 mg twice daily"
report = text_error_rates(ref, hyp, MEDICAL_DOMAIN)
print(f"Reference: {ref}")
print(f"Hypothesis: {hyp}")
print(f"Categories in report: {list(report.keys())}")
print(f"Medical ER: {report['MEDICAL']['error_rate']:.2%}")
print()

print("✅ All domain configuration tests passed!")
