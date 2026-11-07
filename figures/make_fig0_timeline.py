"""Slide-3 figure — research-trajectory timeline (od tekstu do obrazu).

Two-lane timeline:
  upper lane = TEXT & NETWORKS (2021-2024)
  lower lane = MULTIMODAL TURN (2023-2026)
with the methodological question emerging at the transition.

No data dependency. Output: figures/fig0_timeline.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "figures" / "fig0_timeline.png"

fig, ax = plt.subplots(figsize=(13, 5.2))
ax.set_xlim(2020.5, 2026.5)
ax.set_ylim(0, 10)
ax.axis("off")

# time axis
ax.annotate("", xy=(2026.4, 5), xytext=(2020.6, 5),
            arrowprops=dict(arrowstyle="-|>", color="#444", lw=1.6))
for yr in range(2021, 2027):
    ax.plot([yr, yr], [4.85, 5.15], color="#888", lw=1)
    ax.text(yr, 4.5, str(yr), ha="center", fontsize=10, color="#555")

TEXT = "#1f5c8a"
MM = "#a04000"

def box(x, y, w, h, text, color):
    ax.add_patch(FancyBboxPatch((x - w/2, y - h/2), w, h,
                 boxstyle="round,pad=0.03,rounding_size=0.12",
                 fc="white", ec=color, lw=1.8))
    ax.text(x, y, text, ha="center", va="center", fontsize=8.6, color="#222", wrap=True)

# Upper lane — TEXT & NETWORKS
ax.text(2020.7, 8.7, "TEKST i SIECI", fontsize=12, fontweight="bold", color=TEXT)
box(2021.6, 7.7, 1.7, 1.2, "Hate-speech\nTelegram\n(JBS 2022)", TEXT)
box(2023.2, 7.7, 1.9, 1.2, "Ramy wojny RU/UA\n(Studies in Comm.\nSciences 2024)", TEXT)
box(2024.6, 7.7, 1.9, 1.2, "Ambassadors of War\nhub-and-spoke\n(Intersections 2025)", TEXT)
for x in [2021.6, 2023.2, 2024.6]:
    ax.plot([x, x], [5.15, 7.1], color=TEXT, lw=1, ls=":")

# Lower lane — MULTIMODAL TURN
ax.text(2020.7, 1.3, "ZWROT MULTIMODALNY", fontsize=12, fontweight="bold", color=MM)
box(2023.6, 2.3, 2.0, 1.2, "YouTube + LLM +\nmodelowanie tematyczne\n(DHd 2025 Bielefeld)", MM)
box(2025.3, 2.3, 2.0, 1.2, "Korpus 401k →\nwyszukiwanie semantyczne\n(ten projekt)", MM)
for x in [2023.6, 2025.3]:
    ax.plot([x, x], [2.9, 4.85], color=MM, lw=1, ls=":")

# transition marker
ax.annotate("«Czy można ufać\nnarzędziom, którymi\nczytamy ten materiał?»",
            xy=(2024.0, 5), xytext=(2024.0, 5),
            ha="center", va="center", fontsize=9.5, style="italic", color="#a02020",
            bbox=dict(boxstyle="round,pad=0.4", fc="#fff5f0", ec="#a02020", lw=1.3))

ax.set_title("Od tekstu do obrazu — trajektoria badawcza, z której wyrasta pytanie metodologiczne",
             fontsize=13, pad=12)

fig.tight_layout()
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"Wrote {OUT}")
