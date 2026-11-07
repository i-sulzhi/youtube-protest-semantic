"""Figure 12 — SYNTEZA: podział pracy poznawczej (LLM / AGENT / CZŁOWIEK).

The answer to the talk's title question ("Czy można ufać AI w badaniach
społecznych?") is NOT yes/no — it is a MAP of who does what and why.

Three owners, each a column, each cell carrying an empirical number from the talk:
  - LLM      (zielony)  — rozpoznawanie i skala: ufaj, ale waliduj
  - AGENT    (niebieski)— orkiestracja i triage: warstwa pośrednia
  - CZŁOWIEK (pomarańcz)— konstrukt, sporne, kontekst, podmiot: niezastąpiony

The dividing principle runs across the bottom: the boundary is NOT
easy-vs-hard-for-machine, but UNAMBIGUOUS (jednoznaczne) vs CONTESTED (sporne).
The agent is the thing that separates them (disagreement detector + routing).

Output: figures/fig12_division_of_labor.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "figures" / "fig12_division_of_labor.png"

# ---- column definitions -----------------------------------------------------
GREEN  = "#1a7a3a"
BLUE   = "#1f5fa0"
ORANGE = "#b9770e"
GREEN_BG  = "#e7f4ec"
BLUE_BG   = "#e6eef7"
ORANGE_BG = "#fbf0dd"

COLS = [
    dict(
        x=0.5, color=GREEN, bg=GREEN_BG,
        owner="LLM",
        sub="rozpoznawanie i skala",
        tag="ufaj, ale waliduj",
        rows=[
            ("Retrieval semantyczny", "+60% recall · 90% metonimii"),
            ("Percepcja w wideo", "flaga / noc / tłum ~100% recall"),
            ("Anotacja przy zgodzie", "68% jednomyślności → automat"),
        ],
    ),
    dict(
        x=4.0, color=BLUE, bg=BLUE_BG,
        owner="AGENT",
        sub="orkiestracja i triage",
        tag="warstwa pośrednia",
        rows=[
            ("Ansambl modeli/promptów", "4 równoległe sub-agenty · temp 0"),
            ("Detektor niezgody", "28% cross-model · 49% BY-2020"),
            ("Routing + provenance", "pewne → auto · sporne → człowiek"),
        ],
    ),
    dict(
        x=7.5, color=ORANGE, bg=ORANGE_BG,
        owner="CZŁOWIEK",
        sub="konstrukt · sporne · kontekst · podmiot",
        tag="niezastąpiony",
        rows=[
            ("Konstrukt / kodbook", "52% forced-fit · 2 luki kategorii"),
            ("Rozstrzyganie spornych", "11 contested (sam koder zaznaczył)"),
            ("Kontekst kulturowy", "głosowanie 35/17% · cyrylica 0%"),
            ("Rola respondenta", "silicon sampling — nierozwiązane"),
        ],
    ),
]

COL_W = 3.0
fig, ax = plt.subplots(figsize=(13.5, 7.6))
ax.set_xlim(0, 11)
ax.set_ylim(0, 11)
ax.axis("off")

# ---- title ------------------------------------------------------------------
ax.text(5.5, 10.6, "Podział pracy poznawczej", fontsize=20, fontweight="bold",
        ha="center", va="center")
ax.text(5.5, 10.05,
        "Odpowiedź to nie „tak/nie”, lecz mapa: kto robi co i dlaczego",
        fontsize=12, ha="center", va="center", style="italic", color="#444")

ROW_TOP = 9.0      # y of first row top
ROW_H = 0.92       # height per row
HEAD_H = 1.05

for col in COLS:
    x = col["x"]
    n = len(col["rows"])
    # header box
    head_y = ROW_TOP
    ax.add_patch(FancyBboxPatch(
        (x, head_y), COL_W, HEAD_H,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=0, facecolor=col["color"], zorder=2))
    ax.text(x + COL_W/2, head_y + HEAD_H*0.66, col["owner"],
            fontsize=17, fontweight="bold", color="white",
            ha="center", va="center", zorder=3)
    ax.text(x + COL_W/2, head_y + HEAD_H*0.26, col["sub"],
            fontsize=9.5, color="white", ha="center", va="center", zorder=3)
    # tag chip under header
    ax.text(x + COL_W/2, head_y - 0.18, col["tag"],
            fontsize=10, fontweight="bold", color=col["color"],
            ha="center", va="center", zorder=3)

    # rows
    for i, (task, num) in enumerate(col["rows"]):
        ry = head_y - 0.5 - (i + 1) * ROW_H
        ax.add_patch(FancyBboxPatch(
            (x, ry), COL_W, ROW_H - 0.12,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            linewidth=1.1, edgecolor=col["color"], facecolor=col["bg"], zorder=2))
        ax.text(x + 0.18, ry + (ROW_H-0.12)*0.62, task,
                fontsize=10.5, fontweight="bold", color="#222",
                ha="left", va="center", zorder=3)
        ax.text(x + 0.18, ry + (ROW_H-0.12)*0.24, num,
                fontsize=9.5, color=col["color"], ha="left", va="center",
                zorder=3, fontweight="bold")

# ---- bottom: dividing principle ---------------------------------------------
band_y = 0.55
ax.add_patch(FancyBboxPatch(
    (0.5, band_y), 10.0, 1.25,
    boxstyle="round,pad=0.02,rounding_size=0.1",
    linewidth=1.4, edgecolor="#555", facecolor="#f4f4f4", zorder=2))
ax.text(5.5, band_y + 0.92,
        "Granica NIE przebiega między łatwym a trudnym dla maszyny,",
        fontsize=12, ha="center", va="center", color="#222", zorder=3)
ax.text(5.5, band_y + 0.45,
        "lecz między znaczeniem JEDNOZNACZNYM a SPORNYM.",
        fontsize=13.5, fontweight="bold", ha="center", va="center",
        color="#a02020", zorder=3)

# arrow: unambiguous (LLM, green) ----> contested (human, orange)
ax.annotate("", xy=(9.2, 0.18), xytext=(1.8, 0.18),
            arrowprops=dict(arrowstyle="-|>", lw=2.2,
                            color="#777"))
ax.text(2.0, 0.36, "jednoznaczne → automat", fontsize=10, color=GREEN,
        fontweight="bold", ha="left", va="center")
ax.text(9.0, 0.36, "sporne → człowiek", fontsize=10, color=ORANGE,
        fontweight="bold", ha="right", va="center")
ax.text(5.5, 0.05,
        "agent = to, co rozdziela jedno od drugiego (detektor niezgody + routing)",
        fontsize=9.5, ha="center", va="center", style="italic", color="#444")

fig.tight_layout()
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"Wrote {OUT}")
