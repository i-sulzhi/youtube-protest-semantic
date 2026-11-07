"""Figure 5 — cross-model / cross-prompt disagreement (Benchmark Illusion).

Two panels:
  (left)  pairwise disagreement bars: cross-MODEL (Claude vs GPT) vs
          cross-PROMPT (within model), + four-way unanimity.
  (right) label distribution per config — the systematic model bias
          (GPT leans antywojenny, Claude leans neutral/prokremlin).

Data: mini_study/all_predictions.csv (240 predictions, 4 configs × 60 items).

Output: figures/fig5_disagreement.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
LONG = REPO / "mini_study" / "all_predictions.csv"
WIDE = REPO / "mini_study" / "all_predictions_wide.csv"
OUT = REPO / "figures" / "fig5_disagreement.png"

LABELS = ["prokremlowski", "antywojenny", "prozachodni", "bialorusko-narodowy", "neutralny-informacyjny"]
LABEL_SHORT = {"prokremlowski": "pro-Kremlin", "antywojenny": "antiwar",
               "prozachodni": "pro-Western", "bialorusko-narodowy": "BY-national",
               "neutralny-informacyjny": "neutral"}
LABEL_COLOR = {"prokremlowski": "#c0392b", "antywojenny": "#27ae60",
               "prozachodni": "#2980b9", "bialorusko-narodowy": "#8e44ad",
               "neutralny-informacyjny": "#7f8c8d"}


def main():
    wide = pd.read_csv(WIDE)
    long = pd.read_csv(LONG)
    configs = ["claude_A", "claude_B", "gpt_A", "gpt_B"]

    def disagree(c1, c2):
        m = wide[c1].notna() & wide[c2].notna()
        return 100 * (wide.loc[m, c1] != wide.loc[m, c2]).mean()

    pairs = [
        ("Claude vs GPT\n(prompt A)", disagree("claude_A", "gpt_A"), "#e67e22"),
        ("Claude vs GPT\n(prompt B)", disagree("claude_B", "gpt_B"), "#e67e22"),
        ("Claude A vs B\n(prompt only)", disagree("claude_A", "claude_B"), "#3498db"),
        ("GPT A vs B\n(prompt only)", disagree("gpt_A", "gpt_B"), "#3498db"),
    ]
    n_unanimous = wide[configs].apply(lambda r: len(set(r.dropna())) == 1, axis=1).mean() * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))

    names = [p[0] for p in pairs]
    vals = [p[1] for p in pairs]
    cols = [p[2] for p in pairs]
    bars = ax1.bar(names, vals, color=cols, edgecolor="white", width=0.6)
    for b, v in zip(bars, vals):
        ax1.text(b.get_x()+b.get_width()/2, v+0.7, f"{v:.1f}%", ha="center", fontweight="bold")
    ax1.set_ylabel("% items where the two configs differ")
    ax1.set_title("Two frontier models, same codebook, temp 0 —\n"
                  "disagree on ~28% of items (Benchmark Illusion)", fontsize=11.5, loc="left")
    ax1.set_ylim(0, max(vals) + 8)
    # legend
    from matplotlib.patches import Patch
    ax1.legend(handles=[Patch(color="#e67e22", label="cross-MODEL"),
                        Patch(color="#3498db", label="cross-PROMPT")],
               loc="upper right", fontsize=9)
    ax1.text(0.02, 0.95, f"4-way unanimity: {n_unanimous:.0f}%",
             transform=ax1.transAxes, fontsize=10, color="#444",
             bbox=dict(boxstyle="round", fc="#f5f5f5", ec="#ccc"))
    ax1.spines[["top", "right"]].set_visible(False)

    # Right: label distribution per config (grouped bars)
    dist = long.groupby(["config", "label"]).size().unstack(fill_value=0).reindex(columns=LABELS, fill_value=0)
    dist = dist.reindex(configs)
    x = np.arange(len(configs))
    w = 0.16
    for i, lbl in enumerate(LABELS):
        ax2.bar(x + (i - 2) * w, dist[lbl].values, w, label=LABEL_SHORT[lbl], color=LABEL_COLOR[lbl])
    ax2.set_xticks(x); ax2.set_xticklabels(configs, fontsize=9)
    ax2.set_ylabel("count (of 60 items)")
    ax2.set_title("Systematic model bias: GPT-4o labels more 'antiwar',\n"
                  "Claude defaults more to 'neutral'", fontsize=11.5, loc="left")
    ax2.legend(fontsize=8, ncol=2, loc="upper center")
    ax2.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
