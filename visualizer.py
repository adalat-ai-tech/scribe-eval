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
        # Determine error status (substitution, insertion, deletion, correct)
        if r == "**" or r == "<eps>": 
            status = "s-ins"
        elif h == "**" or h == "<eps>":
            status = "s-del"
        elif r != h:
            status = "s-sub"
        else:
            status = "s-correct"
        
        # Determine token type (word, number, punctuation)
        token_type = ""
        
        # For insertion, only the hypothesis token matters
        if r == "**" or r == "<eps>":
            if is_number(h):
                token_type = "t-number"
            elif is_punctuation(h):
                token_type = "t-punct"
            else:
                token_type = "t-word"
        # For deletion, only the reference token matters
        elif h == "**" or h == "<eps>":
            if is_number(r):
                token_type = "t-number"
            elif is_punctuation(r):
                token_type = "t-punct"
            else:
                token_type = "t-word"
        # For substitution or correct match, we use the more specific type
        else:
            if is_number(r) or is_number(h):
                token_type = "t-number"
            elif is_punctuation(r) and is_punctuation(h):
                token_type = "t-punct"
            else:
                token_type = "t-word"
        
        # Display Text
        disp_r = r if (r != "**" and r != "<eps>") else "&nbsp;"
        disp_h = h if (h != "**" and h != "<eps>") else "&nbsp;"
        
        html += f"<td class=\"token-cell {status} {token_type}\"><div class=\"top-text\">{disp_r}</div><div class=\"bot-text\">{disp_h}</div></td>"
    html += "</tr></table></div>"
    return html

# --- UI CONFIG ---
st.set_page_config(layout="wide", page_title="DictErrors vs Jiwer")

st.title("⚖️ Benchmark: DictErrors vs Jiwer")
st.markdown("Compare your custom Indic-aware alignment against standard Jiwer.")

# --- SIDEBAR: CONTROLS ---
st.sidebar.header("🔧 Custom Penalty Tuning")
weights = {}
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
    ref_text = st.text_area("Reference", height=120, value="ഇന്ന് 9ാം തീയതിയാണ്, സമയം 9:60 വന്നു ഞാ പോയി")
with col2:
    hyp_text = st.text_area("Hypothesis", height=120, value="ഇന്ന് 9 ആം തീയതിയാണ് സമയം, 9 30 ഞാൻ ഞാങ്ങോട്ട് പോയി")

if st.button("Compare Alignments", type="primary"):
    
    # --- 1. DictErrors Calculation ---
    custom_ref_tok = tokenizer(ref_text)
    custom_hyp_tok = tokenizer(hyp_text)
    c_ref, c_hyp, c_score = align_arrays(custom_ref_tok, custom_hyp_tok, weights=weights)
    c_wer, c_per, c_ner, c_report = token_error_rates(c_ref, c_hyp)

    # --- 2. Jiwer Calculation ---
    # Jiwer needs standard string input. It does its own basic tokenization (usually just splitting by space)
    # To make it a fair fight, we can feed it our tokenized strings joined by space, 
    # OR let it handle raw text. Let's use raw text to see "Standard Behavior".
    jiwer_out = jiwer.process_words(ref_text, hyp_text)
    
    # Extract Jiwer Alignment for visualization
    # jiwer output alignment is a list of AlignmentChunk objects. We need to flatten it.
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
        .top-text { font-size: 0.85em; color: #666; border-bottom: 1px solid rgba(0,0,0,0.1); margin-bottom: 4px; padding-bottom: 2px; }
        .bot-text { font-size: 1.1em; font-weight: bold; }
        /* Base styles for error types */
        .s-correct { background-color: #d1e7dd; color: #0f5132; }
        .s-sub     { background-color: #f8d7da; color: #842029; }
        .s-ins     { background-color: #cfe2ff; color: #052c65; }
        .s-del     { background-color: #fff3cd; color: #664d03; }
        
        /* Token type distinctions with highly visible borders */
        .t-word   { border: 3px solid #2e7d32; outline: 1px solid #2e7d32; outline-offset: -2px; }
        .t-number { border: 5px double #d32f2f; box-shadow: inset 0 0 0 1px #d32f2f; }
        .t-punct  { border: 3px dashed #9c27b0; background-image: repeating-linear-gradient(45deg, transparent, transparent 5px, rgba(156, 39, 176, 0.1) 5px, rgba(156, 39, 176, 0.1) 10px); }
        .metric-box { padding: 10px; border-radius: 5px; background-color: #f0f2f6; text-align: center; }
        .wer-primary { font-size: 28px; font-weight: bold; color: #1e88e5; }
        .ner-primary { font-size: 28px; font-weight: bold; color: #fb8c00; }
        .per-primary { font-size: 28px; font-weight: bold; color: #43a047; }
        .wer-label, .ner-label, .per-label { font-size: 14px; font-weight: 500; color: #555; text-transform: uppercase; }
        .metrics-row { display: flex; justify-content: space-between; margin-bottom: 15px; }
        .metric-column { flex: 1; text-align: center; padding: 0 10px; }
        .metrics-container { border: 1px solid #eee; border-radius: 10px; padding: 15px; background-color: #fafafa; }
    </style>
    """, unsafe_allow_html=True)

    # --- DISPLAY RESULTS ---
    
    st.header("1. Metric Comparison")
    
    m_col1, m_col2 = st.columns(2)
    
    with m_col1:
        st.subheader("Your DictErrors")
        st.markdown(f"""
        <div class="metrics-container">
            <div class="metrics-row">
                <div class="metric-column">
                    <div class="wer-label">Word Error Rate</div>
                    <div class="wer-primary">{c_wer:.2%}</div>
                </div>
                <div class="metric-column">
                    <div class="ner-label">Number Error Rate</div>
                    <div class="ner-primary">{c_ner:.2%}</div>
                </div>
                <div class="metric-column">
                    <div class="per-label">Punct Error Rate</div>
                    <div class="per-primary">{c_per:.2%}</div>
                </div>
            </div>
        </div>
        <div style="font-size:13px; color:#444; margin-top:8px;">
            Based on {len(custom_ref_tok)} custom tokens
        </div>
        """, unsafe_allow_html=True)

    with m_col2:
        st.subheader("Standard Jiwer")
        st.markdown(f"""
        <div class="metrics-container">
            <div class="metrics-row">
                <div class="metric-column">
                    <div class="wer-label">Word Error Rate</div>
                    <div class="wer-primary">{jiwer_out.wer:.2%}</div>
                </div>
                <div class="metric-column">
                    <div class="ner-label">Match Error Rate</div>
                    <div class="ner-primary">{jiwer_out.mer:.2%}</div>
                </div>
            </div>
        </div>
        <div style="font-size:13px; color:#444; margin-top:8px;">
            Based on standard space-split tokens
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.header("2. Alignment Visualization")

    tab1, tab2 = st.tabs(["✨ Your Custom Alignment", "🐢 Standard Jiwer Alignment"])

    with tab1:
        st.write("#### DictErrors Logic")
        st.write("Notice how punctuation and numbers are handled specifically.")
        st.markdown(generate_alignment_html(c_ref, c_hyp), unsafe_allow_html=True)
        with st.expander("Detailed Report"):
            st.json(c_report)

    with tab2:
        st.write("#### Jiwer Logic")
        st.write("Standard Levenshtein on space-separated tokens.")
        st.markdown(generate_alignment_html(j_ref_viz, j_hyp_viz), unsafe_allow_html=True)
        with st.expander("Jiwer Raw Output"):
            st.text(jiwer.visualize_alignment(jiwer_out))