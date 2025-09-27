import json
import os
from src.measure import text_error_rates
import json
from collections import defaultdict
from tabulate import tabulate
import sys
import argparse

def calculate_error_rate(substitutions, insertions, deletions, total_reference):
    """
    Calculates an error rate (WER, PER, NER) given counts.
    Returns percentage.
    """
    errors = substitutions + insertions + deletions
    if total_reference == 0:
        return 0.0 if errors == 0 else float('inf') # 0 if no reference and no errors, else infinity
    return (errors / total_reference) * 100

def calculate_rate(count, total_reference):
    """
    Calculates a rate (e.g., insertion rate, correct rate) given a count and total reference.
    Returns percentage.
    """
    if total_reference == 0:
        return 0.0 if count == 0 else float('inf') # 0 if no reference and no count, else infinity
    return (count / total_reference) * 100

def calculate_simple_average(rates_list):
    """
    Calculates the simple arithmetic mean of a list of rates,
    ignoring float('inf') values (N/A).
    Returns float('inf') if all values are inf, otherwise the average.
    """
    valid_rates = [rate for rate in rates_list if rate != float('inf')]
    if not valid_rates:
        return float('inf') # If all datasets had N/A for this metric
    return sum(valid_rates) / len(valid_rates)

def format_value(value, is_percentage=True):
    """Formats a float or inf value for display."""
    if value == float('inf'):
        return "N/A"
    if is_percentage:
        return f"{value:.2f}%"
    return str(value) # For counts, just return as string

def generate_asr_report_tables(data):
    """
    Parses ASR evaluation results and generates three detailed reports by source dataset:
    Words, Punctuation, and Numerals.
    Each table includes "Dataset Average" and "Weighted Average (Overall)" rows.
    """
    aggregated_data = defaultdict(lambda: {
        "word": {"substitutions": 0, "insertions": 0, "deletions": 0, "correct": 0, "total_reference": 0},
        "punctuation": {"substitutions": 0, "insertions": 0, "deletions": 0, "correct": 0, "total_reference": 0},
        "numeral": {"substitutions": 0, "insertions": 0, "deletions": 0, "correct": 0, "total_reference": 0}
    })

    # Initialize grand totals for overall weighted averages
    grand_totals = {
        "word": {"substitutions": 0, "insertions": 0, "deletions": 0, "correct": 0, "total_reference": 0},
        "punctuation": {"substitutions": 0, "insertions": 0, "deletions": 0, "correct": 0, "total_reference": 0},
        "numeral": {"substitutions": 0, "insertions": 0, "deletions": 0, "correct": 0, "total_reference": 0}
    }

    for entry in data:
        dataset = entry['source_dataset']
        detailed_report = entry['detailed_report']

        for category in ['word', 'punctuation', 'numeral']:
            for key, value in detailed_report[category].items():
                if key != 'error_rate': # We calculate this ourselves
                    aggregated_data[dataset][category][key] += value
                    grand_totals[category][key] += value # Add to grand total for weighted average

    all_tables_output = []

    # --- Table 1: Word Details ---
    table1_data = []
    table1_headers = [
        "Source Dataset",
        "Ref Word Count",
        "Correct Rate",
        "Substitution Rate",
        "Insertion Rate",
        "Deletion Rate",
        "WER"
    ]

    # Lists to collect individual dataset rates for simple averaging
    word_correct_rates_for_simple_avg = []
    word_sub_rates_for_simple_avg = []
    word_ins_rates_for_simple_avg = []
    word_del_rates_for_simple_avg = []
    wer_rates_for_simple_avg = []

    for dataset, agg_counts in aggregated_data.items():
        word_err = agg_counts['word']
        total_ref = word_err['total_reference']
        
        correct_rate = calculate_rate(word_err['correct'], total_ref)
        sub_rate = calculate_rate(word_err['substitutions'], total_ref)
        ins_rate = calculate_rate(word_err['insertions'], total_ref)
        del_rate = calculate_rate(word_err['deletions'], total_ref)
        wer = calculate_error_rate(word_err['substitutions'], word_err['insertions'], word_err['deletions'], total_ref)

        table1_data.append([
            dataset,
            format_value(total_ref, is_percentage=False),
            format_value(correct_rate),
            format_value(sub_rate),
            format_value(ins_rate),
            format_value(del_rate),
            format_value(wer)
        ])
        # Populate lists for simple average
        word_correct_rates_for_simple_avg.append(correct_rate)
        word_sub_rates_for_simple_avg.append(sub_rate)
        word_ins_rates_for_simple_avg.append(ins_rate)
        word_del_rates_for_simple_avg.append(del_rate)
        wer_rates_for_simple_avg.append(wer)
    
    # Calculate and add Dataset Average row for Table 1
    avg_correct_rate = calculate_simple_average(word_correct_rates_for_simple_avg)
    avg_sub_rate = calculate_simple_average(word_sub_rates_for_simple_avg)
    avg_ins_rate = calculate_simple_average(word_ins_rates_for_simple_avg)
    avg_del_rate = calculate_simple_average(word_del_rates_for_simple_avg)
    avg_wer = calculate_simple_average(wer_rates_for_simple_avg)
    
    table1_data.append([
        "--- Dataset Simple Average ---",
        "N/A", # Ref Count column doesn't have a meaningful simple average here
        format_value(avg_correct_rate),
        format_value(avg_sub_rate),
        format_value(avg_ins_rate),
        format_value(avg_del_rate),
        format_value(avg_wer)
    ])

    # Calculate and add Weighted Average (Overall) row for Table 1
    grand_word_err = grand_totals['word']
    grand_total_ref = grand_word_err['total_reference']

    overall_correct_rate = calculate_rate(grand_word_err['correct'], grand_total_ref)
    overall_sub_rate = calculate_rate(grand_word_err['substitutions'], grand_total_ref)
    overall_ins_rate = calculate_rate(grand_word_err['insertions'], grand_total_ref)
    overall_del_rate = calculate_rate(grand_word_err['deletions'], grand_total_ref)
    overall_wer = calculate_error_rate(grand_word_err['substitutions'], grand_word_err['insertions'], grand_word_err['deletions'], grand_total_ref)

    table1_data.append([
        "--- Weighted Average (Overall) ---",
        format_value(grand_total_ref, is_percentage=False),
        format_value(overall_correct_rate),
        format_value(overall_sub_rate),
        format_value(overall_ins_rate),
        format_value(overall_del_rate),
        format_value(overall_wer)
    ])
    all_tables_output.append("### Table 1: Word Details\n" + tabulate(table1_data, headers=table1_headers, tablefmt="pipe"))


    # --- Table 2: Punctuation Details ---
    table2_data = []
    table2_headers = [
        "Source Dataset",
        "Ref Punctuation Count",
        "Correct Rate",
        "Substitution Rate",
        "Insertion Rate",
        "Deletion Rate",
        "PER"
    ]

    # Lists to collect individual dataset rates for simple averaging
    punc_correct_rates_for_simple_avg = []
    punc_sub_rates_for_simple_avg = []
    punc_ins_rates_for_simple_avg = []
    punc_del_rates_for_simple_avg = []
    per_rates_for_simple_avg = []

    for dataset, agg_counts in aggregated_data.items():
        punc_err = agg_counts['punctuation']
        total_ref = punc_err['total_reference']
        
        correct_rate = calculate_rate(punc_err['correct'], total_ref)
        sub_rate = calculate_rate(punc_err['substitutions'], total_ref)
        ins_rate = calculate_rate(punc_err['insertions'], total_ref)
        del_rate = calculate_rate(punc_err['deletions'], total_ref)
        per = calculate_error_rate(punc_err['substitutions'], punc_err['insertions'], punc_err['deletions'], total_ref)

        table2_data.append([
            dataset,
            format_value(total_ref, is_percentage=False),
            format_value(correct_rate),
            format_value(sub_rate),
            format_value(ins_rate),
            format_value(del_rate),
            format_value(per)
        ])
        # Populate lists for simple average
        punc_correct_rates_for_simple_avg.append(correct_rate)
        punc_sub_rates_for_simple_avg.append(sub_rate)
        punc_ins_rates_for_simple_avg.append(ins_rate)
        punc_del_rates_for_simple_avg.append(del_rate)
        per_rates_for_simple_avg.append(per)
    
    # Calculate and add Dataset Average row for Table 2
    avg_correct_rate = calculate_simple_average(punc_correct_rates_for_simple_avg)
    avg_sub_rate = calculate_simple_average(punc_sub_rates_for_simple_avg)
    avg_ins_rate = calculate_simple_average(punc_ins_rates_for_simple_avg)
    avg_del_rate = calculate_simple_average(punc_del_rates_for_simple_avg)
    avg_per = calculate_simple_average(per_rates_for_simple_avg)
    
    table2_data.append([
        "--- Dataset Average ---",
        "N/A", # Ref Count column doesn't have a meaningful simple average here
        format_value(avg_correct_rate),
        format_value(avg_sub_rate),
        format_value(avg_ins_rate),
        format_value(avg_del_rate),
        format_value(avg_per)
    ])

    # Calculate and add Weighted Average (Overall) row for Table 2
    grand_punc_err = grand_totals['punctuation']
    grand_total_ref = grand_punc_err['total_reference']

    overall_correct_rate = calculate_rate(grand_punc_err['correct'], grand_total_ref)
    overall_sub_rate = calculate_rate(grand_punc_err['substitutions'], grand_total_ref)
    overall_ins_rate = calculate_rate(grand_punc_err['insertions'], grand_total_ref)
    overall_del_rate = calculate_rate(grand_punc_err['deletions'], grand_total_ref)
    overall_per = calculate_error_rate(grand_punc_err['substitutions'], grand_punc_err['insertions'], grand_punc_err['deletions'], grand_total_ref)

    table2_data.append([
        "--- Weighted Average (Overall) ---",
        format_value(grand_total_ref, is_percentage=False),
        format_value(overall_correct_rate),
        format_value(overall_sub_rate),
        format_value(overall_ins_rate),
        format_value(overall_del_rate),
        format_value(overall_per)
    ])
    all_tables_output.append("\n### Table 2: Punctuation Details\n" + tabulate(table2_data, headers=table2_headers, tablefmt="pipe"))


    # --- Table 3: Numeral Details ---
    table3_data = []
    table3_headers = [
        "Source Dataset",
        "Ref Number Count",
        "Correct Rate",
        "Substitution Rate",
        "Insertion Rate",
        "Deletion Rate",
        "NER"
    ]

    # Lists to collect individual dataset rates for simple averaging
    num_correct_rates_for_simple_avg = []
    num_sub_rates_for_simple_avg = []
    num_ins_rates_for_simple_avg = []
    num_del_rates_for_simple_avg = []
    ner_rates_for_simple_avg = []

    for dataset, agg_counts in aggregated_data.items():
        num_err = agg_counts['numeral']
        total_ref = num_err['total_reference']
        
        correct_rate = calculate_rate(num_err['correct'], total_ref)
        sub_rate = calculate_rate(num_err['substitutions'], total_ref)
        ins_rate = calculate_rate(num_err['insertions'], total_ref)
        del_rate = calculate_rate(num_err['deletions'], total_ref)
        ner = calculate_error_rate(num_err['substitutions'], num_err['insertions'], num_err['deletions'], total_ref)

        table3_data.append([
            dataset,
            format_value(total_ref, is_percentage=False),
            format_value(correct_rate),
            format_value(sub_rate),
            format_value(ins_rate),
            format_value(del_rate),
            format_value(ner)
        ])
        # Populate lists for simple average
        num_correct_rates_for_simple_avg.append(correct_rate)
        num_sub_rates_for_simple_avg.append(sub_rate)
        num_ins_rates_for_simple_avg.append(ins_rate)
        num_del_rates_for_simple_avg.append(del_rate)
        ner_rates_for_simple_avg.append(ner)
    
    # Calculate and add Dataset Average row for Table 3
    avg_correct_rate = calculate_simple_average(num_correct_rates_for_simple_avg)
    avg_sub_rate = calculate_simple_average(num_sub_rates_for_simple_avg)
    avg_ins_rate = calculate_simple_average(num_ins_rates_for_simple_avg)
    avg_del_rate = calculate_simple_average(num_del_rates_for_simple_avg)
    avg_ner = calculate_simple_average(ner_rates_for_simple_avg)
    
    table3_data.append([
        "--- Dataset Average ---",
        "N/A", # Ref Count column doesn't have a meaningful simple average here
        format_value(avg_correct_rate),
        format_value(avg_sub_rate),
        format_value(avg_ins_rate),
        format_value(avg_del_rate),
        format_value(avg_ner)
    ])

    # Calculate and add Weighted Average (Overall) row for Table 3
    grand_num_err = grand_totals['numeral']
    grand_total_ref = grand_num_err['total_reference']

    overall_correct_rate = calculate_rate(grand_num_err['correct'], grand_total_ref)
    overall_sub_rate = calculate_rate(grand_num_err['substitutions'], grand_total_ref)
    overall_ins_rate = calculate_rate(grand_num_err['insertions'], grand_total_ref)
    overall_del_rate = calculate_rate(grand_num_err['deletions'], grand_total_ref)
    overall_ner = calculate_error_rate(grand_num_err['substitutions'], grand_num_err['insertions'], grand_num_err['deletions'], grand_total_ref)

    table3_data.append([
        "--- Dataset Weighted Average ---",
        format_value(grand_total_ref, is_percentage=False),
        format_value(overall_correct_rate),
        format_value(overall_sub_rate),
        format_value(overall_ins_rate),
        format_value(overall_del_rate),
        format_value(overall_ner)
    ])
    all_tables_output.append("\n### Table 3: Numeral Details\n" + tabulate(table3_data, headers=table3_headers, tablefmt="pipe"))

    return "\n".join(all_tables_output)

def evaluate_predictions(input_file, output_file):
    """Evaluate predictions and save results to a JSON file."""
    results = []

    with open(input_file, "r") as f:
        lines = f.readlines()

        for line in lines:
            data = json.loads(line)
            file_path = data["file_path"]
            ref_text = data["transcript_cleaned"]
            source_dataset = data["source_dataset"]
            hyp_text = data["prediction"]
            
            # Calculate error rates
            wer, per, ner, report = text_error_rates(ref_text, hyp_text)
            
            # Store results
            result = {
                "file_path": file_path,
                "ref_text": ref_text,
                "hyp_text": hyp_text,
                "source_dataset": source_dataset,
                "WER": wer,
                "PER": per,
                "NER": ner,
                "detailed_report": report
            }
            
            results.append(result)
    
    # Write results to JSON file
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Evaluation complete. Results saved to {output_file}")
    return results

def main():
    # Default paths
    input_file = "dictation-eval/predictions.jsonl"  # Updated to correct path
    evaluation_file = "dictation-eval/evaluation.json"
    report_file = "dictation-eval/evaluation_report.md"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Cannot find {input_file}")
        return
    
    results = evaluate_predictions(input_file, evaluation_file)
    try:
        with open(evaluation_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        report_content = generate_asr_report_tables(json_data)

        if report_file:
            with open(report_file, 'w', encoding='utf-8') as outfile:
                outfile.write(report_content)
            print(f"Report successfully saved to '{report_file}'")
        else:
            print(report_content)

    except FileNotFoundError:
        print(f"Error: The input file '{evaluation_file}' was not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{evaluation_file}'. Please check file format.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
    

if __name__ == "__main__":
    main()
