import streamlit as st
import sys
import os
import json
import pandas as pd
import jiwer
from pathlib import Path

# --- SETUP PATHS ---
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from dicterrors.tokenize import tokenizer
    from dicterrors.measure import token_error_rates
    from dicterrors.align import align_arrays, DEFAULT_WEIGHTS, is_number, is_word, is_punctuation
except ImportError as e:
    st.error(f"Error importing modules: {e}. Make sure you are running this from the project root.")
    st.stop()

# --- HELPER: HTML GENERATOR ---
def generate_alignment_html(ref_tokens, hyp_tokens):
    """Generates the HTML table for alignment visualization."""
    html = '<div class="scroll-container"><table class="alignment-table"><tr>'
    for r, h in zip(ref_tokens, hyp_tokens):
        
        # --- 1. Detect Status & Clean Text ---
        status = "s-correct"
        token_type = "t-word"
        
        # Handle Special Split/Merge Tags from align.py
        if r.startswith("MERGE:"):
            status = "s-merge"  # Only purple box, not an error
            r = r.replace("MERGE:", "") # Clean text
        elif h.startswith("SPLIT:"):
            status = "s-merge"  # Use same style for both split/merge (only purple box)
            h = h.replace("SPLIT:", "") # Clean text
        
        # Handle Standard Errors
        elif r == "**" or r == "<eps>": 
            status = "s-ins"
        elif h == "**" or h == "<eps>":
            status = "s-del"
        elif r != h:
            status = "s-sub"
        
        # --- 2. Determine Border Type (Word vs Num vs Punct) ---
        # We check the content of the cleaned text
        check_content = r if r not in ["**", "<eps>"] else h
        
        # If it's a split/merge, we treat it as a word usually, but let's check content
        if " " in check_content: # It's a compound token
            token_type = "t-word"
        elif is_number(check_content):
            token_type = "t-number"
        elif is_punctuation(check_content):
            token_type = "t-punct"
        else:
            token_type = "t-word"
        
        # --- 3. Prepare Display Text ---
        disp_r = r if (r != "**" and r != "<eps>") else "&nbsp;"
        disp_h = h if (h != "**" and h != "<eps>") else "&nbsp;"
        
        # Render Cell
        html += f"<td class=\"token-cell {status} {token_type}\"><div class=\"top-text\">{disp_r}</div><div class=\"bot-text\">{disp_h}</div></td>"
    
    html += "</tr></table></div>"
    return html

# --- UI CONFIG ---
st.set_page_config(layout="wide", page_title="DictErrors vs Jiwer")

st.title("⚖️ Error Analysis: DictErrors vs Jiwer")
st.markdown("Compare custom Indic-aware alignment against standard Jiwer.")

# --- SIDEBAR: CONTROLS ---
st.sidebar.header("🔧 Custom Penalty Tuning")
weights = {}

# We create sliders based on DEFAULT_WEIGHTS
# Note: We added new weights for Sandhi in align.py, so we add sliders for them too
with st.sidebar.expander("Agglutination (Sandhi)", expanded=True):
    weights['split_merge_penalty'] = st.slider("Split/Merge Penalty", -2.0, 0.0, float(DEFAULT_WEIGHTS.get('split_merge_penalty', -0.5)), 0.1, help="Cost for combining 2 words to match 1. Closer to 0 means easier to merge.")
    weights['sandhi_threshold'] = st.slider("Sandhi Char Tolerance", 0, 5, int(DEFAULT_WEIGHTS.get('sandhi_threshold', 2)), 1, help="How many characters can differ when merging? (e.g. 'kk' in Mazhakkalathu)")

with st.sidebar.expander("Gap Penalties", expanded=False):
    weights['gap_punct_num'] = st.slider("Gap: Punct/Num", -5.0, 0.0, float(DEFAULT_WEIGHTS['gap_punct_num']), 0.5)
    weights['gap_word_base'] = st.slider("Gap: Word Base", -5.0, 0.0, float(DEFAULT_WEIGHTS['gap_word_base']), 0.5)
    weights['gap_word_factor'] = st.slider("Gap: Word Length Factor", 0.0, 2.0, float(DEFAULT_WEIGHTS['gap_word_factor']), 0.1)

with st.sidebar.expander("Mismatch Penalties", expanded=False):
    weights['mismatch_punct_cross'] = st.slider("Sub: Punct ↔ Word", -10.0, -1.0, float(DEFAULT_WEIGHTS['mismatch_punct_cross']), 0.5)
    weights['mismatch_word_num'] = st.slider("Sub: Word ↔ Num", -10.0, -1.0, float(DEFAULT_WEIGHTS['mismatch_word_num']), 0.5)
    weights['mismatch_num_num'] = st.slider("Sub: Num ↔ Num", -5.0, 0.0, float(DEFAULT_WEIGHTS['mismatch_num_num']), 0.5)
    weights['mismatch_punct_punct'] = st.slider("Sub: Punct ↔ Punct", -5.0, 0.0, float(DEFAULT_WEIGHTS['mismatch_punct_punct']), 0.5)
    weights['mismatch_word_base'] = st.slider("Sub: Word Base", -5.0, 0.0, float(DEFAULT_WEIGHTS['mismatch_word_base']), 0.5)
    weights['match_base'] = st.slider("Match Reward", 1.0, 5.0, float(DEFAULT_WEIGHTS['match_base']), 0.5)


# --- MAIN INPUT ---
tab1, tab2 = st.tabs(["Text Input", "JSON File"])

# Initialize action flags
use_manual_input = False
use_json_single = False
use_json_batch = False

# Tab 1: Manual text input
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        # Default example updated to show Sandhi
        ref_text = st.text_area("Reference", height=120, value="തദ്ദേശ സ്വയംഭരണ സ്ഥാപനങ്ങൾ")
    with col2:
        hyp_text = st.text_area("Hypothesis", height=120, value="തദ്ദേശ സ്വയംഭരണസ്ഥാപനങ്ങൾ")
        
    use_manual_input = st.button("Compare Alignments", type="primary")

# Tab 2: JSON file input
with tab2:
    # Default JSONL file path
    default_jsonl_path = os.path.join(os.path.dirname(__file__), 'examples', 'dictation-eval', 'predictions.jsonl')
    
    # Check if default file exists
    default_exists = os.path.exists(default_jsonl_path)
    
    if default_exists:
        st.info(f"Default example file available: examples/dictation-eval/predictions.jsonl")
        use_default = st.checkbox("Use default example file", value=False)
    else:
        use_default = False
    
    # File uploader for custom files
    uploaded_file = st.file_uploader("Upload JSON file with predictions", type=["json", "jsonl"])
    
    # Use either uploaded file or default file
    using_default = False
    
    if uploaded_file is not None:
        st.success("Using uploaded file")
    elif use_default and default_exists:
        using_default = True
        st.success("Using default example file")
    
    if uploaded_file is not None or (use_default and default_exists):
        # Read the uploaded file
        try:
            # Check if it's a JSONL file (multiple JSON objects, one per line)
            if (uploaded_file is not None and uploaded_file.name.endswith('.jsonl')) or (using_default):
                # Read as lines and parse each line as JSON
                if using_default:
                    # Read from default file path
                    with open(default_jsonl_path, 'r', encoding='utf-8') as f:
                        content = f.read().splitlines()
                else:
                    # Read from uploaded file
                    content = uploaded_file.getvalue().decode('utf-8').splitlines()
                
                records = [json.loads(line) for line in content if line.strip()]
                st.success(f"Successfully loaded {len(records)} records from JSONL file")
            else:
                # Regular JSON file
                content = json.load(uploaded_file)
                # Check if it's an array of objects or a single object
                if isinstance(content, list):
                    records = content
                else:
                    records = [content]
                st.success(f"Successfully loaded {len(records)} records from JSON file")
            
            # Check for required fields in the first record
            first_record = records[0] if records else {}
            
            col1, col2 = st.columns(2)
            with col1:
                # For the sample JSONL file, the reference field is 'transcript_cleaned'
                default_ref_index = 0
                if "transcript_cleaned" in first_record:
                    default_ref_index = list(first_record.keys()).index("transcript_cleaned")
                elif "text" in first_record:
                    default_ref_index = list(first_record.keys()).index("text")
                elif "reference" in first_record:
                    default_ref_index = list(first_record.keys()).index("reference")
                    
                ref_field = st.selectbox(
                    "Select reference field", 
                    options=list(first_record.keys()),
                    index=default_ref_index,
                    help="Field containing the reference/ground truth text"
                )
            
            with col2:
                # For the sample JSONL file, the hypothesis field is 'prediction'
                default_hyp_index = 0
                if "prediction" in first_record:
                    default_hyp_index = list(first_record.keys()).index("prediction")
                elif "hypothesis" in first_record:
                    default_hyp_index = list(first_record.keys()).index("hypothesis")
                    
                hyp_field = st.selectbox(
                    "Select hypothesis field", 
                    options=list(first_record.keys()),
                    index=default_hyp_index,
                    help="Field containing the prediction/hypothesis text"
                )
            
            # Show a preview of the data
            if st.checkbox("Show data preview"):
                preview_df = pd.DataFrame([
                    {ref_field: r.get(ref_field, ""), hyp_field: r.get(hyp_field, "")} 
                    for r in records[:5]  # Show only first 5 records
                ])
                st.dataframe(preview_df)
            
            # Option to analyze all or a specific record
            analysis_choice = st.radio(
                "Choose what to analyze:",
                options=["Analyze specific record", "Analyze all records (summary statistics)"],
                horizontal=True
            )
            
            if analysis_choice == "Analyze specific record":
                # Let user select a specific record
                record_idx = st.number_input(
                    "Select record index", 
                    min_value=0, 
                    max_value=len(records)-1, 
                    value=0,
                    step=1,
                    help="Index of the record to analyze"
                )
                
                # Get the selected record
                selected_record = records[record_idx]
                ref_text = selected_record.get(ref_field, "")
                hyp_text = selected_record.get(hyp_field, "")
                
                # Show the selected texts
                st.markdown("**Selected Record:**")
                st.markdown(f"**Reference:** {ref_text}")
                st.markdown(f"**Hypothesis:** {hyp_text}")
                
                if st.button("Analyze Selected Record", type="primary"):
                    use_json_single = True
            
            else:  # Analyze all records
                # Extract all texts for batch processing
                all_refs = [r.get(ref_field, "") for r in records]
                all_hyps = [r.get(hyp_field, "") for r in records]
                
                if st.button("Analyze All Records", type="primary"):
                    use_json_batch = True
                
        except Exception as e:
            st.error(f"Error processing the JSON file: {str(e)}")
            use_json_single = False
            use_json_batch = False
    else:
        use_json_single = False
        use_json_batch = False

if use_manual_input or use_json_single:
    
    # --- 1. DictErrors Calculation ---
    custom_ref_tok = tokenizer(ref_text)
    custom_hyp_tok = tokenizer(hyp_text)
    c_ref, c_hyp, c_score = align_arrays(custom_ref_tok, custom_hyp_tok, weights=weights)
    
    # Note: calculate_error_rates might need updates to handle "SPLIT:" tags if you want strict counting
    # For now, it will likely treat "SPLIT:..." as a string mismatch unless we clean it inside token_error_rates too.
    # But for visualization, this is fine.
    c_wer, c_per, c_ner, c_report = token_error_rates(c_ref, c_hyp)

    # --- 2. Jiwer Calculation ---
    jiwer_out = jiwer.process_words(ref_text, hyp_text)
    
    # Extract Jiwer Alignment
    j_ref_viz = []
    j_hyp_viz = []
    
    for chunk in jiwer_out.alignments[0]:
        if chunk.type == 'equal':
            j_ref_viz.extend([ref_text.split()[i] for i in range(chunk.ref_start_idx, chunk.ref_end_idx)])
            j_hyp_viz.extend([hyp_text.split()[i] for i in range(chunk.hyp_start_idx, chunk.hyp_end_idx)])
        elif chunk.type == 'substitute':
            j_ref_viz.extend([ref_text.split()[i] for i in range(chunk.ref_start_idx, chunk.ref_end_idx)])
            j_hyp_viz.extend([hyp_text.split()[i] for i in range(chunk.hyp_start_idx, chunk.hyp_end_idx)])
        elif chunk.type == 'delete':
            for i in range(chunk.ref_start_idx, chunk.ref_end_idx):
                j_ref_viz.append(ref_text.split()[i])
                j_hyp_viz.append("**")
        elif chunk.type == 'insert':
            for i in range(chunk.hyp_start_idx, chunk.hyp_end_idx):
                j_ref_viz.append("**")
                j_hyp_viz.append(hyp_text.split()[i])

    # --- CSS STYLING ---
    st.markdown("""
    <style>
        .scroll-container { overflow-x: auto; white-space: nowrap; padding-bottom: 15px; width: 100%; border: 1px solid #eee; border-radius: 8px; background: #fafafa; }
        table.alignment-table { border-collapse: separate; border-spacing: 8px; margin: 10px; }
        td.token-cell { border-radius: 6px; padding: 8px 12px; text-align: center; min-width: 60px; font-family: sans-serif; vertical-align: middle; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .top-text { font-size: 1em; font-weight: bold; color: #666; border-bottom: 1px solid rgba(0,0,0,0.1);}
        .bot-text { font-size: 1em; margin-bottom: 4px; padding-bottom: 2px; }
        
        /* Standard Status Colors */
        .s-correct { background-color: #d1e7dd; color: #0f5132; } /* Green */
        .s-sub     { background-color: #f8d7da; color: #842029; } /* Red */
        .s-ins     { background-color: #ffe0b2; color: #7d4e00; } /* Orange */
        .s-del     { background-color: #ffe0b2; color: #7d4e00; } /* Orange */
        
        /* Sandhi: Split/Merge Colors (Purple/Indigo) - not considered an error */
        .s-merge { 
            background-color: #e0e7ff; 
            color: #3730a3; 
            border: 1px solid #6366f1 !important; 
        }

        /* Token Type Borders */
        .t-word   { border: 4px solid #a3cfbb; } 
        .t-number { border: 2px double #d32f2f; }
        .t-punct  { border: 4px dashed #9c27b0; }

        .wer-primary { font-size: 28px; font-weight: bold; color: #1e88e5; }
        .metrics-container { border: 1px solid #eee; border-radius: 10px; padding: 15px; background-color: #fafafa; }
    </style>
    """, unsafe_allow_html=True)

    # --- DISPLAY RESULTS ---
    st.subheader("1. Alignment Visualization")

    tab1, tab2 = st.tabs(["✨ DictErrors Alignment", "Jiwer Alignment"])

    with tab1:
        st.write("#### DictErrors Logic")
        st.write("Look for the **Purple Boxes** indicating Split/Merge handling. These are not considered errors.")
        st.markdown(generate_alignment_html(c_ref, c_hyp), unsafe_allow_html=True)
        with st.expander("Detailed Report"):
            st.json(c_report)

    with tab2:
        st.write("#### Jiwer Logic")
        st.markdown(generate_alignment_html(j_ref_viz, j_hyp_viz), unsafe_allow_html=True)

    st.subheader("2. Metric Comparison")
    
    m_col1, m_col2 = st.columns(2)
    
    with m_col1:
        st.subheader("[DictErrors](https://github.com/adalat-ai-tech/dict-errors)")
        st.markdown(f"""
        <div class="metrics-container">
            <div style="font-size: 20px; font-weight: bold; color: #1e88e5;">WER: {c_wer:.2%}</div>
            <div>PER: {c_per:.2%} | NER: {c_ner:.2%}</div>
        </div>
        """, unsafe_allow_html=True)

    with m_col2:
        st.subheader("[Jiwer](https://github.com/jitsi/jiwer)")
        st.markdown(f"""
        <div class="metrics-container">
            <div style="font-size: 20px; font-weight: bold; color: #666;">WER: {jiwer_out.wer:.2%}</div>
            <div>MER: {jiwer_out.mer:.2%}</div>
        </div>
        """, unsafe_allow_html=True)

# Add batch analysis for JSON files
elif use_json_batch:
    # Calculate metrics for all records
    all_c_wer = []
    all_c_per = []
    all_c_ner = []
    all_j_wer = []
    all_j_mer = []
    
    # Process each record
    for ref, hyp in zip(all_refs, all_hyps):
        if not ref or not hyp:  # Skip empty records
            continue
            
        # DictErrors
        try:
            custom_ref_tok = tokenizer(ref)
            custom_hyp_tok = tokenizer(hyp)
            _, _, _ = align_arrays(custom_ref_tok, custom_hyp_tok, weights=weights)
            c_wer, c_per, c_ner, _ = token_error_rates(custom_ref_tok, custom_hyp_tok)
            all_c_wer.append(c_wer)
            all_c_per.append(c_per)
            all_c_ner.append(c_ner)
        except Exception as e:
            st.warning(f"DictErrors error on text: '{ref[:30]}...': {str(e)}")
        
        # Jiwer
        try:
            jiwer_out = jiwer.process_words(ref, hyp)
            all_j_wer.append(jiwer_out.wer)
            all_j_mer.append(jiwer_out.mer)
        except Exception as e:
            st.warning(f"Jiwer error on text: '{ref[:30]}...': {str(e)}")
    
    # Display results
    st.subheader("Batch Analysis Results")
    st.write(f"Processed {len(all_c_wer)} records successfully")
    
    # Metrics summary
    metrics_df = pd.DataFrame({
        "DictErrors WER": all_c_wer,
        "DictErrors PER": all_c_per,
        "DictErrors NER": all_c_ner,
        "Jiwer WER": all_j_wer,
        "Jiwer MER": all_j_mer
    })
    
    # Summary statistics
    st.subheader("Summary Statistics")
    st.write(metrics_df.describe())
    
    # Option to download results
    csv = metrics_df.to_csv(index=False)
    st.download_button(
        label="Download metrics as CSV",
        data=csv,
        file_name="alignment_metrics.csv",
        mime="text/csv"
    )


