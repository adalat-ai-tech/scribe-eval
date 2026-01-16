import streamlit as st
import sys
import os
import jiwer

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
col1, col2 = st.columns(2)
with col1:
    # Default example updated to show Sandhi
    ref_text = st.text_area("Reference", height=120, value="മഴക്കാലത്ത് വെള്ളം പൊങ്ങി")
with col2:
    hyp_text = st.text_area("Hypothesis", height=120, value="മഴ കാലത്ത് വെള്ളം പൊങ്ങി")

if st.button("Compare Alignments", type="primary"):
    
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
        st.subheader("[DictErrors](https://github.com/kavyamanohar/dicterrors)")
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


