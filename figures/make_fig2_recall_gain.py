"""Figure 2 — retrieval recall gain over the keyword baseline.

Two panels:
  (left) distinct newly-surfaced videos: single encoder → 2-way UNION → 4-way UNION
  (right) per-anchor newly-surfaced rate (e5-large), re-derived 2026-05-28

Data: docs/RESULTS_LOG.md (UNION counts) + outputs/retrieval_e5large (per-anchor),
re-verified to match the log exactly.

Output: figures/fig2_recall_gain.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "figures" / "fig2_recall_gain.png"

# Newly-surfaced counts (docs/RESULTS_LOG.md, reproduced 2026-05-28)
methods = ["e5-small\nalone", "e5-large\nalone", "2-way\nUNION", "4-way\nUNION"]
newly = [315, 329, 527, 712]
colors = ["#9aa0a6", "#9aa0a6", "#f5b342", "#e67e22"]

# Per-anchor newly-surfaced rate, e5-large (re-run today; matches RESULTS_LOG)
anchors = {
    "BY-2020": 50.0, "RU-antiwar": 63.0, "RU-Navalny": 39.0,
    "RU-mobilis.": 63.0, "UA-Maidan": 85.0, "UA-current": 82.0, "general": 74.0,
}

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.4))

# Left: recall gain
bars = ax1.bar(methods, newly, color=colors, edgecolor="white", width=0.62)
ax1.set_ylabel("newly-surfaced videos\n(no protest keyword in text)")
ax1.set_title("Semantic retrieval surfaces protest videos\nthat keyword search misses", fontsize=12, loc="left")
for b, v in zip(bars, newly):
    ax1.text(b.get_x() + b.get_width()/2, v + 10, f"{v}", ha="center", fontweight="bold")
# annotate gains
ax1.annotate("+60%\nvs best single", xy=(2, 527), xytext=(1.5, 600),
             fontsize=10, color="#b9770e", fontweight="bold")
ax1.annotate("+116%\nvs best single", xy=(3, 712), xytext=(2.55, 760),
             fontsize=10, color="#a04000", fontweight="bold", ha="center")
ax1.set_ylim(0, 870)
ax1.spines[["top", "right"]].set_visible(False)

# Right: per-anchor rate
keys = list(anchors.keys())
vals = list(anchors.values())
bars2 = ax2.barh(keys[::-1], vals[::-1], color="#2980b9", edgecolor="white")
ax2.set_xlabel("% of top-100 with NO surface protest keyword")
ax2.set_title("Per-anchor newly-surfaced rate (e5-large)\nmedian = 63%", fontsize=12, loc="left")
ax2.axvline(63, color="#c0392b", ls="--", lw=1, label="median 63%")
for b, v in zip(bars2, vals[::-1]):
    ax2.text(v + 1.5, b.get_y() + b.get_height()/2, f"{v:.0f}%", va="center", fontsize=9)
ax2.set_xlim(0, 100)
ax2.legend(loc="lower right", fontsize=9)
ax2.spines[["top", "right"]].set_visible(False)

fig.tight_layout()
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"Wrote {OUT}")
