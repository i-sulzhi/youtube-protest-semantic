"""Backup slide B3 — validation metrics & statistical-correction formulas.

Renders the methodologist-facing formulas (Cohen's κ, Krippendorff's α,
DSL, PPI) cleanly via matplotlib mathtext, so the candidate can show a
single defensible reference slide under Olszowski-style scrutiny.

Output: figures/fig6_formulas.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "figures" / "fig6_formulas.png"

fig, ax = plt.subplots(figsize=(12, 7.6))
ax.axis("off")
ax.set_xlim(0, 10); ax.set_ylim(0, 10)

ax.text(0.2, 9.6, "Backup — metryki zgodności i korekta statystyczna",
        fontsize=15, fontweight="bold")

blocks = [
    (8.7, "Cohen's κ  (zgodność dwóch koderów)",
     r"$\kappa = \frac{p_o - p_e}{1 - p_e}$",
     "p_o = zgodność obserwowana,  p_e = zgodność oczekiwana losowo.\n"
     "κ koryguje surową zgodność o zgodność przypadkową. κ>0,8 = b. dobra; 0,6-0,8 = znacząca."),
    (6.9, "Krippendorff's α  (n ≥ 2 koderów, dane nominalne)",
     r"$\alpha = 1 - \frac{D_o}{D_e}$",
     "D_o = obserwowana niezgodność,  D_e = oczekiwana niezgodność.\n"
     "Działa dla >2 koderów i braków danych. Tu: {człowiek, Claude, GPT-4o}."),
    (5.1, "Design-Based Supervised Learning — DSL  (Egami i in. 2023)",
     r"$Y_i^{*} = g(X_i) + \frac{R_i}{\pi_i}\,(Y_i - g(X_i))$",
     "g(X) = etykieta LLM,  R=1 dla próby złotej (prawdopod. π).\n"
     "Daje nieobciążony estymator z poprawnymi przedziałami ufności — nawet gdy LLM jest skrzywiony."),
    (3.1, "Prediction-Powered Inference — PPI  (Angelopoulos i in. 2023, Science)",
     r"$\hat{\theta}_{PPI} = \hat{\theta}_{f}\ -\ (\hat{\Delta}_{f} - \hat{\Delta}_{Y})$",
     "θ_f = ML na całości,  (Δ_f − Δ_Y) = rektyfikacja na próbie złotej.\n"
     "Buduje ważne CI z predykcji ML + małej próby. Naiwne wstawienie etykiet LLM psuje CI nawet przy 80-90% trafności."),
]

for y, title, formula, note in blocks:
    ax.text(0.2, y + 0.55, title, fontsize=12, fontweight="bold", color="#1f5c8a")
    ax.text(0.5, y - 0.15, formula, fontsize=17, color="#111")
    ax.text(5.4, y - 0.05, note, fontsize=9.2, color="#333", va="center")

ax.text(0.2, 0.9,
        "Wniosek operacyjny: anotacje LLM jako zmienne w regresji wymagają DSL lub PPI —\n"
        "inaczej przedziały ufności są zaniżone. To jest mój standard metodologiczny.",
        fontsize=10.5, style="italic", color="#a02020")

fig.tight_layout()
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"Wrote {OUT}")
