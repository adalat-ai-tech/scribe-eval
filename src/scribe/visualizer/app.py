try:
    import streamlit as st
except ImportError as exc:
    raise SystemExit(
        "The Streamlit visualizer requires the 'visualizer' extra.\n"
        "Install it with:\n"
        "    pip install 'scribe-eval[visualizer]'"
    ) from exc

import json
import os
import tempfile
from pathlib import Path

import jiwer
import pandas as pd

from scribe import (
    DEFAULT_WEIGHTS,
    DomainConfig,
    aggregate_error_details,
    align_arrays,
    compute_aggregate_metrics,
    compute_category_contributions,
    compute_error_summary,
    compute_sample_errors,
    domain_aware_tokenizer,
    text_error_details,
    token_error_rates,
)
from scribe.reporting import (
    extract_error_rates,
    format_alignment_dict,
    format_contribution_table,
    format_dataset_table,
    format_frequent_errors_table,
)

try:
    from scribe.charts import category_breakdown_chart

    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False


def parse_data(content_list):
    """Handles both JSON (list of dicts) and JSONL (line by line)."""
    full_content = "\n".join(content_list).strip()

    if full_content.startswith("["):
        try:
            return json.loads(full_content)
        except Exception:
            pass

    records = []
    for line in content_list:
        if line.strip():
            try:
                records.append(json.loads(line))
            except Exception as e:
                st.error(f"Failed to parse line: {line[:50]}... Error: {e}")
    return records


def extract_jiwer_aligned_pairs(ref_text, hyp_text):
    """Extract aligned token pairs from jiwer alignment."""
    word_output = jiwer.process_words(ref_text, hyp_text)
    if not word_output.alignments or not word_output.alignments[0]:
        return ([], [])

    ref_words = word_output.references[0]
    hyp_words = word_output.hypotheses[0]
    alignment_chunks = word_output.alignments[0]

    aligned_ref = []
    aligned_hyp = []
    for chunk in alignment_chunks:
        if chunk.type in ("equal", "substitute"):
            aligned_ref.extend(ref_words[chunk.ref_start_idx : chunk.ref_end_idx])
            aligned_hyp.extend(hyp_words[chunk.hyp_start_idx : chunk.hyp_end_idx])
        elif chunk.type == "insert":
            hyp_tokens = hyp_words[chunk.hyp_start_idx : chunk.hyp_end_idx]
            for _ in hyp_tokens:
                aligned_ref.append("**")
            aligned_hyp.extend(hyp_tokens)
        elif chunk.type == "delete":
            ref_tokens = ref_words[chunk.ref_start_idx : chunk.ref_end_idx]
            aligned_ref.extend(ref_tokens)
            for _ in ref_tokens:
                aligned_hyp.append("**")

    return (aligned_ref, aligned_hyp)


def inject_custom_css():
    st.markdown(
        """
    <style>
        .scroll-container { overflow-x: auto; white-space: nowrap; padding-bottom: 15px; width: 100%; border: 1px solid #eee; border-radius: 8px; background: #fafafa; }
        table.alignment-table { border-collapse: separate; border-spacing: 8px; margin: 10px; }
        td.token-cell { border-radius: 6px; padding: 8px 12px; text-align: center; min-width: 80px; font-family: sans-serif; vertical-align: middle; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .top-text { font-size: 1em; font-weight: bold; color: #666; border-bottom: 1px solid rgba(0,0,0,0.1);}
        .bot-text { font-size: 1em; margin-bottom: 4px; padding-bottom: 2px; color: #000; }
        .tag-label { font-size: 0.65em; font-weight: bold; text-transform: uppercase; opacity: 0.5; margin-top: 4px; display: block;}

        .s-correct { background-color: #d1e7dd; color: #0f5132; }
        .s-sub     { background-color: #f8d7da; color: #842029; }
        .s-ins, .s-del { background-color: #ffe0b2; color: #7d4e00; }
        .s-merge   { background-color: #e0e7ff; color: #3730a3; border: 2px solid #6366f1 !important; }

        .t-WORD    { border: 3px solid #a3cfbb; }
        .t-NUMERAL { border: 3px solid #d32f2f; }
        .t-PUNCT   { border: 3px dashed #9c27b0; }
        .t-LEGAL   { border: 4px solid #1a237e; box-shadow: 0 0 8px rgba(26, 35, 126, 0.4); }
        .t-MEDICAL { border: 4px solid #00695c; box-shadow: 0 0 8px rgba(0, 105, 92, 0.4); }
        .t-TECH    { border: 4px solid #4527a0; box-shadow: 0 0 8px rgba(69, 39, 160, 0.4); }

        .jiwer-table td.token-cell { border: 2px solid #bbb; }

        .metrics-container { border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 10px; padding: 15px; background-color: rgba(250, 250, 250, 0.8); color: rgba(0, 0, 0, 0.87); }
        .metric-value { font-size: 24px; font-weight: bold; color: #1e88e5; }
        .metric-legal { color: #1a237e; margin: 10px 0; }
        .jiwer-metric { color: #9c27b0; }
        .metric-secondary { font-size: 20px; color: rgba(0, 0, 0, 0.8); }
    </style>
    """,
        unsafe_allow_html=True,
    )


def generate_alignment_html(aligned_ref, aligned_hyp, normalize=True):
    """Render SCRIBE alignment as HTML."""
    alignment_data = format_alignment_dict(aligned_ref, aligned_hyp, normalize)
    status_map = {
        "correct": "s-correct",
        "substitution": "s-sub",
        "insertion": "s-ins",
        "deletion": "s-del",
        "sandhi": "s-merge",
    }

    html = '<div class="scroll-container"><table class="alignment-table"><tr>'
    for item in alignment_data:
        status = status_map.get(item["error_type"], "s-correct")
        border_class = f"t-{item['token_type']}"
        disp_r = item["ref_text"] if item["ref_text"] != "**" else "&nbsp;"
        disp_h = item["hyp_text"] if item["hyp_text"] != "**" else "&nbsp;"
        html += f"""
        <td class="token-cell {status} {border_class}">
            <div class="top-text">{disp_r}</div>
            <div class="bot-text">{disp_h}</div>
            <div class="tag-label">{item["token_type"]}</div>
        </td>"""
    html += "</tr></table></div>"
    return html


def generate_jiwer_alignment_html(ref_text, hyp_text):
    """Render jiwer alignment as HTML (no category borders)."""
    aligned_ref, aligned_hyp = extract_jiwer_aligned_pairs(ref_text, hyp_text)
    if not aligned_ref:
        return "<p>No alignment data available.</p>"

    html = '<div class="scroll-container"><table class="alignment-table jiwer-table"><tr>'
    for ref_tok, hyp_tok in zip(aligned_ref, aligned_hyp):
        if ref_tok == "**":
            status = "s-ins"
        elif hyp_tok == "**":
            status = "s-del"
        elif ref_tok == hyp_tok:
            status = "s-correct"
        else:
            status = "s-sub"

        disp_r = ref_tok if ref_tok != "**" else "&nbsp;"
        disp_h = hyp_tok if hyp_tok != "**" else "&nbsp;"
        html += f"""
        <td class="token-cell {status}">
            <div class="top-text">{disp_r}</div>
            <div class="bot-text">{disp_h}</div>
        </td>"""
    html += "</tr></table></div>"
    return html


def build_category_chips(contributions, domain_config):
    """Return 'Word Tokens 5.4%' style chips in canonical display order."""
    display_names = {
        "WORD": "Word Tokens",
        "NUMERAL": "Numeral Tokens",
        "PUNCT": "Punctuation Tokens",
    }
    base_cats = {"WORD", "NUMERAL", "PUNCT"}
    domain_cats = [c for c in contributions if c not in base_cats]
    ordered_cats = [c for c in ["WORD"] + domain_cats + ["NUMERAL", "PUNCT"] if c in contributions]
    domain_display = f"{domain_config.name.title()} Tokens" if domain_config else "Domain Tokens"
    return [
        f"{display_names.get(c, domain_display)} {contributions[c]['error_rate']:.2%}"
        for c in ordered_cats
    ]


def render_category_analysis(summary, domain_config):
    """Contributions table + breakdown chart."""
    rows = format_contribution_table(summary["contributions"], domain_config)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    if HAS_CHARTS:
        fig = category_breakdown_chart(summary["contributions"], output_path=None)
        if fig is not None:
            st.pyplot(fig, width="stretch")
    else:
        st.info("Install matplotlib to see the category breakdown chart: `uv add matplotlib`")


def render_frequent_errors(summary, top_n):
    """Five sub-tabs (Subs / Dels / Ins / Sandhi Merges / Sandhi Splits)."""
    sub_tab, del_tab, ins_tab, merge_tab, split_tab = st.tabs(
        ["Substitutions", "Deletions", "Insertions", "Sandhi Merges", "Sandhi Splits"]
    )

    for tab, error_type, freq_key, label in [
        (sub_tab, "substitution", "frequent_substitutions", "substitutions"),
        (del_tab, "deletion", "frequent_deletions", "deletions"),
        (ins_tab, "insertion", "frequent_insertions", "insertions"),
        (merge_tab, "sandhi_merge", "frequent_sandhi_merges", "sandhi merges"),
        (split_tab, "sandhi_split", "frequent_sandhi_splits", "sandhi splits"),
    ]:
        with tab:
            freq_data = summary[freq_key]
            rows = format_frequent_errors_table(freq_data, error_type, top_n)
            if rows:
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            else:
                st.info(f"No {label} found in this batch.")


def render_analysis(ref_text, hyp_text, weights, domain_config, normalize=True, use_sandhi=True):
    """Manual Inspection view: alignment + metrics + single-sample error analysis."""
    t1, g1 = domain_aware_tokenizer(ref_text, domain_config)
    t2, g2 = domain_aware_tokenizer(hyp_text, domain_config)
    a_ref, a_hyp, _ = align_arrays(t1, g1, t2, g2, weights=weights, use_sandhi=use_sandhi)
    report = token_error_rates(a_ref, a_hyp, domain_config, normalize)

    j_wer = jiwer.wer(ref_text, hyp_text)
    j_cer = jiwer.cer(ref_text, hyp_text)
    j_output = jiwer.process_words(ref_text, hyp_text)
    j_subs = j_output.substitutions
    j_ins = j_output.insertions
    j_dels = j_output.deletions

    st.subheader("Alignment Visualizations")
    rates = extract_error_rates(report, domain_config)
    contributions = compute_category_contributions(report)
    ter_frac = sum(c["error_rate"] for c in contributions.values())
    total_correct = sum(c["correct"] for c in contributions.values())
    total_ref = sum(c["ref_tokens"] for c in contributions.values())
    accuracy_frac = (total_correct / total_ref) if total_ref > 0 else 0.0

    category_chips = build_category_chips(contributions, domain_config)

    st.markdown("**SCRIBE Alignment** (Domain-Aware)")
    mc1, mc2, _ = st.columns([1, 1, 2])
    mc1.metric("Token Error Rate", f"{ter_frac:.2%}")
    mc2.metric(
        "Accuracy",
        f"{accuracy_frac:.2%}",
        help=(
            "Accuracy + Token Error Rate need not sum to 100%. "
            "Insertions and Sandhi corrections affects the reference token count."
        ),
    )
    st.caption(" + ".join(category_chips) + f"  =  {ter_frac:.2%}")
    st.caption(f"Sandhis: {rates['sandhi']}")
    st.markdown(generate_alignment_html(a_ref, a_hyp, normalize), unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("**Jiwer Alignment** (Standard Word-Level)")
    jc1, jc2, _ = st.columns([1, 1, 2])
    jc1.metric("Word Error Rate", f"{j_wer:.2%}")
    jc2.metric("Character Error Rate", f"{j_cer:.2%}")
    st.caption(f"{j_subs} subs  ·  {j_ins} ins  ·  {j_dels} del")
    st.markdown(generate_jiwer_alignment_html(ref_text, hyp_text), unsafe_allow_html=True)

    st.markdown("---")
    with st.expander("🔬 Error Analysis (single sample)", expanded=False):
        rows = format_contribution_table(contributions, domain_config)
        st.markdown("**Category breakdown**")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

        if HAS_CHARTS:
            fig = category_breakdown_chart(
                contributions,
                output_path=None,
                title="ASR Error Analysis by Category (single sample)",
            )
            if fig is not None:
                st.pyplot(fig, width="stretch")
        else:
            st.info("Install matplotlib to see the category breakdown chart: `uv add matplotlib`")

        details = text_error_details(ref_text, hyp_text, domain_config, normalize, use_sandhi)
        if details:
            st.markdown("**Individual error records**")
            st.dataframe(pd.DataFrame(details), hide_index=True, width="stretch")
        else:
            st.caption("No errors detected.")


def build_domain_config(choice, uploaded_file):
    """Resolve the sidebar domain-config choice into a DomainConfig instance (or None)."""
    if choice == "Legal":
        return DomainConfig.legal()
    if choice == "Medical":
        return DomainConfig.medical()
    if choice == "Technical":
        return DomainConfig.technical()
    if choice == "From file":
        if uploaded_file is None:
            st.sidebar.warning("Upload a .txt config file to activate the 'From file' domain.")
            return None
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write(uploaded_file.getvalue().decode("utf-8"))
            tmp_path = tmp.name
        try:
            return DomainConfig.from_file(tmp_path)
        except Exception as e:
            st.sidebar.error(f"Failed to load domain config: {e}")
            return None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    return None  # "None" option


def clear_session_keys():
    """Remove all cached analysis keys from session state."""
    for key in (
        "detailed_results",
        "jiwer_stats",
        "ref_col",
        "hyp_col",
        "analysis_summary",
        "all_error_details",
        "agg_metrics",
        "domain_config_snapshot",
    ):
        st.session_state.pop(key, None)


# --- UI CONFIG ---
st.set_page_config(layout="wide", page_title="SCRIBE: ASR Error Analysis")
st.title("🔍 SCRIBE: ASR Error Analysis")
inject_custom_css()

# --- SIDEBAR ---
st.sidebar.header("🏷️ Domain")
with st.sidebar.expander("Domain Configuration", expanded=True):
    domain_choice = st.selectbox(
        "Domain",
        ["Legal", "Medical", "Technical", "From file", "None"],
        index=0,
        help="Protects domain-critical terminology from splitting and tracks its error rate separately.",
    )
    uploaded_domain_file = None
    if domain_choice == "From file":
        uploaded_domain_file = st.file_uploader("Domain config (.txt)", type=["txt"])

domain_config = build_domain_config(domain_choice, uploaded_domain_file)

st.sidebar.divider()
st.sidebar.header("🔧 Penalty Tuning")
weights = {}
with st.sidebar.expander("Category Penalties", expanded=False):
    weights["gap_penalty"] = st.slider(
        "Gap Penalty - General", -5.0, 0.0, DEFAULT_WEIGHTS["gap_penalty"], 0.5
    )
    weights["gap_penalty_punct"] = st.slider(
        "Gap Penalty - Punctuation", -5.0, 0.0, DEFAULT_WEIGHTS["gap_penalty_punct"], 0.1
    )
    weights["mismatch_default_penalty"] = st.slider(
        "Mismatch Penalty - Default", -5.0, 0.0, DEFAULT_WEIGHTS["mismatch_default_penalty"], 0.5
    )
    weights["mismatch_cross_punct_penalty"] = st.slider(
        "Mismatch Penalty - Cross-Category Punct",
        -10.0,
        0.0,
        DEFAULT_WEIGHTS["mismatch_cross_punct_penalty"],
        1.0,
    )
    weights["match_reward"] = st.slider(
        "Match Reward", 1.0, 5.0, DEFAULT_WEIGHTS["match_reward"], 0.5
    )

with st.sidebar.expander("Agglutination & Sandhi", expanded=False):
    weights["split_merge_penalty"] = st.slider(
        "Split/Merge Penalty", -2.0, 0.0, DEFAULT_WEIGHTS["split_merge_penalty"], 0.1
    )
    weights["sandhi_char_tolerance"] = st.slider(
        "Sandhi Char Tolerance", 0, 5, DEFAULT_WEIGHTS["sandhi_char_tolerance"], 1
    )

st.sidebar.divider()
st.sidebar.header("🔄 Token Normalization")
normalize_enabled = st.sidebar.checkbox(
    "Enable Normalization",
    value=True,
    help="Treat date/currency format variations as matches (22.05.2023 = 22/05/2023, 10,500 = 10500).",
)

st.sidebar.header("🔀 Sandhi Detection")
use_sandhi_enabled = st.sidebar.checkbox(
    "Enable Sandhi Detection",
    value=True,
    help="Detect Sandhi splits/merges in agglutinative languages (e.g., 'ഇന്നല്ലെങ്കിൽ' ↔ 'ഇന്ന് അല്ലെങ്കിൽ').",
)

st.sidebar.divider()
st.sidebar.header("📈 Error Analysis")
top_n = st.sidebar.slider(
    "Top N frequent errors",
    5,
    25,
    10,
    help="Number of rows in the frequent Substitutions / Deletions / Insertions tables and charts.",
)

st.sidebar.divider()
st.sidebar.header("🗑️ Session Management")
if st.sidebar.button("Clear Session Data"):
    clear_session_keys()
    st.rerun()

# --- TABS ---
tab_manual, tab_json = st.tabs(["Single Sample Analysis", "Batch Dataset Analysis"])

with tab_manual:
    mc1, mc2 = st.columns(2)
    with mc1:
        m_ref = st.text_area(
            "Reference",
            height=100,
            value="IPC 302 പ്രകാരം ഇന്ന് അല്ലെങ്കിൽ നാളെ ശിക്ഷിക്കപ്പെടും",
        )
    with mc2:
        m_hyp = st.text_area(
            "Hypothesis",
            height=100,
            value="IPS 302 പ്രകാരം ഇന്നല്ലെങ്കിൽ നാളെ ശിക്ഷിക്കപ്പെടും",
        )
    if m_ref.strip() and m_hyp.strip():
        render_analysis(m_ref, m_hyp, weights, domain_config, normalize_enabled, use_sandhi_enabled)
    else:
        st.caption("Enter both a reference and hypothesis to see the analysis.")

with tab_json:
    col_config, col_batch = st.columns([1, 1], gap="large")
    records = []
    ref_col = hyp_col = src_col = None

    base_dir = Path(__file__).parent
    # Repo-checkout layout: src/scribe/visualizer/app.py → ../../../examples/.
    # Falls back gracefully (warning shown below) when running from an
    # installed wheel where examples/ is not packaged.
    default_path = Path(__file__).resolve().parents[3] / "examples" / "predictions.jsonl"

    with col_config:
        st.markdown("### 📂 Load Data")
        upload_opt = st.radio("Source", ["Default Path", "Upload File"], horizontal=True)
        data_content = None

        if upload_opt == "Upload File":
            uploaded = st.file_uploader("Upload File", type=["json", "jsonl"])
            if uploaded:
                data_content = uploaded.getvalue().decode("utf-8").splitlines()
        else:
            if default_path.exists():
                with open(default_path, "r", encoding="utf-8") as f:
                    data_content = f.readlines()
            else:
                st.warning(f"Default file not found at: `{default_path}`")

        if data_content:
            records = parse_data(data_content)
            if records:
                st.success(f"Successfully loaded {len(records)} records")
                try:
                    keys = list(records[0].keys())
                    def_ref = (
                        keys.index("transcript_cleaned") if "transcript_cleaned" in keys else 0
                    )
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
                with tempfile.NamedTemporaryFile(
                    mode="w+", suffix=".jsonl", delete=False, encoding="utf-8"
                ) as tmp:
                    for r in records:
                        tmp.write(json.dumps(r, ensure_ascii=False) + "\n")
                    tmp_path = tmp.name

                try:
                    res_detailed = compute_sample_errors(
                        tmp_path,
                        ref_field=ref_col,
                        hyp_field=hyp_col,
                        domain_config=domain_config,
                        normalize=normalize_enabled,
                        use_sandhi=use_sandhi_enabled,
                        collect_error_details=True,
                    )

                    for i, r in enumerate(res_detailed):
                        r["source_dataset"] = (
                            records[i].get(src_col, "unknown")
                            if src_col and src_col != "(None)"
                            else "overall"
                        )

                    agg = compute_aggregate_metrics(res_detailed, domain_config=domain_config)
                    all_error_details = aggregate_error_details(res_detailed)

                    all_refs = [r.get(ref_col, "") for r in records]
                    all_hyps = [r.get(hyp_col, "") for r in records]
                    j_output = jiwer.process_words(all_refs, all_hyps)
                    jiwer_stats = {
                        "wer": jiwer.wer(all_refs, all_hyps),
                        "cer": jiwer.cer(all_refs, all_hyps),
                        "subs": j_output.substitutions,
                        "ins": j_output.insertions,
                        "dels": j_output.deletions,
                    }

                    MAX_STORED_RESULTS = 100
                    st.session_state["detailed_results"] = res_detailed[-MAX_STORED_RESULTS:]
                    st.session_state["jiwer_stats"] = jiwer_stats
                    st.session_state["ref_col"] = ref_col
                    st.session_state["hyp_col"] = hyp_col
                    st.session_state["all_error_details"] = all_error_details
                    st.session_state["agg_metrics"] = agg
                    st.session_state["domain_config_snapshot"] = (
                        domain_config.name if domain_config else None
                    )
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

    # --- Render results (from session state) ---
    if "agg_metrics" in st.session_state and "all_error_details" in st.session_state:
        agg = st.session_state["agg_metrics"]
        all_error_details = st.session_state["all_error_details"]
        jiwer_stats = st.session_state.get(
            "jiwer_stats", {"wer": 0.0, "cer": 0.0, "subs": 0, "ins": 0, "dels": 0}
        )

        # Recompute summary with current top_n slider (no batch rerun needed)
        summary = compute_error_summary(agg["overall"], all_error_details, top_n=top_n)
        total_ref = sum(c["ref_tokens"] for c in summary["contributions"].values())

        # Warn if the domain config changed since last batch
        prev_snapshot = st.session_state.get("domain_config_snapshot")
        curr_snapshot = domain_config.name if domain_config else None
        if prev_snapshot != curr_snapshot:
            st.warning(
                f"Sidebar domain (`{curr_snapshot}`) differs from the batch run "
                f"(`{prev_snapshot}`). Re-run the batch evaluation to refresh results."
            )

        st.divider()
        st.markdown("## 📈 Overall Metrics")
        overall_rates = extract_error_rates(agg["overall"], domain_config)
        overall_chips = build_category_chips(summary["contributions"], domain_config)
        overall_ter = summary["total_error_rate"]

        st.markdown("**SCRIBE** (Domain-Aware)")
        mc1, mc2, _ = st.columns([1, 1, 2])
        mc1.metric("Token Error Rate", f"{overall_ter:.2%}")
        mc2.metric(
            "Accuracy",
            f"{summary['total_correct_pct'] / 100:.2%}",
            help=(
                "Accuracy + Token Error Rate need not sum to 100%. "
                "Insertions add to the error rate without affecting the reference-token denominator, "
                "and Sandhi corrections are tracked separately."
            ),
        )
        st.caption(" + ".join(overall_chips) + f"  =  {overall_ter:.2%}")
        st.caption(f"Sandhis: {overall_rates['sandhi']}  ·  Total Ref Tokens: {total_ref:,}")

        st.markdown("---")

        st.markdown("**Jiwer** (Standard Word-Level)")
        jc1, jc2, _ = st.columns([1, 1, 2])
        jc1.metric("Word Error Rate", f"{jiwer_stats['wer']:.2%}")
        jc2.metric("Character Error Rate", f"{jiwer_stats['cer']:.2%}")
        st.caption(
            f"{jiwer_stats['subs']} subs  ·  {jiwer_stats['ins']} ins  ·  {jiwer_stats['dels']} del"
        )

        st.divider()
        st.markdown("## 📊 Per-Dataset Breakdown")
        table_data = format_dataset_table(agg, domain_config)
        table_data = [row for row in table_data if row["Dataset"] != "OVERALL"]
        if table_data:
            st.dataframe(pd.DataFrame(table_data), hide_index=True, width="stretch")
        else:
            st.caption("No per-dataset split available (all samples in a single batch).")

        st.divider()
        st.markdown("## 🧩 Category Analysis")
        render_category_analysis(summary, domain_config)

        st.divider()
        st.markdown("## 🔎 Frequent Errors")
        st.caption(f"Showing top {top_n} (adjust via sidebar).")
        render_frequent_errors(summary, top_n)

    if "detailed_results" in st.session_state:
        st.divider()
        st.markdown("## 🔍 Individual Record Inspection")
        res_list = st.session_state["detailed_results"]
        saved_ref_col = st.session_state.get("ref_col", "reference")
        saved_hyp_col = st.session_state.get("hyp_col", "hypothesis")

        idx = st.selectbox(
            "Select record",
            range(len(res_list)),
            format_func=lambda i: f"Record {i + 1}: {res_list[i][saved_ref_col][:60]}...",
        )

        sel = res_list[idx]
        render_analysis(
            sel[saved_ref_col],
            sel[saved_hyp_col],
            weights,
            domain_config,
            normalize_enabled,
            use_sandhi_enabled,
        )
