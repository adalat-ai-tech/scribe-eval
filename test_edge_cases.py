#!/usr/bin/env python3
"""
Test edge cases for combined denominator implementation.
"""

from src.dicterrors.measure import token_error_rates

def test_case(name, aligned_ref, aligned_hyp, expected_combined_total):
    """Run a test case and display results."""
    report = token_error_rates(aligned_ref, aligned_hyp)

    print(f"\n{'='*70}")
    print(f"Test Case: {name}")
    print('='*70)

    actual_combined = report["WORD"]["combined_total"]
    print(f"Combined Total: {actual_combined} (expected: {expected_combined_total})")

    if actual_combined != expected_combined_total:
        print(f"❌ FAILED: Combined total mismatch!")
        return False

    print(f"\n{'Category':<10} | {'Errors':>7} | {'Total':>7} | {'Error Rate':>12}")
    print('-'*70)

    passed = True
    for cat in ["WORD", "LEGAL", "NUMERAL", "PUNCT"]:
        r = report[cat]
        errors = r["substitutions"] + r["insertions"] + r["deletions"]
        rate = r["error_rate"]
        total = r["total_ref"]

        print(f"{cat:<10} | {errors:>7} | {total:>7} | {rate:>11.2%}")

        # Verify that error_rate = errors / combined_total
        expected_rate = errors / max(1, actual_combined)
        if abs(rate - expected_rate) > 0.0001:
            print(f"  ❌ ERROR: Expected rate {expected_rate:.4%}, got {rate:.4%}")
            passed = False

    if passed:
        print(f"\n✅ {name} PASSED")
    else:
        print(f"\n❌ {name} FAILED")

    return passed


# Test Case 1: Zero tokens in some categories
print("\n" + "="*70)
print("EDGE CASE TESTING")
print("="*70)

aligned_ref = []
aligned_hyp = []

# 100 WORD tokens, 5 errors
for i in range(95):
    aligned_ref.append((f"word{i}", "WORD"))
    aligned_hyp.append((f"word{i}", "WORD"))

for i in range(95, 100):
    aligned_ref.append((f"word{i}", "WORD"))
    aligned_hyp.append((f"wrong{i}", "WORD"))

# 0 LEGAL tokens
# 10 NUMERAL tokens, 0 errors
for i in range(10):
    aligned_ref.append((f"{i}", "NUMERAL"))
    aligned_hyp.append((f"{i}", "NUMERAL"))

# 5 PUNCT tokens, 0 errors
for i in range(5):
    aligned_ref.append((".", "PUNCT"))
    aligned_hyp.append((".", "PUNCT"))

test1_passed = test_case(
    "Zero LEGAL tokens",
    aligned_ref,
    aligned_hyp,
    expected_combined_total=115  # 100 + 0 + 10 + 5
)


# Test Case 2: Only one category has tokens
aligned_ref = []
aligned_hyp = []

# 1 LEGAL token, 1 error
aligned_ref.append(("धारा", "LEGAL"))
aligned_hyp.append(("धरा", "LEGAL"))

test2_passed = test_case(
    "Only LEGAL category has tokens",
    aligned_ref,
    aligned_hyp,
    expected_combined_total=1
)


# Test Case 3: Empty sample (all categories zero)
aligned_ref = []
aligned_hyp = []

test3_passed = test_case(
    "Empty sample (no tokens)",
    aligned_ref,
    aligned_hyp,
    expected_combined_total=0
)


# Test Case 4: Large class imbalance
aligned_ref = []
aligned_hyp = []

# 10,000 WORD tokens, 100 errors
for i in range(9900):
    aligned_ref.append((f"word{i}", "WORD"))
    aligned_hyp.append((f"word{i}", "WORD"))

for i in range(9900, 10000):
    aligned_ref.append((f"word{i}", "WORD"))
    aligned_hyp.append((f"wrong{i}", "WORD"))

# 1 LEGAL token, 1 error
aligned_ref.append(("धारा", "LEGAL"))
aligned_hyp.append(("धरा", "LEGAL"))

# 5 NUMERAL tokens, 0 errors
for i in range(5):
    aligned_ref.append((f"{i}", "NUMERAL"))
    aligned_hyp.append((f"{i}", "NUMERAL"))

# 50 PUNCT tokens, 2 errors
for i in range(48):
    aligned_ref.append((".", "PUNCT"))
    aligned_hyp.append((".", "PUNCT"))

for i in range(2):
    aligned_ref.append((".", "PUNCT"))
    aligned_hyp.append((",", "PUNCT"))

test4_passed = test_case(
    "Large class imbalance (10000:1:5:50)",
    aligned_ref,
    aligned_hyp,
    expected_combined_total=10056  # 10000 + 1 + 5 + 50
)


# Test Case 5: Insertions and Deletions
aligned_ref = []
aligned_hyp = []

# 10 WORD tokens: 2 substitutions, 1 deletion, 7 correct
for i in range(7):
    aligned_ref.append((f"word{i}", "WORD"))
    aligned_hyp.append((f"word{i}", "WORD"))

# 2 substitutions
for i in range(7, 9):
    aligned_ref.append((f"word{i}", "WORD"))
    aligned_hyp.append((f"wrong{i}", "WORD"))

# 1 deletion
aligned_ref.append(("deleted", "WORD"))
aligned_hyp.append(("**", "WORD"))  # ** indicates gap

# 1 insertion (1 WORD insertion)
aligned_ref.append(("**", "WORD"))
aligned_hyp.append(("inserted", "WORD"))

# 2 LEGAL tokens: 1 correct, 1 deletion
aligned_ref.append(("धारा", "LEGAL"))
aligned_hyp.append(("धारा", "LEGAL"))

aligned_ref.append(("न्यायालय", "LEGAL"))
aligned_hyp.append(("**", "LEGAL"))

test5_passed = test_case(
    "Insertions and Deletions",
    aligned_ref,
    aligned_hyp,
    expected_combined_total=12  # 10 WORD + 2 LEGAL (insertions not counted in total)
)


# Summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)

all_tests = [
    ("Zero LEGAL tokens", test1_passed),
    ("Only LEGAL category has tokens", test2_passed),
    ("Empty sample (no tokens)", test3_passed),
    ("Large class imbalance", test4_passed),
    ("Insertions and Deletions", test5_passed),
]

passed_count = sum(1 for _, passed in all_tests if passed)
total_count = len(all_tests)

print(f"\nTests passed: {passed_count}/{total_count}")

for name, passed in all_tests:
    status = "✅" if passed else "❌"
    print(f"{status} {name}")

if passed_count == total_count:
    print("\n🎉 All edge case tests passed!")
else:
    print(f"\n⚠️  {total_count - passed_count} test(s) failed.")

print()
