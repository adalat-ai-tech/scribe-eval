import streamlit as st
import sys
import os
import json
import pandas as pd
import jiwer
from collections import defaultdict
from dicterrors import tokenizer, token_error_rates, align_arrays, DEFAULT_WEIGHTS, is_number, is_punctuation, compute_aggregate_metrics, compute_sample_errors
import tempfile 


# --- HELPER: HTML GENERATOR ---
def generate_alignment_html(ref_tokens, hyp_tokens):
    """Generates the HTML table for alignment visualization."""
    html = '<div class="scroll-container"><table class="alignment-table"><tr>'
    for r, h in zip(ref_tokens, hyp_tokens):
        
        # --- 1. Detect Status & Clean Text ---
        status = "s-correct"
        token_type = "t-word"
        
        if r.startswith("MERGE:"):
            status = "s-merge"
            r = r.replace("MERGE:", "")
        elif h.startswith("SPLIT:"):
            status = "s-merge"
            h = h.replace("SPLIT:", "")
        elif r == "**" or r == "<eps>": 
            status = "s-ins"
        elif h == "**" or h == "<eps>":
            status = "s-del"
        elif r != h:
            status = "s-sub"
        
        # --- 2. Determine Border Type ---
        check_content = r if r not in ["**", "<eps>"] else h
        if " " in check_content: token_type = "t-word"
        elif is_number(check_content): token_type = "t-number"
        elif is_punctuation(check_content): token_type = "t-punct"
        else: token_type = "t-word"
        
        disp_r = r if (r != "**" and r != "<eps>") else "&nbsp;"
        disp_h = h if (h != "**" and h != "<eps>") else "&nbsp;"
        
        html += f"<td class=\"token-cell {status} {token_type}\"><div class=\"top-text\">{disp_r}</div><div class=\"bot-text\">{disp_h}</div></td>"
    
    html += "</tr></table></div>"
    return html

# --- HELPER: RENDER ANALYSIS ---
def render_analysis(ref_text, hyp_text, weights):
    """Reusable function to render the metrics and visualization."""
    
    # 1. DictErrors Calculation
    custom_ref_tok = tokenizer(ref_text)
    custom_hyp_tok = tokenizer(hyp_text)
    c_ref, c_hyp, c_score = align_arrays(custom_ref_tok, custom_hyp_tok, weights=weights)
    c_wer, c_per, c_ner, c_report = token_error_rates(c_ref, c_hyp)

    # 2. Jiwer Calculation
    jiwer_out = jiwer.process_words(ref_text, hyp_text)
    
    # Extract Jiwer Alignment
    j_ref_viz, j_hyp_viz = [], []
    for chunk in jiwer_out.alignments[0]:
        if chunk.type in ['equal', 'substitute']:
            j_ref_viz.extend([ref_text.split()[i] for i in range(chunk.ref_start_idx, chunk.ref_end_idx)])
            j_hyp_viz.extend([hyp_text.split()[i] for i in range(chunk.hyp_start_idx, chunk.hyp_end_idx)])
        elif chunk.type == 'delete':
            for i in range(chunk.ref_start_idx, chunk.ref_end_idx):
                j_ref_viz.append(ref_text.split()[i]); j_hyp_viz.append("**")
        elif chunk.type == 'insert':
            for i in range(chunk.hyp_start_idx, chunk.hyp_end_idx):
                j_ref_viz.append("**"); j_hyp_viz.append(hyp_text.split()[i])

    # 3. Render CSS
    st.markdown("""
    <style>
        .scroll-container { overflow-x: auto; white-space: nowrap; padding-bottom: 15px; width: 100%; border: 1px solid #eee; border-radius: 8px; background: #fafafa; }
        table.alignment-table { border-collapse: separate; border-spacing: 8px; margin: 10px; }
        td.token-cell { border-radius: 6px; padding: 8px 12px; text-align: center; min-width: 60px; font-family: sans-serif; vertical-align: middle; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .top-text { font-size: 1em; font-weight: bold; color: #666; border-bottom: 1px solid rgba(0,0,0,0.1);}
        .bot-text { font-size: 1em; margin-bottom: 4px; padding-bottom: 2px; }
        .s-correct { background-color: #d1e7dd; color: #0f5132; }
        .s-sub     { background-color: #f8d7da; color: #842029; }
        .s-ins, .s-del { background-color: #ffe0b2; color: #7d4e00; }
        .s-merge { background-color: #e0e7ff; color: #3730a3; border: 1px solid #6366f1 !important; }
        .t-word   { border: 4px solid #a3cfbb; } 
        .t-number { border: 2px double #d32f2f; }
        .t-punct  { border: 4px dashed #9c27b0; }
        .metrics-container { border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 10px; padding: 15px; background-color: rgba(250, 250, 250, 0.8); color: rgba(0, 0, 0, 0.87); }
        .metric-value { font-size: 24px; font-weight: bold; color: #1e88e5; }
        .jiwer-metric { color: #9c27b0; }
        .metric-secondary { font-size: 16px; color: rgba(0, 0, 0, 0.8); }
    </style>
    """, unsafe_allow_html=True)

    # 4. Render UI
    st.subheader("1. Alignment Visualization")
    t1, t2 = st.tabs(["✨ DictErrors Alignment", "Jiwer Alignment"])
    
    with t1:
        st.write("**Purple Boxes** indicate Split/Merge handling (Sandhi).")
        st.markdown(generate_alignment_html(c_ref, c_hyp), unsafe_allow_html=True)
        with st.expander("Detailed Report"): st.json(c_report)
    with t2:
        st.markdown(generate_alignment_html(j_ref_viz, j_hyp_viz), unsafe_allow_html=True)

    st.subheader("2. Metric Comparison")
    mc1, mc2 = st.columns(2)
    with mc1:
        st.subheader("DictErrors")
        st.markdown(f"""<div class="metrics-container"><div class="metric-value">WER: {c_wer:.2%}</div><div class="metric-secondary">PER: {c_per:.2%} | NER: {c_ner:.2%}</div></div>""", unsafe_allow_html=True)
    with mc2:
        st.subheader("Jiwer")
        st.markdown(f"""<div class="metrics-container"><div class="metric-value jiwer-metric">WER: {jiwer_out.wer:.2%}</div><div class="metric-secondary">MER: {jiwer_out.mer:.2%}</div></div>""", unsafe_allow_html=True)


# --- UI CONFIG ---
st.set_page_config(layout="wide", page_title="DictErrors vs Jiwer")
st.title("⚖️ Error Analysis: DictErrors vs Jiwer")

# --- SIDEBAR ---
st.sidebar.header("🔧 Custom Penalty Tuning")
weights = {}
with st.sidebar.expander("Agglutination (Sandhi)", expanded=True):
    weights['split_merge_penalty'] = st.slider("Split/Merge Penalty", -2.0, 0.0, float(DEFAULT_WEIGHTS.get('split_merge_penalty', -0.5)), 0.1)
    weights['sandhi_threshold'] = st.slider("Sandhi Char Tolerance", 0, 5, int(DEFAULT_WEIGHTS.get('sandhi_threshold', 2)), 1)
with st.sidebar.expander("Gap & Mismatch", expanded=False):
    weights['gap_punct_num'] = st.slider("Gap: Punct/Num", -5.0, 0.0, float(DEFAULT_WEIGHTS['gap_punct_num']), 0.5)
    weights['gap_word_base'] = st.slider("Gap: Word Base", -5.0, 0.0, float(DEFAULT_WEIGHTS['gap_word_base']), 0.5)
    weights['gap_word_factor'] = st.slider("Gap: Word Length Factor", 0.0, 2.0, float(DEFAULT_WEIGHTS['gap_word_factor']), 0.1)
    weights['mismatch_word_base'] = st.slider("Sub: Word Base", -5.0, 0.0, float(DEFAULT_WEIGHTS['mismatch_word_base']), 0.5)
    weights['match_base'] = st.slider("Match Reward", 1.0, 5.0, float(DEFAULT_WEIGHTS['match_base']), 0.5)
    # Add other weights as needed...
    weights['mismatch_punct_cross'] = float(DEFAULT_WEIGHTS['mismatch_punct_cross'])
    weights['mismatch_word_num'] = float(DEFAULT_WEIGHTS['mismatch_word_num'])
    weights['mismatch_num_num'] = float(DEFAULT_WEIGHTS['mismatch_num_num'])
    weights['mismatch_punct_punct'] = float(DEFAULT_WEIGHTS['mismatch_punct_punct'])

# --- MAIN INPUT ---
tab_manual, tab_json = st.tabs(["Text Input", "JSON File"])

# --- TAB 1: MANUAL ---
with tab_manual:
    mc1, mc2 = st.columns(2)
    with mc1:
        m_ref = st.text_area("Reference", height=100, value="തദ്ദേശ സ്വയംഭരണ സ്ഥാപനങ്ങൾ")
    with mc2:
        m_hyp = st.text_area("Hypothesis", height=100, value="തദ്ദേശ സ്വയംഭരണസ്ഥാപനങ്ങൾ")
    
    if st.button("Compare Manual Input", type="primary"):
        render_analysis(m_ref, m_hyp, weights)

# --- TAB 2: JSON ---
with tab_json:
    
    # 1. LOAD DATA SECTION (Collapsible)
    with st.expander("📂 Load Data Configuration", expanded=True):
        col_load, col_map = st.columns([1, 2])
        
        records = []
        default_path = os.path.join(os.path.dirname(__file__), 'examples', 'dictation-eval', 'predictions.jsonl')
        
        with col_load:
            upload_opt = st.radio("Source", ["Default Example", "Upload File"], horizontal=True, label_visibility="collapsed")
            data_content = None
            
            if upload_opt == "Upload File":
                uploaded = st.file_uploader("Upload .jsonl", type=["jsonl", "json"], label_visibility="collapsed")
                if uploaded: data_content = uploaded.getvalue().decode('utf-8').splitlines()
            elif os.path.exists(default_path):
                with open(default_path, 'r', encoding='utf-8') as f:
                    data_content = f.read().splitlines()
            
            if data_content:
                try:
                    records = [json.loads(line) for line in data_content if line.strip()]
                    if not isinstance(records, list): records = [records] 
                    st.success(f"Loaded {len(records)} records")
                except Exception as e:
                    st.error(f"Error parsing JSON: {e}")

        with col_map:
            if records:
                keys = list(records[0].keys())
                # Smart defaults helper
                def get_idx(options, search):
                    for s in search:
                        if s in options: return options.index(s)
                    return 0

                c1, c2, c3 = st.columns(3)
                with c1: ref_col = st.selectbox("Reference Field", keys, index=get_idx(keys, ["transcript_cleaned", "text", "reference"]))
                with c2: hyp_col = st.selectbox("Hypothesis Field", keys, index=get_idx(keys, ["prediction", "hypothesis"]))
                
                # Make Source ID Optional
                source_options = ["(None)"] + keys
                default_src_idx = 0
                for s in ["source_dataset", "file_path", "audio_path"]:
                    if s in keys:
                        default_src_idx = source_options.index(s)
                        break
                
                with c3: 
                    src_col_selection = st.selectbox("Source ID Field (Optional)", source_options, index=default_src_idx)
                    src_col = None if src_col_selection == "(None)" else src_col_selection

    if records:
        # 2. BATCH ANALYSIS SECTION (Now at the top)
        st.markdown("### 📊 Dataset Evaluation")
        
        with st.expander("Compute Aggregate Statistics (WER/PER/NER)", expanded=False):
            if st.button("Run Batch Evaluation", type="primary", use_container_width=True):
                
                with st.spinner("Processing records..."):
                    # Create a temporary file to store the JSONL data for the function to read
                    with tempfile.NamedTemporaryFile(mode='w+', suffix='.jsonl', delete=False, encoding='utf-8') as tmp_in:
                        # Write current records to temp file
                        for r in records:
                            tmp_in.write(json.dumps(r, ensure_ascii=False) + '\n')
                        tmp_in_path = tmp_in.name
                    
                    try:
                        # --- 1. CALL YOUR EXISTING BACKEND FUNCTION ---
                        # We pass None as output_file so it returns the list directly 
                        # without needing another read operation, though we can save if needed.
                        detailed_results = compute_sample_errors(
                            input_file=tmp_in_path,
                            output_file=None, # We get results in return
                            ref_field=ref_col,
                            hyp_field=hyp_col,
                            source_dataset_field=src_col if src_col else "source_dataset", # Handle None
                            audio_path_field="file_path" # Default or mapping if you have it
                        )
                        
                        # --- 2. AGGREGATION ---
                        agg_stats = compute_aggregate_metrics(detailed_results)
                        
                        # --- 3. DISPLAY TABLE ---
                        table_rows = []
                        def get_row_data(name, metrics):
                            return {
                                "Dataset": name,
                                "WER": f"{metrics['word']['error_rate']:.2%}",
                                "PER": f"{metrics['punctuation']['error_rate']:.2%}",
                                "NER": f"{metrics['numeral']['error_rate']:.2%}",
                                "Sandhi Count": metrics['word']['sandhi_splits'] + metrics['word']['sandhi_merges']
                            }
                        
                        table_rows.append(get_row_data("OVERALL", agg_stats["overall"]))
                        for source, metrics in agg_stats["by_dataset"].items():
                            # Filter out "Unknown" if we have other valid sources
                            if source != "Unknown" or len(agg_stats["by_dataset"]) > 1:
                                table_rows.append(get_row_data(source, metrics))
                        
                        st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True)

                        # --- 4. DOWNLOADS ---
                        d_col1, d_col2 = st.columns(2)
                        
                        # Detailed JSONL
                        jsonl_str = "\n".join([json.dumps(r, ensure_ascii=False) for r in detailed_results])
                        d_col1.download_button("📥 Download Detailed JSONL", jsonl_str, "evaluation_detailed.jsonl", "application/json", use_container_width=True)
                        
                        # Summary TXT
                        summary_txt = f"{'DATASET':<20} | {'WER':<8} | {'PER':<8} | {'NER':<8} | {'SANDHI'}\n" + "-"*65 + "\n"
                        def format_txt_row(name, m):
                            s = m['word']['sandhi_splits'] + m['word']['sandhi_merges']
                            return f"{name:<20} | {m['word']['error_rate']:8.2%} | {m['punctuation']['error_rate']:8.2%} | {m['numeral']['error_rate']:8.2%} | {s:<4}\n"
                        
                        summary_txt += format_txt_row("OVERALL", agg_stats["overall"]) + "-"*65 + "\n"
                        for source, metrics in agg_stats["by_dataset"].items():
                            summary_txt += format_txt_row(source, metrics)

                        d_col2.download_button("📄 Download Summary TXT", summary_txt, "evaluation_summary.txt", "text/plain", use_container_width=True)
                        
                    finally:
                        # Cleanup temp file
                        if os.path.exists(tmp_in_path):
                            os.unlink(tmp_in_path)
        # 3. INDIVIDUAL RECORD ANALYSIS (Below)
        st.markdown("### 🔍 Individual Record Analysis")
        
        # Create a display list for the selectbox
        def format_option(i, r):
            source_tag = f"[{r.get(src_col, 'N/A')}] " if src_col else ""
            text_preview = r.get(ref_col, '')[:100]
            return f"{i+1}. {source_tag}{text_preview}..."

        display_options = [format_option(i, r) for i, r in enumerate(records)]
        
        sel_idx = st.selectbox("Select a record to visualize:", range(len(records)), format_func=lambda x: display_options[x], label_visibility="collapsed")
        
        selected_record = records[sel_idx]
        selected_ref = selected_record.get(ref_col, "")
        selected_hyp = selected_record.get(hyp_col, "")

        # 4. RENDER ANALYSIS
        if selected_ref and selected_hyp:
            render_analysis(selected_ref, selected_hyp, weights)