#!/usr/bin/env python3
"""
Test the reporting module functions.
"""
from dicterrors import text_error_rates
from dicterrors.reporting import (
    format_metrics_dict,
    format_dataset_table,
    format_error_counts_table,
    format_alignment_table
)
from dicterrors import legal_aware_tokenizer, align_arrays

def test_format_metrics_dict():
    """Test format_metrics_dict function."""
    print("=" * 70)
    print("TEST: format_metrics_dict")
    print("=" * 70)

    # Generate a sample report
    ref = "U/S 302 IPC on 22.05.2023"
    hyp = "US 302 IPC on 22/05/2023"
    report = text_error_rates(ref, hyp)

    # Format metrics
    metrics = format_metrics_dict(report)

    print("\nFormatted Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    # Verify structure
    assert 'WER' in metrics
    assert 'LER' in metrics
    assert 'NER' in metrics
    assert 'PER' in metrics
    assert 'Sandhi' in metrics
    assert 'Total' in metrics

    print("\n✅ format_metrics_dict test passed!")
    return True


def test_format_error_counts_table():
    """Test format_error_counts_table function."""
    print("\n" + "=" * 70)
    print("TEST: format_error_counts_table")
    print("=" * 70)

    # Generate a sample report
    ref = "പണം അക്കൗണ്ടിൽ എത്തിയപ്പോൾ."
    hyp = "പണം അക്കൗണ്ടിൽ എത്തി:"
    report = text_error_rates(ref, hyp)

    # Format error counts
    counts = format_error_counts_table(report)

    print(f"\nGenerated {len(counts)} error count rows")
    print("Sample rows:")
    for i, row in enumerate(counts[:4]):
        print(f"  {row}")

    # Verify structure
    assert len(counts) == 16  # 4 categories × 4 types
    assert all('Category' in row for row in counts)
    assert all('Type' in row for row in counts)
    assert all('Count' in row for row in counts)

    print("\n✅ format_error_counts_table test passed!")
    return True


def test_format_alignment_table():
    """Test format_alignment_table function."""
    print("\n" + "=" * 70)
    print("TEST: format_alignment_table")
    print("=" * 70)

    # Tokenize and align
    ref = "U/S 302 IPC"
    hyp = "US 302 IPC"

    t1, g1 = legal_aware_tokenizer(ref)
    t2, g2 = legal_aware_tokenizer(hyp)
    aligned_ref, aligned_hyp, score = align_arrays(t1, g1, t2, g2)

    # Format alignment
    alignment = format_alignment_table(aligned_ref, aligned_hyp)

    print(f"\nGenerated {len(alignment)} alignment rows")
    print("Sample rows:")
    for row in alignment[:3]:
        print(f"  {row}")

    # Verify structure
    assert len(alignment) > 0
    assert all('Position' in row for row in alignment)
    assert all('Reference' in row for row in alignment)
    assert all('Hypothesis' in row for row in alignment)
    assert all('Error Type' in row for row in alignment)
    assert all('Token Type' in row for row in alignment)

    print("\n✅ format_alignment_table test passed!")
    return True


def test_format_dataset_table():
    """Test format_dataset_table function."""
    print("\n" + "=" * 70)
    print("TEST: format_dataset_table")
    print("=" * 70)

    # Create mock aggregate results
    mock_agg = {
        'overall': {
            'WORD': {'error_rate': 0.05, 'sandhi_hits': 2, 'combined_total': 100},
            'LEGAL': {'error_rate': 0.01, 'sandhi_hits': 0, 'combined_total': 100},
            'NUMERAL': {'error_rate': 0.00, 'sandhi_hits': 0, 'combined_total': 100},
            'PUNCT': {'error_rate': 0.03, 'sandhi_hits': 0, 'combined_total': 100}
        },
        'by_dataset': {
            'dataset_A': {
                'WORD': {'error_rate': 0.06, 'sandhi_hits': 1, 'combined_total': 50},
                'LEGAL': {'error_rate': 0.02, 'sandhi_hits': 0, 'combined_total': 50},
                'NUMERAL': {'error_rate': 0.00, 'sandhi_hits': 0, 'combined_total': 50},
                'PUNCT': {'error_rate': 0.04, 'sandhi_hits': 0, 'combined_total': 50}
            },
            'dataset_B': {
                'WORD': {'error_rate': 0.04, 'sandhi_hits': 1, 'combined_total': 50},
                'LEGAL': {'error_rate': 0.00, 'sandhi_hits': 0, 'combined_total': 50},
                'NUMERAL': {'error_rate': 0.00, 'sandhi_hits': 0, 'combined_total': 50},
                'PUNCT': {'error_rate': 0.02, 'sandhi_hits': 0, 'combined_total': 50}
            }
        }
    }

    # Format dataset table
    table = format_dataset_table(mock_agg)

    print(f"\nGenerated {len(table)} table rows")
    print("Rows:")
    for row in table:
        print(f"  {row['Dataset']}: WER={row['WER']}, LER={row['LER']}, Sandhi={row['Sandhi']}")

    # Verify structure
    assert len(table) == 3  # OVERALL + 2 datasets
    assert table[0]['Dataset'] == 'OVERALL'
    assert all('WER' in row for row in table)
    assert all('LER' in row for row in table)
    assert all('NER' in row for row in table)
    assert all('PER' in row for row in table)
    assert all('Sandhi' in row for row in table)

    print("\n✅ format_dataset_table test passed!")
    return True


def main():
    print("\n" + "=" * 70)
    print("REPORTING MODULE TESTS")
    print("=" * 70)

    tests = [
        test_format_metrics_dict,
        test_format_error_counts_table,
        test_format_alignment_table,
        test_format_dataset_table
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("\n🎉 All reporting module tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
