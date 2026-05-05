# Interactive Visualizer

scribe-eval ships a Streamlit-based web UI for exploring alignment and error metrics interactively.

## Launching

Install the `visualizer` extra and run the bundled command:

```bash
pip install 'scribe-eval[visualizer]'
scribe-visualizer
```

Any extra arguments are forwarded to `streamlit run` (e.g. `scribe-visualizer --server.port 8502`).

## Tabs

### Single Sample Analysis

Enter reference and hypothesis text directly. The view updates automatically on every change — no button press required.

- **Token-level alignment** with color coding:
  - Green: exact match
  - Red: substitution, insertion, or deletion
  - Blue: Sandhi correction (merged/split Indic word)
- **Token Error Rate** and **Accuracy** as metric tiles (hover on Accuracy for a note on why TER + Accuracy ≠ 100% when insertions or Sandhis are present)
- Category decomposition caption: `Word Tokens X% + Legal Tokens Y% + ... = TER%`
- **Jiwer WER and CER** shown side-by-side for baseline comparison
- **Error Analysis** expander:
  - Category contributions table (Ref Tokens, Exact Match, Accuracy, Sub, Del, Ins, Error Rate, Impact on Total)
  - Category breakdown chart (stacked bar: token matches left, TER contribution right)
- **Frequent Errors** expander: top-N substitutions, deletions, insertions, sandhi merges, sandhi splits across five sub-tabs (the two sandhi tabs are populated only when sandhi detection is enabled and the language has agglutinative compounds)

### Batch Dataset Analysis

Upload a JSONL file (or use the default path) to get aggregate metrics across multiple samples.

- Same **Token Error Rate + Accuracy** and **Jiwer WER + CER** metric tiles as Single Sample
- Category decomposition caption and Sandhis count
- Category contributions table and breakdown chart
- Frequent errors tables with adjustable top-N (changing top-N does not rerun the batch)
- Per-dataset breakdown table
- **Individual record inspection** — select a sample from a dropdown to see full alignment and per-sample metrics

## Sidebar Options

| Option | Description |
|---|---|
| **Domain Configuration** | Dropdown: Legal, Medical, Technical, From file, or None |
| **Sandhi Detection** | Toggle Sandhi split/merge detection on/off |
| **Normalize** | Toggle token normalization (date/currency format variations) |
| **Top N** | Slider (5–25): controls depth of frequent-error tables |
| **Category Penalties** | Advanced sliders for alignment scoring weights |

## Session State

The visualizer caches results in session state to survive Streamlit re-runs:

| Key | Content |
|---|---|
| `detailed_results` | Last 100 per-sample error dicts |
| `jiwer_stats` | Overall jiwer WER, CER, subs, ins, dels |
| `ref_col`, `hyp_col` | Field names used when the batch was loaded |
| `agg_metrics` | Output of `compute_aggregate_metrics()` |
| `all_error_details` | Flat list of per-token error records (for top-N recomputation) |
| `analysis_summary` | Output of `compute_error_summary()` at the current top-N |
| `domain_config_snapshot` | Domain config name/category at batch time |

Use the **Clear Session Data** button in the sidebar to reset all stored results.

## JSONL Input Format

See [Batch Processing — Input Format](./batch-processing.md#input-format) for the expected JSONL structure and field names.
