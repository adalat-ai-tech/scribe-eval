import streamlit as st
import sys
import os
import Levenshtein as levenshtein

# --- SETUP PATHS ---
# Ensure we can import from src directory relative to this file
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from dicterrors.tokenize import tokenizer
    from dicterrors.measure import token_error_rates
    from dicterrors.align import is_punctuation, is_number, is_word, words_match
except ImportError as e:
    st.error(f"Error importing modules: {e}. Make sure you are running this from the project root.")
    st.stop()

# --- DYNAMIC ALIGNMENT LOGIC ---
# These functions mirror your 'align.py' but accept a 'weights' dictionary 
# so you can control them via sliders.

def get_dynamic_gap_penalty(token, weights):
    if token == '**': return 0
    # Penalty for inserting/deleting punctuation or numbers
    if is_punctuation(token) or is_number(token):
        return weights['gap_punct_num']
    else: 
        # Penalty for inserting/deleting words (base + length factor)
        return weights['gap_word_base'] - (levenshtein.distance(token, '') * weights['gap_word_factor'])

def get_dynamic_mismatch_penalty(w1, w2, weights):
    # Cross-type penalties (e.g. Word vs Punctuation)
    if (is_punctuation(w1) and (is_word(w2) or is_number(w2))) or \
       ((is_word(w1) or is_number(w1)) and is_punctuation(w2)):
        return weights['mismatch_punct_cross']
    
    # Word vs Number
    elif (is_word(w1) and is_number(w2)) or (is_number(w1) and is_word(w2)):
        return weights['mismatch_word_num']
    
    # Number vs Number
    elif is_number(w1) and is_number(w2):
        return weights['mismatch_num_num']
    
    # Punctuation vs Punctuation
    elif is_punctuation(w1) and is_punctuation(w2):
        return weights['mismatch_punct_punct']
    
    # Word vs Word (Base penalty + Levenshtein distance)
    else:  
        return weights['mismatch_word_base'] - levenshtein.distance(w1, w2)

def get_dynamic_match_score(w1, w2, weights):
    # Reward for a match (Base + length bonus)
    return weights['match_base'] + (levenshtein.distance(w1, w2)/(len(w1)+len(w2)))

def run_dynamic_alignment(arr1, arr2, weights):
    m, n = len(arr1), len(arr2)
    dp = [[0 for _ in range(n + 1)] for _ in range(m + 1)]

    # Initialize DP Table (First row and column are gap penalties)
    for i in range(1, m + 1):
        dp[i][0] = dp[i-1][0] + get_dynamic_gap_penalty(arr1[i-1], weights)
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j-1] + get_dynamic_gap_penalty(arr2[j-1], weights)

    # Fill DP Table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            # Check for Match
            # Note: Currently using exact match or your 'words_match' logic
            if words_match(arr1[i-1], arr2[j-1], 0): 
                score = get_dynamic_match_score(arr1[i-1], arr2[j-1], weights)
                match_val = dp[i-1][j-1] + score
            else:
                score = get_dynamic_mismatch_penalty(arr1[i-1], arr2[j-1], weights)
                match_val = dp[i-1][j-1] + score

            # Calculate Deletion (Gap in Hyp) and Insertion (Gap in Ref)
            delete_val = dp[i-1][j] + get_dynamic_gap_penalty(arr1[i-1], weights)
            insert_val = dp[i][j-1] + get_dynamic_gap_penalty(arr2[j-1], weights)

            dp[i][j] = max(match_val, delete_val, insert_val)

    # Traceback to build alignment strings
    aligned_arr1, aligned_arr2 = [], []
    i, j = m, n

    while i > 0 or j > 0:
        if i > 0 and j > 0:
            current = dp[i][j]
            diag = dp[i-1][j-1]
            
            # Re-calculate match score to see if we came from diagonal
            if words_match(arr1[i-1], arr2[j-1], 0):
                step_score = get_dynamic_match_score(arr1[i-1], arr2[j-1], weights)
            else:
                step_score = get_dynamic_mismatch_penalty(arr1[i-1], arr2[j-1], weights)
            
            # Check path (using small float tolerance)
            if abs(current - (diag + step_score)) < 1e-9:
                aligned_arr1.append(arr1[i-1])
                aligned_arr2.append(arr2[j-1])
                i -= 1; j -= 1
            elif i > 0 and abs(current - (dp[i-1][j] + get_dynamic_gap_penalty(arr1[i-1], weights))) < 1e-9:
                aligned_arr1.append(arr1[i-1])
                aligned_arr2.append('**')
                i -= 1
            else:
                aligned_arr1.append('**')
                aligned_arr2.append(arr2[j-1])
                j -= 1
        elif i > 0:
            aligned_arr1.append(arr1[i-1])
            aligned_arr2.append('**')
            i -= 1
        else:
            aligned_arr1.append('**')
            aligned_arr2.append(arr2[j-1])
            j -= 1

    return aligned_arr1[::-1], aligned_arr2[::-1], dp[m][n]

# --- UI CONFIG ---
st.set_page_config(layout="wide", page_title="DictErrors Alignment Lab")

st.title("🧬 DictErrors: Alignment Laboratory")
st.markdown("Test and tune alignment heuristics for Indic Dictation.")

# --- SIDEBAR: CONTROLS ---
st.sidebar.header("⚖️ Penalty Tuning")
st.sidebar.info("Adjust these weights to fix alignment errors.")

weights = {}
# Default values match your python logic roughly
with st.sidebar.expander("Gap Penalties (Ins/Del)", expanded=True):
    weights['gap_punct_num'] = st.sidebar.slider("Gap: Punct/Num", -5.0, 0.0, -1.0, 0.5)
    weights['gap_word_base'] = st.sidebar.slider("Gap: Word Base", -5.0, 0.0, -1.0, 0.5)
    weights['gap_word_factor'] = st.sidebar.slider("Gap: Word Length Factor", 0.0, 2.0, 0.5, 0.1)

with st.sidebar.expander("Mismatch Penalties (Substitution)", expanded=True):
    weights['mismatch_punct_cross'] = st.sidebar.slider("Sub: Punct ↔ Word/Num", -10.0, -1.0, -6.0, 0.5)
    weights['mismatch_word_num'] = st.sidebar.slider("Sub: Word ↔ Num", -10.0, -1.0, -5.0, 0.5)
    weights['mismatch_num_num'] = st.sidebar.slider("Sub: Num ↔ Num", -5.0, 0.0, -2.0, 0.5)
    weights['mismatch_punct_punct'] = st.sidebar.slider("Sub: Punct ↔ Punct", -5.0, 0.0, -1.0, 0.5)
    weights['mismatch_word_base'] = st.sidebar.slider("Sub: Word Base", -5.0, 0.0, -1.0, 0.5)

with st.sidebar.expander("Match Rewards", expanded=False):
    weights['match_base'] = st.sidebar.slider("Match Base Reward", 1.0, 5.0, 3.0, 0.5)

# --- MAIN AREA ---
col1, col2 = st.columns(2)
with col1:
    ref_text = st.text_area("Reference (Ground Truth)", height=150,
        value="ഇന്ന് 9ാം തീയതിയാണ്, സമയം 9:60 വന്നു ഞാ പോയി")
with col2:
    hyp_text = st.text_area("Hypothesis (Prediction)", height=150,
        value="ഇന്ന് 9 ആം തീയതിയാണ് സമയം, 9 30 ഞാൻ ഞാങ്ങോട്ട് പോയി")

if st.button("Run Alignment", type="primary"):
    # 1. Tokenize
    ref_tokens = tokenizer(ref_text)
    hyp_tokens = tokenizer(hyp_text)
    
    # 2. Align (Using Dynamic Logic defined above)
    a_ref, a_hyp, score = run_dynamic_alignment(ref_tokens, hyp_tokens, weights)
    
    # 3. Measure Errors (Using your existing logic)
    wer, per, ner, report = token_error_rates(a_ref, a_hyp)

    # --- VISUALIZATION ---
    st.divider()
    
    # Metrics Header
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Alignment Score", f"{score:.2f}")
    m2.metric("WER (Word)", f"{wer:.2%}")
    m3.metric("PER (Punct)", f"{per:.2%}")
    m4.metric("NER (Numeral)", f"{ner:.2%}")

    st.subheader("Visual Alignment")

    # 1. CSS (Styling)
    st.markdown("""
    <style>
        .scroll-container {
            overflow-x: auto;
            white-space: nowrap;
            padding-bottom: 15px;
            width: 100%;
            border: 1px solid #eee;
            border-radius: 8px;
            background: #fafafa;
        }
        table.alignment-table {
            border-collapse: separate;
            border-spacing: 6px;
            margin: 10px;
        }
        td.token-cell {
            border-radius: 6px;
            padding: 8px 12px;
            text-align: center;
            min-width: 60px;
            border: 1px solid #ddd;
            font-family: sans-serif;
            vertical-align: middle;
        }
        .top-text {
            font-size: 0.85em;
            color: #666;
            border-bottom: 1px solid rgba(0,0,0,0.1);
            margin-bottom: 4px;
            padding-bottom: 2px;
        }
        .bot-text {
            font-size: 1.1em;
            font-weight: bold;
        }
        /* Status Colors */
        .s-correct { background-color: #d1e7dd; border-color: #a3cfbb; color: #0f5132; }
        .s-sub     { background-color: #f8d7da; border-color: #f1aeb5; color: #842029; }
        .s-ins     { background-color: #cfe2ff; border-color: #9ec5fe; color: #052c65; }
        .s-del     { background-color: #fff3cd; border-color: #ffe69c; color: #664d03; }
    </style>
    """, unsafe_allow_html=True)

    # 2. HTML GENERATION (Using Table)
    # Build a clean HTML string without unwanted whitespace
    
    table_html = '<div class="scroll-container"><table class="alignment-table"><tr>'
    
    for r, h in zip(a_ref, a_hyp):
        # Determine Status
        status = "s-correct"
        if r == "**": status = "s-ins"
        elif h == "**": status = "s-del"
        elif r != h: status = "s-sub"
        
        # Display Text (Handle Gaps)
        disp_r = r if r != "**" else "&nbsp;"
        disp_h = h if h != "**" else "&nbsp;"
        
        # Add Cell - without extra newlines and indentation that break rendering
        table_html += f"<td class=\"token-cell {status}\"><div class=\"top-text\">{disp_r}</div><div class=\"bot-text\">{disp_h}</div></td>"
    
    table_html += "</tr></table></div>"
    
    # 3. RENDER
    st.markdown(table_html, unsafe_allow_html=True)

    # Detailed Stats
    st.divider()
    with st.expander("See Detailed Error Report"):
        st.json(report)