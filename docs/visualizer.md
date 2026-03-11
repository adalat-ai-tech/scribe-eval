# Interactive Visualizer

DictErrors includes a Streamlit-based web UI for exploring alignment and error metrics interactively.

## Launching

```bash
streamlit run visualizer.py
```

## Tabs

### Manual Inspection

Enter reference and hypothesis text directly to:
- View token-level alignment with color coding:
  - Green: correct matches
  - Red: substitutions, insertions, deletions
  - Blue: Sandhi corrections (merged/split Indic words)
- See category-specific error rates (WER, LER, NER, PER)
- Compare against baseline jiwer WER

### Batch Dataset Analysis

Upload a JSONL file to get aggregate metrics across multiple samples:

- Overall error rates (WER, LER, NER, PER) with Sandhi counts
- Per-dataset breakdown table
- Individual record inspection via dropdown — full alignment visualization per sample

## Sidebar Options

| Option | Description |
|---|---|
| **Sandhi Detection** | Toggle Sandhi split/merge detection on/off |
| **Normalize** | Toggle token normalization (date/currency format variations) |

## Session State

The visualizer stores the last 100 batch results in session state, including field names (`ref_col`, `hyp_col`). This preserves results across Streamlit re-runs (e.g., when clicking the file uploader) and prevents crashes when accessing stored results.

Use the **Clear Session Data** button to reset all stored results.

## JSONL Input Format

See [Batch Processing — Input Format](./batch-processing.md#input-format) for the expected JSONL structure and field names.
