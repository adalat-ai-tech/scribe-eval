import streamlit as st
import sys
import os
import json
import pandas as pd
import jiwer
import tempfile
from pathlib import Path
from dicterrors import (
    domain_aware_tokenizer,
    align_arrays,
    token_error_rates,
    compute_aggregate_metrics,
    compute_sample_errors,
    DEFAULT_WEIGHTS,
    CAT_WORD, CAT_PUNCT, CAT_NUMERAL,
    LEGAL_DOMAIN
)
from dicterrors.reporting import (
    format_dataset_table,
    format_error_counts_table,
    extract_error_rates,
    format_alignment_dict
)

def parse_data(content_list):
    """Handles both JSON (list of dicts) and JSONL (line by line)."""
    # Join the lines to check the overall structure
    full_content = "\n".join(content_list).strip()
    
    # Try parsing as a standard JSON list first
    if full_content.startswith("["):
        try:
            return json.loads(full_content)
        except:
            pass
            
    # Fallback to JSONL (line by line)
    records = []
    for line in content_list:
        if line.strip():
            try:
                records.append(json.loads(line))
            except Exception as e:
                st.error(f"Failed to parse line: {line[:50]}... Error: {e}")
    return records


# --- HELPER: CSS INJECTION (Restored & Enhanced) ---
def inject_custom_css():
    st.markdown("""
    <style>
        .scroll-container { overflow-x: auto; white-space: nowrap; padding-bottom: 15px; width: 100%; border: 1px solid #eee; border-radius: 8px; background: #fafafa; }
        table.alignment-table { border-collapse: separate; border-spacing: 8px; margin: 10px; }
        td.token-cell { border-radius: 6px; padding: 8px 12px; text-align: center; min-width: 80px; font-family: sans-serif; vertical-align: middle; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .top-text { font-size: 1em; font-weight: bold; color: #666; border-bottom: 1px solid rgba(0,0,0,0.1);}
        .bot-text { font-size: 1em; margin-bottom: 4px; padding-bottom: 2px; color: #000; }
        .tag-label { font-size: 0.65em; font-weight: bold; text-transform: uppercase; opacity: 0.5; margin-top: 4px; display: block;}
        
        /* Status Colors */
        .s-correct { background-color: #d1e7dd; color: #0f5132; }
        .s-sub     { background-color: #f8d7da; color: #842029; }
        .s-ins, .s-del { background-color: #ffe0b2; color: #7d4e00; }
        .s-merge   { background-color: #e0e7ff; color: #3730a3; border: 2px solid #6366f1 !important; }
        
        /* Category Border Styles */
        .t-WORD    { border: 3px solid #a3cfbb; } 
        .t-NUMERAL { border: 3px solid #d32f2f; }
        .t-PUNCT   { border: 3px dashed #9c27b0; }
        .t-LEGAL   { border: 4px solid #1a237e; box-shadow: 0 0 8px rgba(26, 35, 126, 0.4); }
        
        .metrics-container { border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 10px; padding: 15px; background-color: rgba(250, 250, 250, 0.8); color: rgba(0, 0, 0, 0.87); }
        .metric-value { font-size: 24px; font-weight: bold; color: #1e88e5; }
        .metric-legal { color: #1a237e; margin: 10px 0; }
        .jiwer-metric { color: #9c27b0; }
        .metric-secondary { font-size: 20px; color: rgba(0, 0, 0, 0.8); }
    </style>
    """, unsafe_allow_html=True)

# --- HELPER: HTML GENERATOR (Tagged Version) ---
def generate_alignment_html(aligned_ref, aligned_hyp):
    """
    aligned_ref/hyp: List of tuples (text, tag)
    Uses shared format_alignment_dict() for error detection logic.
    """
    # Use shared alignment logic
    alignment_data = format_alignment_dict(aligned_ref, aligned_hyp)

    # Map error types to CSS classes
    status_map = {
        'correct': 's-correct',
        'substitution': 's-sub',
        'insertion': 's-ins',
        'deletion': 's-del',
        'sandhi': 's-merge'
    }

    html = '<div class="scroll-container"><table class="alignment-table"><tr>'

    for item in alignment_data:
        status = status_map.get(item['error_type'], 's-correct')
        border_class = f"t-{item['token_type']}"

        # Replace ** with &nbsp; for display
        disp_r = item['ref_text'] if item['ref_text'] != "**" else "&nbsp;"
        disp_h = item['hyp_text'] if item['hyp_text'] != "**" else "&nbsp;"

        html += f"""
        <td class="token-cell {status} {border_class}">
            <div class="top-text">{disp_r}</div>
            <div class="bot-text">{disp_h}</div>
            <div class="tag-label">{item['token_type']}</div>
        </td>"""

    html += "</tr></table></div>"
    return html

# --- HELPER: METRIC CARD RENDERER ---
def render_metrics_comparison(report, jiwer_wer, domain_config):
    mc1, mc2 = st.columns(2)
    with mc1:
        st.subheader("DictErrors (Domain-Aware)")
        # Use shared error rate extraction function
        rates = extract_error_rates(report, domain_config)

        # Get domain label dynamically
        domain_label_lower = domain_config.label.lower() if domain_config else "der"

        st.markdown(f"""
        <div class="metrics-container">
            <div class="metric-value">General WER: {rates['wer']:.2%}</div>
            <div class="metric-value metric-legal">{domain_config.name.title()} WER: {rates[domain_label_lower]:.2%}</div>
            <div class="metric-secondary">Numeral WER: {rates['ner']:.2%}</div>
            <div class="metric-secondary">Punctuation WER: {rates['per']:.2%}</div>
        </div>
        """, unsafe_allow_html=True)
    with mc2:
        st.subheader("Jiwer Baseline")
        st.markdown(f"""
        <div class="metrics-container">
            <div class="metric-value jiwer-metric">Global WER: {jiwer_wer:.2%}</div>
            <div class="metric-secondary">Standard word-level calculation without category shielding or Sandhi awareness.</div>
        </div>
        """, unsafe_allow_html=True)

# --- HELPER: RENDER ANALYSIS ---
def render_analysis(ref_text, hyp_text, weights):
    # Use legal domain configuration
    domain_config = LEGAL_DOMAIN

    # 1. DictErrors Calculation
    t1, g1 = domain_aware_tokenizer(ref_text, domain_config)
    t2, g2 = domain_aware_tokenizer(hyp_text, domain_config)
    a_ref, a_hyp, _ = align_arrays(t1, g1, t2, g2, weights=weights)
    report = token_error_rates(a_ref, a_hyp, domain_config)

    # 2. Jiwer Calculation
    j_wer = jiwer.wer(ref_text, hyp_text)

    # 3. Render
    st.subheader("Alignment Visualization")
    st.markdown(generate_alignment_html(a_ref, a_hyp), unsafe_allow_html=True)
    render_metrics_comparison(report, j_wer, domain_config)


# --- UI CONFIG ---
st.set_page_config(layout="wide", page_title="DictErrors Legal Visualizer")
st.title("⚖️ DictErrors vs Jiwer: Legal & Indic Evaluation")
inject_custom_css()

# --- SIDEBAR: WEIGHT TUNING (Restored) ---
st.sidebar.header("🔧 Penalty Tuning")
weights = {}

with st.sidebar.expander("Category Penalties", expanded=True):
    weights['gap_penalty'] = st.slider("Gap Penalty - General", -5.0, 0.0, DEFAULT_WEIGHTS['gap_penalty'], 0.5)
    weights['gap_penalty_punct'] = st.slider("Gap Penalty - Punctuation", -5.0, 0.0, DEFAULT_WEIGHTS['gap_penalty_punct'], 0.1)
    weights['mismatch_default_penalty'] = st.slider("Mismatch Penalty - Default", -5.0, 0.0, DEFAULT_WEIGHTS['mismatch_default_penalty'], 0.5)
    weights['mismatch_cross_punct_penalty'] = st.slider("Mismatch Penalty - Cross-Category Punct", -10.0, 0.0, DEFAULT_WEIGHTS['mismatch_cross_punct_penalty'], 1.0)
    weights['match_reward'] = st.slider("Match Reward", 1.0, 5.0, DEFAULT_WEIGHTS['match_reward'], 0.5)

with st.sidebar.expander("Agglutination & Sandhi", expanded=False):
    weights['split_merge_penalty'] = st.slider("Split/Merge Penalty", -2.0, 0.0, DEFAULT_WEIGHTS['split_merge_penalty'], 0.1)
    weights['sandhi_char_tolerence'] = st.slider("Sandhi Char Tolerance", 0, 5, DEFAULT_WEIGHTS['sandhi_char_tolerence'], 1)

# Session state management
st.sidebar.divider()
st.sidebar.header("🗑️ Session Management")
if st.sidebar.button("Clear Session Data"):
    if 'detailed_results' in st.session_state:
        del st.session_state['detailed_results']
    if 'global_jiwer' in st.session_state:
        del st.session_state['global_jiwer']
    if 'ref_col' in st.session_state:
        del st.session_state['ref_col']
    if 'hyp_col' in st.session_state:
        del st.session_state['hyp_col']
    st.rerun()

# --- MAIN INPUT ---
tab_manual, tab_json = st.tabs(["Manual Inspection", "Batch Dataset Analysis"])

with tab_manual:
    mc1, mc2 = st.columns(2)
    with mc1: m_ref = st.text_area("Reference", height=100, value="U/S 302 പ്രകാരം മഴക്കാലത്ത് ശിക്ഷിക്കപ്പെടും")
    with mc2: m_hyp = st.text_area("Hypothesis", height=100, value="US 302 പ്രകാരം മഴ കാലത്ത് ശിക്ഷിക്കപ്പെടും")
    if st.button("Analyze Manual Input", type="primary"):
        render_analysis(m_ref, m_hyp, weights)

 #--- UPDATED TAB 2: JSON/JSONL ---
with tab_json:
    col_config, col_batch = st.columns([1, 1], gap="large")
    records = []
    
    # Robust Default Path: Looking in the current dir /dictation-eval/
    # Adjust this if your folder structure is different!
    base_dir = Path(__file__).parent
    default_path = base_dir / "examples" / "dictation-eval" / "predictions.jsonl"
    
    with col_config:
        st.markdown("### 📂 Load Data")
        upload_opt = st.radio("Source", ["Default Path", "Upload File"], horizontal=True)
        data_content = None
        
        if upload_opt == "Upload File":
            # ACCEPT BOTH JSON AND JSONL
            uploaded = st.file_uploader("Upload File", type=["json", "jsonl"])
            if uploaded:
                data_content = uploaded.getvalue().decode('utf-8').splitlines()
        else:
            # CHECK DEFAULT PATH
            if default_path.exists():
                with open(default_path, 'r', encoding='utf-8') as f:
                    data_content = f.readlines()
            else:
                st.warning(f"Default file not found at: `{default_path.relative_to(base_dir)}`")
        
        if data_content:
            records = parse_data(data_content)
            if records:
                st.success(f"Successfully loaded {len(records)} records")

                # Field validation with error handling
                try:
                    keys = list(records[0].keys())
                    # Auto-select fields if they exist
                    def_ref = keys.index("transcript_cleaned") if "transcript_cleaned" in keys else 0
                    def_hyp = keys.index("prediction") if "prediction" in keys else 0
                except (KeyError, IndexError) as e:
                    st.error(f"Error accessing record fields: {e}")
                    keys = []
                    def_ref = 0
                    def_hyp = 0

                if keys:
                    ref_col = st.selectbox("Reference Field", keys, index=def_ref)
                    hyp_col = st.selectbox("Hypothesis Field", keys, index=def_hyp)
                    src_col = st.selectbox("Dataset Split Field", ["(None)"] + keys)

    with col_batch:
        if records:
            st.markdown("### 📊 Dataset Evaluation")
            if st.button("Run Batch Evaluation", type="primary"):
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.jsonl', delete=False, encoding='utf-8') as tmp:
                    for r in records:
                        tmp.write(json.dumps(r, ensure_ascii=False) + '\n')
                    tmp_path = tmp.name
                
                try:
                    # Use legal domain configuration
                    domain_config = LEGAL_DOMAIN

                    # 1. DictErrors Calculation
                    res_detailed = compute_sample_errors(tmp_path, ref_field=ref_col, hyp_field=hyp_col, domain_config=domain_config)

                    # Ensure source_dataset is attached for aggregation
                    for i, r in enumerate(res_detailed):
                        r["source_dataset"] = records[i].get(src_col, "unknown") if src_col != "(None)" else "overall"

                    agg = compute_aggregate_metrics(res_detailed, domain_config=domain_config)

                    # 2. Jiwer Global Comparison
                    all_refs = [r.get(ref_col, "") for r in records]
                    all_hyps = [r.get(hyp_col, "") for r in records]
                    jiwer_wer = jiwer.wer(all_refs, all_hyps)

                    st.write("#### Overall Metrics")
                    # Using the consolidated 'error_rate' key
                    render_metrics_comparison(agg['overall'], jiwer_wer, domain_config)

                    # 3. Dataset Breakdown Table
                    st.write("#### Per-Dataset Breakdown")
                    table_data = format_dataset_table(agg, domain_config)
                    # Remove OVERALL row for display (already shown above)
                    table_data = [row for row in table_data if row['Dataset'] != 'OVERALL']
                    st.table(pd.DataFrame(table_data))

                    # 4. Detailed Error Counts Display (NEW)
                    with st.expander("📊 Detailed Error Counts"):
                        error_counts = format_error_counts_table(agg['overall'], domain_config)
                        st.dataframe(pd.DataFrame(error_counts), width='stretch')

                    # Save results to session state (limit to 100 most recent)
                    MAX_STORED_RESULTS = 100
                    st.session_state['detailed_results'] = res_detailed[-MAX_STORED_RESULTS:]
                    st.session_state['global_jiwer'] = jiwer_wer
                    st.session_state['ref_col'] = ref_col
                    st.session_state['hyp_col'] = hyp_col
                finally:
                    if os.path.exists(tmp_path): os.unlink(tmp_path)

    if 'detailed_results' in st.session_state:
        st.divider()
        st.markdown("### 🔍 Individual Record Inspection")
        res_list = st.session_state['detailed_results']
        # Retrieve field names from session state
        saved_ref_col = st.session_state.get('ref_col', 'reference')
        saved_hyp_col = st.session_state.get('hyp_col', 'hypothesis')

        idx = st.selectbox("Select record", range(len(res_list)),
                           format_func=lambda i: f"Record {i+1}: {res_list[i][saved_ref_col][:60]}...")

        sel = res_list[idx]
        render_analysis(sel[saved_ref_col], sel[saved_hyp_col], weights)