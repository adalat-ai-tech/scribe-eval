"""
Chart generation for ASR error analysis.

Uses matplotlib for static chart generation (CLI reports, file output).
For Streamlit, callers can use st.pyplot(fig) with the returned figures.
"""

from typing import Optional

try:
    import matplotlib

    matplotlib.use("Agg")  # Non-interactive backend for CLI/file output
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def _check_matplotlib():
    if not HAS_MATPLOTLIB:
        raise ImportError(
            "matplotlib is required for chart generation. Install it with: uv add matplotlib"
        )


# Segment colors (consistent across all charts)
COLOR_CORRECT = "#4CAF50"  # Green
COLOR_SUBSTITUTION = "#E53935"  # Red
COLOR_DELETION = "#FFC107"  # Amber/Yellow
COLOR_INSERTION = "#1E88E5"  # Blue


def category_breakdown_chart(
    contributions: dict[str, dict],
    output_path: Optional[str] = None,
    title: str = "ASR Error Analysis by Category",
) -> Optional[object]:
    """
    Generate a multi-panel figure with category breakdown and error rates.

    Three panels:
      Left (wide):   Stacked bar — correct/sub/del/ins counts per category + TOTAL
      Right-top:     Cat ER% — (S+I+D) / category_ref_tokens per category
      Right-bottom:  ER% of Total — (S+I+D) / total_ref_tokens per category

    Args:
        contributions: From compute_category_contributions(). Each entry has
            correct, substitutions, deletions, insertions, ref_tokens.
        output_path: If provided, save as PNG/PDF. If None, return figure.
        title: Overall figure title

    Returns:
        matplotlib Figure object, or None if saved to file.
    """
    _check_matplotlib()
    from matplotlib.gridspec import GridSpec

    # Display names for categories
    category_display = {
        "WORD": "Word Tokens",
        "PUNCT": "Punctuation Tokens",
        "NUMERAL": "Numeral Tokens",
    }

    # Fixed display order: Word, Domain, Numeral, Punctuation
    # Domain categories are anything not in the base set
    base_cats = {"WORD", "NUMERAL", "PUNCT"}
    domain_cats = [c for c in contributions if c not in base_cats]

    ordered_cats = ["WORD"] + domain_cats + ["NUMERAL", "PUNCT"]
    # Only include categories that exist in contributions
    ordered_cats = [c for c in ordered_cats if c in contributions]

    total_correct = 0
    total_subs = 0
    total_dels = 0
    total_ins = 0
    total_ref = 0

    cat_rows = []  # per-category rows (without TOTAL)
    for cat in ordered_cats:
        d = contributions[cat]
        display_name = category_display.get(cat, "Domain Tokens")
        cat_rows.append(
            (display_name, d["correct"], d["substitutions"], d["deletions"], d["insertions"])
        )
        total_correct += d["correct"]
        total_subs += d["substitutions"]
        total_dels += d["deletions"]
        total_ins += d["insertions"]
        total_ref += d["ref_tokens"]

    # Left panel: TOTAL at bottom → reversed y-axis means TOTAL first in list
    # then categories in reverse so Word ends up at top
    rows = [("TOTAL", total_correct, total_subs, total_dels, total_ins)] + cat_rows[::-1]

    labels = [r[0] for r in rows]
    correct = [r[1] for r in rows]
    subs = [r[2] for r in rows]
    dels = [r[3] for r in rows]
    ins = [r[4] for r in rows]
    n = len(labels)
    y_pos = range(n)

    # --- Figure layout: left panel (wide) + right panel (contribution) ---
    fig_h = max(4, n * 1.0)
    fig = plt.figure(figsize=(18, fig_h))
    gs = GridSpec(1, 2, width_ratios=[3, 1], wspace=0.35)

    ax1 = fig.add_subplot(gs[0, 0])  # Left: stacked bar
    ax3 = fig.add_subplot(gs[0, 1])  # Right: contribution

    # ========== Panel 1: Stacked bar chart (left) ==========
    ax1.barh(y_pos, correct, label="Exact Match", color=COLOR_CORRECT)
    ax1.barh(y_pos, subs, left=correct, label="Substitutions", color=COLOR_SUBSTITUTION)
    ax1.barh(
        y_pos,
        dels,
        left=[c + s for c, s in zip(correct, subs)],
        label="Deletions",
        color=COLOR_DELETION,
    )
    ax1.barh(
        y_pos,
        ins,
        left=[c + s + d for c, s, d in zip(correct, subs, dels)],
        label="Insertions",
        color=COLOR_INSERTION,
    )

    # Reference count markers
    for i, row in enumerate(rows):
        ref_count = row[1] + row[2] + row[3]
        if row[4] > 0:
            ax1.plot(ref_count, i, marker="|", color="black", markersize=15, markeredgewidth=1.5)

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(labels, fontsize=11)
    ax1.set_xlabel("Token Count", fontsize=11)
    ax1.set_title("Token Matches and Errors", fontsize=13, fontweight="bold")
    ax1.legend(loc="center right", fontsize=9)

    # Percentage annotations
    max_total = max(r[1] + r[2] + r[3] + r[4] for r in rows) if rows else 1
    for i, row in enumerate(rows):
        _, cor, sub, dl, ins_count = row
        ref = cor + sub + dl
        total = ref + ins_count
        if ref > 0:
            pct = cor / ref * 100
            if cor > max_total * 0.08:
                ax1.text(
                    cor / 2,
                    i,
                    f"{pct:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=9,
                    fontweight="bold",
                    color="white",
                )
            else:
                ax1.text(
                    total + max_total * 0.02,
                    i,
                    f"{pct:.0f}% accuracy",
                    ha="left",
                    va="center",
                    fontsize=8,
                    color="#333",
                )
        ax1.text(
            total + max_total * 0.005,
            i + 0.25,
            str(total),
            ha="left",
            va="center",
            fontsize=8,
            color="#999",
        )

    # Separator between TOTAL (index 0) and category rows
    ax1.axhline(y=0.5, color="gray", linewidth=0.8, linestyle="--")

    # ========== Panel 2: Category Contribution (right) ==========
    # Right panel rows: TOTAL at bottom (index 0), then categories reversed
    right_cat_rows = cat_rows[::-1]
    total_row = ("TOTAL", total_correct, total_subs, total_dels, total_ins)
    right_rows = [total_row] + right_cat_rows
    right_labels = [r[0] for r in right_rows]
    right_y = range(len(right_labels))

    # (S+I+D) / total_ref_tokens
    er_of_total = []
    for r in right_rows:
        errors = r[2] + r[3] + r[4]
        er_of_total.append((errors / total_ref * 100) if total_ref > 0 else 0)

    # Stacked sub/del/ins with matching colors
    tot_sub_pct = []
    tot_del_pct = []
    tot_ins_pct = []
    for r in right_rows:
        tot_sub_pct.append((r[2] / total_ref * 100) if total_ref > 0 else 0)
        tot_del_pct.append((r[3] / total_ref * 100) if total_ref > 0 else 0)
        tot_ins_pct.append((r[4] / total_ref * 100) if total_ref > 0 else 0)

    ax3.barh(right_y, tot_sub_pct, color=COLOR_SUBSTITUTION)
    ax3.barh(right_y, tot_del_pct, left=tot_sub_pct, color=COLOR_DELETION)
    ax3.barh(
        right_y,
        tot_ins_pct,
        left=[s + d for s, d in zip(tot_sub_pct, tot_del_pct)],
        color=COLOR_INSERTION,
    )
    ax3.set_yticks(right_y)
    ax3.set_yticklabels(right_labels, fontsize=10)
    ax3.set_xlabel("%", fontsize=10)
    total_er_pct = er_of_total[0]  # TOTAL row is index 0
    ax3.set_title(
        f"Category Contribution to {total_er_pct:.1f}% Token Error Rate",
        fontsize=11,
        fontweight="bold",
    )
    ax3.set_xlim(0, max(er_of_total + [10]) * 1.2)

    for i, val in enumerate(er_of_total):
        ax3.text(val + 0.3, i, f"{val:.1f}%", va="center", fontsize=9)

    # Separator between TOTAL and category rows
    ax3.axhline(y=0.5, color="gray", linewidth=0.8, linestyle="--")

    fig.suptitle(title, fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, bbox_inches="tight", dpi=150)
        plt.close(fig)
        return None
    return fig
