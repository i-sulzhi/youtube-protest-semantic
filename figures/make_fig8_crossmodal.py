"""Figure 8 — the central thesis proven across BOTH modalities.

Two panels, two metrics, one message: two frontier models, same data,
diverge sharply — so the model choice is a researcher degree of freedom.

  (left)  TEXT — Claude vs GPT-4o categorical framing-label agreement (N=200):
          agree 75% / disagree 25%.
  (right) VIDEO — GPT-4o mini vs LLaVA-v1.5 per-frame keyword-set Jaccard
          (3 094/3 730 frames): mean ≈ 0.07 overlap. Source: peer-reviewed
          DH 2025 (Howanitz, Kaltseis & Sulzhytski 2025). The keyword data
          used there (dataframe_backup.xlsx) is not in the local repo, so the
          figure CITES the published value rather than recomputing it.

NOTE: the two panels use DIFFERENT metrics (categorical-label disagreement vs
keyword-set Jaccard) — they are complementary evidence for the same qualitative
point, NOT the same number. Labelled as such on the figure.

Output: figures/fig8_crossmodal.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "figures" / "fig8_crossmodal.png"

# Text side (from mini_study/cross_model_200.md)
TEXT_AGREE = 75.0
TEXT_DISAGREE = 25.0
# Video side — GPT-4o keywords vs LLaVA keywords, per-frame Jaccard.
# DH 2025 (Howanitz/Kaltseis/Sulzhytski) report 0.07; independent recompute on
# the available keyword data (combined_frames_gpto_sorted-2.pkl, 100% identical
# to the scenes-file keywords) gives 0.106. Both => very low overlap.
VIDEO_JACCARD = 0.106  # bar length; label shows the 0,07–0,11 range

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.4))

# Left: text categorical agreement (stacked bar)
ax1.bar(["Claude vs GPT-4o"], [TEXT_AGREE], color="#27ae60", label="zgoda", width=0.5)
ax1.bar(["Claude vs GPT-4o"], [TEXT_DISAGREE], bottom=[TEXT_AGREE], color="#c0392b",
        label="niezgoda", width=0.5)
ax1.text(0, TEXT_AGREE/2, f"{TEXT_AGREE:.0f}%\nzgoda", ha="center", va="center",
         color="white", fontweight="bold", fontsize=12)
ax1.text(0, TEXT_AGREE + TEXT_DISAGREE/2, f"{TEXT_DISAGREE:.0f}%\nniezgoda", ha="center",
         va="center", color="white", fontweight="bold", fontsize=12)
ax1.set_ylim(0, 100)
ax1.set_ylabel("% itemów (N=200)")
ax1.set_title("TEKST — zgodność etykiety ramy\n(metryka: identyczna kategoria)",
              fontsize=12, loc="left")
ax1.spines[["top", "right"]].set_visible(False)
ax1.legend(loc="center right", fontsize=9)

# Right: video Jaccard gauge-style bar
ax2.barh(["GPT-4o vs LLaVA"], [VIDEO_JACCARD], color="#e67e22", height=0.4)
ax2.barh(["GPT-4o vs LLaVA"], [1 - VIDEO_JACCARD], left=[VIDEO_JACCARD],
         color="#ecdccb", height=0.4)
ax2.text(VIDEO_JACCARD + 0.02, 0, "  Jaccard ≈ 0,07–0,11\n  (~7–11% wspólnych słów)",
         va="center", fontsize=12, fontweight="bold", color="#a04000")
ax2.set_xlim(0, 1)
ax2.set_xlabel("średnie pokrycie słów kluczowych na klatkę (Jaccard)")
ax2.set_title("WIDEO — zgodność adnotacji wizualnej\n(metryka: pokrycie zbiorów słów)",
              fontsize=12, loc="left")
ax2.spines[["top", "right"]].set_visible(False)
ax2.set_yticks([0]); ax2.set_yticklabels(["GPT-4o vs\nLLaVA"], fontsize=9)

fig.suptitle("Ta sama teza, dwie modalności:  dwa czołowe modele, te same dane — rozchodzą się",
             fontsize=14, y=1.02)
fig.text(0.5, -0.04,
         "Różne metryki (kategoria vs zbiór słów) — komplementarne dowody tego samego: "
         "wybór modelu to ukryty stopień swobody badacza.\n"
         "Tekst: korpus YouTube N=200 (pomiar własny).  Wideo: 3 730 klatek dokumentu 2020 — "
         "recenzowane 0,07 (DH 2025), niezależne przeliczenie na słowach kluczowych 0,11.  LLaVA = open-weight (reprodukowalność).",
         ha="center", fontsize=9, style="italic", color="#444")

fig.tight_layout(rect=[0, 0.02, 1, 0.96])
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"Wrote {OUT}")
