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
    from matplotlib.patches import Rectangle

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def _check_matplotlib():
    if not HAS_MATPLOTLIB:
        raise ImportError(
            "matplotlib is required for chart generation. Install it with: uv add matplotlib"
        )


# Editorial palette — matches the visualizer design system
# (.streamlit theme + inject_custom_css tokens).
PAPER = "#FAF7F2"
INK = "#1C1B1A"
INK_MUTED = "#6B675F"
HAIRLINE = "#DDD6C9"
ACCENT = "#3A3D8F"

# Segment colors (consistent across all charts)
COLOR_CORRECT = "#4A7C59"  # muted green
COLOR_SUBSTITUTION = "#A6453C"  # muted brick
COLOR_DELETION = "#B07D2E"  # muted ochre
COLOR_INSERTION = "#56679A"  # muted slate indigo

SERIF = "serif"
SANS = "sans-serif"


def category_breakdown_chart(
    contributions: dict[str, dict],
    output_path: Optional[str] = None,
    title: str = "ASR Error Analysis by Category",
) -> Optional[object]:
    """
    Generate a typographic report-card figure of the category breakdown.

    One row per category (plus TOTAL): a 100%-normalized outcome bar
    (exact match / substitutions / deletions / insertions — readable
    regardless of how few tokens the category has), a large accuracy
    figure, a token/error stat line, and the category's contribution to
    WER_SCRIBE as a dot-and-stem mark. Left-aligned title block with an
    accent tick, inline color key, and a footnote replace axes, grids
    and legends.

    Args:
        contributions: From compute_category_contributions(). Each entry has
            correct, substitutions, deletions, insertions, ref_tokens.
        output_path: If provided, save as PNG/PDF. If None, return figure.
        title: Overall figure title

    Returns:
        matplotlib Figure object, or None if saved to file.
    """
    _check_matplotlib()

    # Display names for categories
    category_display = {
        "LEXICAL": "Lexical",
        "PUNCT": "Punctuation",
        "NUMERAL": "Numeral",
    }

    # Fixed display order: Lexical, Domain, Numeral, Punctuation.
    # A single domain category displays as "Domain"; with several
    # (mixed aggregates), each keeps its category name.
    base_cats = {"LEXICAL", "NUMERAL", "PUNCT"}
    domain_cats = [c for c in contributions if c not in base_cats]
    if len(domain_cats) > 1:
        for c in domain_cats:
            category_display[c] = c
    ordered_cats = ["LEXICAL"] + domain_cats + ["NUMERAL", "PUNCT"]
    ordered_cats = [c for c in ordered_cats if c in contributions]

    rows = []  # (name, correct, sub, del, ins)
    totals = [0, 0, 0, 0]
    total_ref = 0
    for cat in ordered_cats:
        d = contributions[cat]
        rows.append(
            (
                category_display.get(cat, "Domain"),
                d["correct"],
                d["substitutions"],
                d["deletions"],
                d["insertions"],
            )
        )
        for k, key in enumerate(("correct", "substitutions", "deletions", "insertions")):
            totals[k] += d[key]
        total_ref += d["ref_tokens"]
    total_row = ("All tokens", *totals)
    wer_scribe_pct = (totals[1] + totals[2] + totals[3]) / total_ref * 100 if total_ref > 0 else 0.0

    def contribution_pct(row):
        return ((row[2] + row[3] + row[4]) / total_ref * 100) if total_ref > 0 else 0.0

    max_contrib = max([contribution_pct(r) for r in rows] + [wer_scribe_pct, 0.1])

    # ---- Canvas: one axes in 0..1 coordinates, everything hand-placed ----
    n_rows = len(rows) + 1  # + TOTAL
    row_h = 1.05
    header_h = 2.75
    footer_h = 0.7
    fig_h = header_h + n_rows * row_h + footer_h
    fig = plt.figure(figsize=(13, fig_h), dpi=110)
    fig.set_facecolor(PAPER)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    # Column geometry (x, in axes fraction)
    X_NAME = 0.045
    X_BAR0, X_BAR1 = 0.21, 0.60
    X_ACC = 0.665
    X_DOT0, X_DOT1 = 0.735, 0.92
    X_RIGHT = 0.955

    def txt(x, y, s, size, color=INK, weight="normal", family=SANS, ha="left", va="center"):
        ax.text(x, y, s, fontsize=size, color=color, fontweight=weight, family=family, ha=ha, va=va)

    # ---- Header block ----
    y = fig_h - 0.42
    ax.add_patch(Rectangle((X_NAME, y + 0.13), 0.045, 0.075, color=ACCENT))
    txt(X_NAME, y - 0.28, title, 21, weight="bold", family=SERIF)
    txt(
        X_NAME,
        y - 0.80,
        f"{total_ref:,} reference tokens   ·   WER_SCRIBE {wer_scribe_pct:.1f}%",
        12.5,
        color=INK_MUTED,
    )

    # Inline color key
    key_y = y - 1.28
    key_x = X_NAME
    for label, color in (
        ("Match", COLOR_CORRECT),
        ("Substitutions", COLOR_SUBSTITUTION),
        ("Deletions", COLOR_DELETION),
        ("Insertions", COLOR_INSERTION),
    ):
        ax.add_patch(Rectangle((key_x, key_y - 0.045), 0.011, 0.10, color=color))
        txt(key_x + 0.017, key_y, label, 10.5, color=INK)
        key_x += 0.017 + 0.012 * len(label) + 0.025

    # Column captions
    cap_y = key_y - 0.62
    txt(X_BAR0, cap_y, "OUTCOME SHARE WITHIN CATEGORY", 8.5, color=INK_MUTED)
    txt(X_ACC, cap_y, "ACCURACY", 8.5, color=INK_MUTED)
    txt(X_DOT0, cap_y, "CONTRIBUTION TO WER_SCRIBE", 8.5, color=INK_MUTED)
    ax.plot([X_NAME, X_RIGHT], [cap_y - 0.18, cap_y - 0.18], color=INK, linewidth=1.4)

    # ---- Category rows ----
    def draw_row(y_mid, row, emphasize=False):
        name, cor, sub, dl, ins = row
        touched = cor + sub + dl + ins
        ref = cor + sub + dl
        acc = (cor / ref * 100) if ref > 0 else None

        name_size = 13.5 if emphasize else 12.5
        txt(X_NAME, y_mid + 0.10, name, name_size, weight="bold" if emphasize else "600")
        txt(
            X_NAME,
            y_mid - 0.24,
            f"{ref:,} ref tokens" if ref else "no ref tokens",
            9.5,
            color=INK_MUTED,
        )

        # Normalized outcome bar (share of touched tokens)
        bar_h = 0.30
        if touched > 0:
            x = X_BAR0
            for count, color in (
                (cor, COLOR_CORRECT),
                (sub, COLOR_SUBSTITUTION),
                (dl, COLOR_DELETION),
                (ins, COLOR_INSERTION),
            ):
                w = (count / touched) * (X_BAR1 - X_BAR0)
                if w > 0:
                    ax.add_patch(
                        Rectangle((x, y_mid - bar_h / 2), w, bar_h, color=color, linewidth=0)
                    )
                    x += w
            txt(
                X_BAR0,
                y_mid - bar_h / 2 - 0.17,
                f"{cor:,} match · {sub} sub · {dl} del · {ins} ins",
                8.5,
                color=INK_MUTED,
                va="top",
            )
        else:
            ax.plot(
                [X_BAR0, X_BAR1],
                [y_mid, y_mid],
                color=HAIRLINE,
                linewidth=1.2,
                linestyle=(0, (2, 3)),
            )
            txt(X_BAR0, y_mid - 0.32, "nothing to measure", 8.5, color=INK_MUTED, va="top")

        # Accuracy figure — the row's headline number, full ink
        txt(X_ACC, y_mid, f"{acc:.0f}%" if acc is not None else "—", 15, weight="bold")

        # Contribution dot-and-stem
        contrib = contribution_pct(row)
        frac = contrib / max_contrib if max_contrib > 0 else 0
        x_end = X_DOT0 + frac * (X_DOT1 - X_DOT0)
        ax.plot([X_DOT0, X_DOT1], [y_mid, y_mid], color=HAIRLINE, linewidth=1.0)
        ax.plot([X_DOT0, x_end], [y_mid, y_mid], color=ACCENT, linewidth=2.2)
        ax.plot([x_end], [y_mid], marker="o", markersize=7, color=ACCENT)
        txt(x_end + 0.012, y_mid, f"{contrib:.1f}%", 11.5, weight="600")

    y_cursor = fig_h - header_h - row_h / 2
    for row in rows:
        draw_row(y_cursor, row)
        y_cursor -= row_h

    # TOTAL row under a heavier rule
    ax.plot(
        [X_NAME, X_RIGHT],
        [y_cursor + row_h / 2 - 0.02, y_cursor + row_h / 2 - 0.02],
        color=INK,
        linewidth=1.0,
    )
    draw_row(y_cursor, total_row, emphasize=True)

    # ---- Footer ----
    foot_y = y_cursor - row_h / 2 - 0.18
    ax.plot([X_NAME, X_RIGHT], [foot_y + 0.14, foot_y + 0.14], color=HAIRLINE, linewidth=1.0)
    txt(
        X_NAME,
        foot_y - 0.08,
        "Bars are normalized within each category; error rates use the combined "
        "denominator (all reference tokens). Generated by scribe-eval.",
        8.5,
        color=INK_MUTED,
        va="top",
    )

    if output_path:
        fig.savefig(output_path, bbox_inches="tight", dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        return None
    return fig
