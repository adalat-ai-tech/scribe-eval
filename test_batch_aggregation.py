#!/usr/bin/env python3
"""
Test batch aggregation with combined denominator.
"""

from src.dicterrors.measure_batch import compute_aggregate_metrics

# Create mock sample results
sample_results = []

# Sample 1: 100 WORD, 1 LEGAL, 10 NUMERAL, 15 PUNCT
sample_results.append({
    "source_dataset": "dataset_A",
    "detailed_report": {
        "WORD": {
            "error_rate": 0.03968,  # Will be recalculated
            "substitutions": 5,
            "insertions": 0,
            "deletions": 0,
            "correct": 95,
            "total_ref": 100,
            "sandhi_hits": 2,
            "combined_total": 126
        },
        "LEGAL": {
            "error_rate": 0.007937,
            "substitutions": 1,
            "insertions": 0,
            "deletions": 0,
            "correct": 0,
            "total_ref": 1,
            "sandhi_hits": 0,
            "combined_total": 126
        },
        "NUMERAL": {
            "error_rate": 0.0,
            "substitutions": 0,
            "insertions": 0,
            "deletions": 0,
            "correct": 10,
            "total_ref": 10,
            "sandhi_hits": 0,
            "combined_total": 126
        },
        "PUNCT": {
            "error_rate": 0.015873,
            "substitutions": 2,
            "insertions": 0,
            "deletions": 0,
            "correct": 13,
            "total_ref": 15,
            "sandhi_hits": 0,
            "combined_total": 126
        }
    }
})

# Sample 2: 50 WORD, 0 LEGAL, 5 NUMERAL, 10 PUNCT (same dataset)
sample_results.append({
    "source_dataset": "dataset_A",
    "detailed_report": {
        "WORD": {
            "error_rate": 0.03077,
            "substitutions": 2,
            "insertions": 0,
            "deletions": 0,
            "correct": 48,
            "total_ref": 50,
            "sandhi_hits": 1,
            "combined_total": 65
        },
        "LEGAL": {
            "error_rate": 0.0,
            "substitutions": 0,
            "insertions": 0,
            "deletions": 0,
            "correct": 0,
            "total_ref": 0,
            "sandhi_hits": 0,
            "combined_total": 65
        },
        "NUMERAL": {
            "error_rate": 0.015385,
            "substitutions": 1,
            "insertions": 0,
            "deletions": 0,
            "correct": 4,
            "total_ref": 5,
            "sandhi_hits": 0,
            "combined_total": 65
        },
        "PUNCT": {
            "error_rate": 0.0,
            "substitutions": 0,
            "insertions": 0,
            "deletions": 0,
            "correct": 10,
            "total_ref": 10,
            "sandhi_hits": 0,
            "combined_total": 65
        }
    }
})

# Sample 3: 200 WORD, 5 LEGAL, 20 NUMERAL, 30 PUNCT (different dataset)
sample_results.append({
    "source_dataset": "dataset_B",
    "detailed_report": {
        "WORD": {
            "error_rate": 0.039216,
            "substitutions": 10,
            "insertions": 0,
            "deletions": 0,
            "correct": 190,
            "total_ref": 200,
            "sandhi_hits": 5,
            "combined_total": 255
        },
        "LEGAL": {
            "error_rate": 0.003922,
            "substitutions": 1,
            "insertions": 0,
            "deletions": 0,
            "correct": 4,
            "total_ref": 5,
            "sandhi_hits": 0,
            "combined_total": 255
        },
        "NUMERAL": {
            "error_rate": 0.0,
            "substitutions": 0,
            "insertions": 0,
            "deletions": 0,
            "correct": 20,
            "total_ref": 20,
            "sandhi_hits": 0,
            "combined_total": 255
        },
        "PUNCT": {
            "error_rate": 0.007843,
            "substitutions": 2,
            "insertions": 0,
            "deletions": 0,
            "correct": 28,
            "total_ref": 30,
            "sandhi_hits": 0,
            "combined_total": 255
        }
    }
})

print("="*80)
print("BATCH AGGREGATION TEST")
print("="*80)

print("\n📊 Test Data Summary:")
print("-"*80)
print("Sample 1 (dataset_A): 100W+1L+10N+15P=126 total, 5+1+0+2=8 errors")
print("Sample 2 (dataset_A): 50W+0L+5N+10P=65 total, 2+0+1+0=3 errors")
print("Sample 3 (dataset_B): 200W+5L+20N+30P=255 total, 10+1+0+2=13 errors")
print("-"*80)

# Compute aggregate metrics
agg = compute_aggregate_metrics(sample_results)

print("\n📈 Overall Aggregated Metrics:")
print("-"*80)
print(f"{'Category':<10} | {'Errors':>7} | {'Total':>7} | {'Error Rate':>12} | {'Combined':>10}")
print("-"*80)

# Expected values for overall
# WORD: (100+50+200)=350 total, (5+2+10)=17 errors
# LEGAL: (1+0+5)=6 total, (1+0+1)=2 errors
# NUMERAL: (10+5+20)=35 total, (0+1+0)=1 error
# PUNCT: (15+10+30)=55 total, (2+0+2)=4 errors
# Combined total = 350+6+35+55 = 446

expected_overall = {
    "WORD": {"total": 350, "errors": 17, "rate": 17/446},
    "LEGAL": {"total": 6, "errors": 2, "rate": 2/446},
    "NUMERAL": {"total": 35, "errors": 1, "rate": 1/446},
    "PUNCT": {"total": 55, "errors": 4, "rate": 4/446},
    "combined": 446
}

overall_passed = True
for cat in ["WORD", "LEGAL", "NUMERAL", "PUNCT"]:
    m = agg["overall"][cat]
    exp = expected_overall[cat]

    actual_rate = m["error_rate"]
    expected_rate = exp["rate"]
    actual_total = m["total"]
    expected_total = exp["total"]
    actual_combined = m["combined_total"]
    expected_combined = expected_overall["combined"]

    status = "✅" if (abs(actual_rate - expected_rate) < 0.0001 and
                     actual_total == expected_total and
                     actual_combined == expected_combined) else "❌"

    print(f"{cat:<10} | {exp['errors']:>7} | {actual_total:>7} | {actual_rate:>11.4%} | {actual_combined:>10} {status}")

    if status == "❌":
        overall_passed = False
        print(f"  Expected: rate={expected_rate:.4%}, total={expected_total}, combined={expected_combined}")

print("-"*80)
print(f"Expected combined total: {expected_overall['combined']}")
print(f"Actual combined total: {agg['overall']['WORD']['combined_total']}")

print("\n📊 Per-Dataset Metrics:")
print("-"*80)

# Dataset A: (100+50)=150 WORD, (1+0)=1 LEGAL, (10+5)=15 NUMERAL, (15+10)=25 PUNCT
# Combined = 150+1+15+25 = 191
# Errors: (5+2)=7 WORD, (1+0)=1 LEGAL, (0+1)=1 NUMERAL, (2+0)=2 PUNCT
expected_dataset_a = {
    "WORD": {"total": 150, "errors": 7, "rate": 7/191},
    "LEGAL": {"total": 1, "errors": 1, "rate": 1/191},
    "NUMERAL": {"total": 15, "errors": 1, "rate": 1/191},
    "PUNCT": {"total": 25, "errors": 2, "rate": 2/191},
    "combined": 191
}

print("\nDataset A:")
print(f"{'Category':<10} | {'Errors':>7} | {'Total':>7} | {'Error Rate':>12} | {'Combined':>10}")
print("-"*80)

dataset_a_passed = True
for cat in ["WORD", "LEGAL", "NUMERAL", "PUNCT"]:
    m = agg["by_dataset"]["dataset_A"][cat]
    exp = expected_dataset_a[cat]

    actual_rate = m["error_rate"]
    expected_rate = exp["rate"]
    actual_total = m["total"]
    expected_total = exp["total"]
    actual_combined = m["combined_total"]
    expected_combined = expected_dataset_a["combined"]

    status = "✅" if (abs(actual_rate - expected_rate) < 0.0001 and
                     actual_total == expected_total and
                     actual_combined == expected_combined) else "❌"

    print(f"{cat:<10} | {exp['errors']:>7} | {actual_total:>7} | {actual_rate:>11.4%} | {actual_combined:>10} {status}")

    if status == "❌":
        dataset_a_passed = False

# Dataset B: 200 WORD, 5 LEGAL, 20 NUMERAL, 30 PUNCT
# Combined = 200+5+20+30 = 255
# Errors: 10 WORD, 1 LEGAL, 0 NUMERAL, 2 PUNCT
expected_dataset_b = {
    "WORD": {"total": 200, "errors": 10, "rate": 10/255},
    "LEGAL": {"total": 5, "errors": 1, "rate": 1/255},
    "NUMERAL": {"total": 20, "errors": 0, "rate": 0/255},
    "PUNCT": {"total": 30, "errors": 2, "rate": 2/255},
    "combined": 255
}

print("\nDataset B:")
print(f"{'Category':<10} | {'Errors':>7} | {'Total':>7} | {'Error Rate':>12} | {'Combined':>10}")
print("-"*80)

dataset_b_passed = True
for cat in ["WORD", "LEGAL", "NUMERAL", "PUNCT"]:
    m = agg["by_dataset"]["dataset_B"][cat]
    exp = expected_dataset_b[cat]

    actual_rate = m["error_rate"]
    expected_rate = exp["rate"]
    actual_total = m["total"]
    expected_total = exp["total"]
    actual_combined = m["combined_total"]
    expected_combined = expected_dataset_b["combined"]

    status = "✅" if (abs(actual_rate - expected_rate) < 0.0001 and
                     actual_total == expected_total and
                     actual_combined == expected_combined) else "❌"

    print(f"{cat:<10} | {exp['errors']:>7} | {actual_total:>7} | {actual_rate:>11.4%} | {actual_combined:>10} {status}")

    if status == "❌":
        dataset_b_passed = False

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

all_passed = overall_passed and dataset_a_passed and dataset_b_passed

if all_passed:
    print("\n✅ All batch aggregation tests passed!")
    print("   - Overall metrics correctly aggregated")
    print("   - Per-dataset metrics correctly aggregated")
    print("   - Combined denominators correctly calculated")
else:
    print("\n❌ Some tests failed:")
    if not overall_passed:
        print("   - Overall metrics aggregation failed")
    if not dataset_a_passed:
        print("   - Dataset A aggregation failed")
    if not dataset_b_passed:
        print("   - Dataset B aggregation failed")

print()
