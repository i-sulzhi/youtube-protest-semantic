"""Figure 10 — the killer move: disagreement is a MAP of contested meaning.

Two panels showing that cross-model disagreement is NOT random noise but
concentrates on substantively contested categories:

  (left)  text — Claude vs GPT-4o disagreement by anchor (N=200).
          Belarus-2020 stands out (48.6%) — exactly the case where the
          'białorusko-narodowy' and 'antywojenny' framings overlap.
  (right) where the disagreement lands — top label transitions (Claude→GPT).
          The systematic confusion is national-identity ↔ anti-war, i.e. the
          genuine scholarly debate about how to read the Belarusian protest.

Message: where the models disagree is where the scholars disagree → inter-model
disagreement is an automatic detector of contested cases for human review
(gated human-in-the-loop; Gligorić et al. 2024).

Output: figures/fig10_disagreement_map.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "figures" / "fig10_disagreement_map.png"

# from /tmp/fig10_data.py (N=200, reproducible)
ANCHORS = [
    ("BY-2020", 48.6, 35),
    ("UA-current", 23.6, 55),
    ("RU-mobilis.", 18.8, 32),
    ("general", 18.8, 48),
    ("RU-antiwar", 16.7, 30),
]
TRANS = [
    ("neutral → antiwar", 14, "#7f8c8d"),
    ("BY-national → antiwar", 7, "#8e44ad"),
    ("antiwar → neutral", 6, "#27ae60"),
    ("pro-Kremlin → neutral", 5, "#c0392b"),
    ("BY-national → neutral", 4, "#8e44ad"),
    ("neutral → BY-national", 4, "#7f8c8d"),
]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.4))

# Left — disagreement by anchor
names = [a[0] for a in ANCHORS][::-1]
vals = [a[1] for a in ANCHORS][::-1]
colors = ["#c0392b" if v > 40 else "#3498db" for v in vals]
bars = ax1.barh(names, vals, color=colors, edgecolor="white")
for b, v in zip(bars, vals):
    ax1.text(v + 0.8, b.get_y() + b.get_height()/2, f"{v:.0f}%", va="center", fontsize=10, fontweight="bold")
ax1.axvline(25, color="#888", ls="--", lw=1)
ax1.text(25.5, 0.1, "śr. 25%", fontsize=8, color="#888", rotation=90, va="bottom")
ax1.set_xlim(0, 60)
ax1.set_xlabel("% niezgody Claude vs GPT-4o (N=200)")
ax1.set_title("Niezgoda NIE jest losowa — koncentruje się\nna Białorusi-2020 (granica ramy)", fontsize=12, loc="left")
ax1.annotate("← tu nakładają się ramy\n«narodowa» i «antywojenna»",
             xy=(48.6, 4), xytext=(30, 3.0), fontsize=9, color="#a02020",
             arrowprops=dict(arrowstyle="-|>", color="#a02020", lw=1.4))
ax1.spines[["top", "right"]].set_visible(False)

# Right — transitions
tnames = [t[0] for t in TRANS][::-1]
tvals = [t[1] for t in TRANS][::-1]
tcols = [t[2] for t in TRANS][::-1]
b2 = ax2.barh(tnames, tvals, color=tcols, edgecolor="white")
for b, v in zip(b2, tvals):
    ax2.text(v + 0.15, b.get_y() + b.get_height()/2, str(v), va="center", fontsize=10, fontweight="bold")
ax2.set_xlabel("liczba itemów (gdzie modele się różnią)")
ax2.set_title("Gdzie ląduje niezgoda: oś narodowa ↔ antywojenna\n(realny spór naukowy o protest białoruski)", fontsize=12, loc="left")
ax2.spines[["top", "right"]].set_visible(False)

fig.suptitle("Tam, gdzie nie zgadzają się modele — tam, gdzie nie zgadzają się badacze",
             fontsize=14.5, y=1.02)
fig.text(0.5, -0.04,
         "Niezgoda międzymodelowa = automatyczny detektor spornych przypadków → kieruj je do człowieka "
         "(gated human-in-the-loop; Gligorić i in. 2024).\n"
         "Z problemu („który model ma rację?”) robi się instrument („gdzie znaczenie jest sporne?”).",
         ha="center", fontsize=9.5, style="italic", color="#444")

fig.tight_layout(rect=[0, 0.02, 1, 0.95])
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"Wrote {OUT}")
