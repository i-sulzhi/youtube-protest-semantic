"""Figure 1 — the validation-maturity axis (conceptual anchor of the talk).

A single horizontal scale: text (mature) → images (developing) →
video × Slavic (frontier — the candidate's territory). Hand-designed,
no data dependency.

Output: figures/fig1_maturity_axis.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
import numpy as np

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "figures" / "fig1_maturity_axis.png"

fig, ax = plt.subplots(figsize=(12, 4.2))
ax.set_xlim(0, 10); ax.set_ylim(0, 5)
ax.axis("off")

# gradient bar
grad = np.linspace(0, 1, 256).reshape(1, -1)
ax.imshow(grad, extent=[0.5, 9.5, 2.4, 3.0], aspect="auto",
          cmap="RdYlGn_r", alpha=0.85, zorder=1)

# arrow
ax.add_patch(FancyArrowPatch((0.5, 2.7), (9.65, 2.7),
             arrowstyle="-|>", mutation_scale=22, lw=2, color="#333", zorder=3))

stages = [
    (1.8, "TEKST", "dojrzała\n(κ, α, F1, DSL/PPI,\nLLM-Hacking stress-test)", "#1a7a3a"),
    (5.0, "OBRAZ", "rozwijająca się\n(GPT-4V, LLaVA;\nmało raportowanych κ/α)", "#b9770e"),
    (8.2, "WIDEO × SŁOWIAŃSKIE", "front badań\n(brak recenzowanych protokołów\nz inter-coder reliability)", "#a02020"),
]
for x, title, sub, color in stages:
    ax.plot([x, x], [2.4, 3.0], color="#333", lw=1.5, zorder=4)
    ax.text(x, 3.55, title, ha="center", fontsize=13, fontweight="bold", color=color)
    ax.text(x, 1.95, sub, ha="center", va="top", fontsize=9.5, color="#333")

# left/right captions
ax.text(0.5, 1.2, "← walidacja dojrzała", fontsize=10, color="#1a7a3a", style="italic")
ax.text(9.5, 1.2, "walidacja niedojrzała →", fontsize=10, color="#a02020",
        style="italic", ha="right")

# "my territory" marker
ax.annotate("← tu pracuję", xy=(8.2, 3.0), xytext=(8.2, 4.35),
            ha="center", fontsize=12, fontweight="bold", color="#a02020",
            arrowprops=dict(arrowstyle="-|>", color="#a02020", lw=2))

ax.set_title("Dojrzałość walidacji modeli językowych wg modalności danych",
             fontsize=14, pad=14, loc="center")

fig.tight_layout()
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"Wrote {OUT}")
