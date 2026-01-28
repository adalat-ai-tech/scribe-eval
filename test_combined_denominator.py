#!/usr/bin/env python3
"""
Test script to verify combined denominator implementation.

Expected behavior with combined denominator:
- 100 WORD tokens, 5 errors → Error rate: 5/126 = 3.97%
- 1 LEGAL token, 1 error → Error rate: 1/126 = 0.79%
- 10 NUMERAL tokens, 0 errors → Error rate: 0/126 = 0.00%
- 15 PUNCT tokens, 2 errors → Error rate: 2/126 = 1.59%

Combined total = 100 + 1 + 10 + 15 = 126
"""

from src.dicterrors.measure import token_error_rates

# Create a synthetic aligned reference and hypothesis to match the test case
# We'll create tuples of (text, tag) representing aligned tokens

aligned_ref = []
aligned_hyp = []

# 100 WORD tokens: 5 substitutions, 95 correct
for i in range(95):
    aligned_ref.append((f"word{i}", "WORD"))
    aligned_hyp.append((f"word{i}", "WORD"))  # Correct

for i in range(95, 100):
    aligned_ref.append((f"word{i}", "WORD"))
    aligned_hyp.append((f"wrong{i}", "WORD"))  # Substitution

# 1 LEGAL token: 1 substitution
aligned_ref.append(("धारा", "LEGAL"))
aligned_hyp.append(("धरा", "LEGAL"))  # Substitution

# 10 NUMERAL tokens: 0 errors (all correct)
for i in range(10):
    aligned_ref.append((f"{i}", "NUMERAL"))
    aligned_hyp.append((f"{i}", "NUMERAL"))  # Correct

# 15 PUNCT tokens: 2 substitutions, 13 correct
for i in range(13):
    aligned_ref.append((".", "PUNCT"))
    aligned_hyp.append((".", "PUNCT"))  # Correct

for i in range(2):
    aligned_ref.append((".", "PUNCT"))
    aligned_hyp.append((",", "PUNCT"))  # Substitution

# Run the error rate calculation
report = token_error_rates(aligned_ref, aligned_hyp)

# Print results
print("\n" + "="*80)
print("Combined Denominator Test Results")
print("="*80)

combined_total = report["WORD"]["combined_total"]
print(f"\nCombined Total: {combined_total}")
print(f"Expected: 126")
print(f"Match: {'✓' if combined_total == 126 else '✗'}")

print("\n" + "-"*80)
print(f"{'Category':<10} | {'Errors':>7} | {'Total':>7} | {'Error Rate':>12} | {'Expected':>12}")
print("-"*80)

test_cases = [
    ("WORD", 5, 100, 5/126),
    ("LEGAL", 1, 1, 1/126),
    ("NUMERAL", 0, 10, 0/126),
    ("PUNCT", 2, 15, 2/126),
]

all_passed = True
for cat, expected_errors, expected_total, expected_rate in test_cases:
    r = report[cat]
    actual_errors = r["substitutions"] + r["insertions"] + r["deletions"]
    actual_rate = r["error_rate"]
    actual_total = r["total_ref"]

    errors_match = actual_errors == expected_errors
    total_match = actual_total == expected_total
    rate_match = abs(actual_rate - expected_rate) < 0.0001

    status = "✓" if (errors_match and total_match and rate_match) else "✗"

    print(f"{cat:<10} | {actual_errors:>7} | {actual_total:>7} | {actual_rate:>11.2%} | {expected_rate:>11.2%} {status}")

    if not (errors_match and total_match and rate_match):
        all_passed = False
        if not errors_match:
            print(f"  ERROR: Expected {expected_errors} errors, got {actual_errors}")
        if not total_match:
            print(f"  ERROR: Expected {expected_total} total, got {actual_total}")
        if not rate_match:
            print(f"  ERROR: Expected {expected_rate:.4%} rate, got {actual_rate:.4%}")

print("="*80)

if all_passed:
    print("\n✓ All tests passed! Combined denominator is working correctly.")
else:
    print("\n✗ Some tests failed. Please review the output above.")

print("\nDetailed Report:")
print("-"*80)
for cat in ["WORD", "LEGAL", "NUMERAL", "PUNCT"]:
    r = report[cat]
    print(f"\n{cat}:")
    print(f"  Substitutions: {r['substitutions']}")
    print(f"  Insertions: {r['insertions']}")
    print(f"  Deletions: {r['deletions']}")
    print(f"  Correct: {r['correct']}")
    print(f"  Total Ref: {r['total_ref']}")
    print(f"  Error Rate: {r['error_rate']:.4%}")
    print(f"  Combined Total: {r['combined_total']}")

print("\n")
