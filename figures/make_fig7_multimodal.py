"""Slide-13 figure — the multimodal frontier, as a WORKING result.

2×2 montage of frames from the 2020-Belarus protest documentary
(«Мы не знали друг друга до этого лета», Abramchik 2021) with the GPT-4o
visual annotations that drive the distant-viewing pipeline
(Sulzhytski & Howanitz 2025, manuscript under review).

Demonstrates that "multimodal" in the talk title is a real result, not a
promise: same event (Belarus 2020) as the multilingual text study, second
modality (video), same method family (LLM annotation + topic modeling).

Frames from: know_this_summer/frames_per_sec/
Annotations: GPT-4o KEYWORDS from keywords_tokens_scenes_borders_and_numbers.pkl
(comma-separated keyword output, NOT the prose-description run).

Output: figures/fig7_multimodal.png
"""
import os
from pathlib import Path
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import pandas as pd

# Sibling projects live next to this repo (nexus/code on the Mac, C:\code on the PC);
# override with the NEXUS_CODE environment variable.
CODE_ROOT = Path(os.environ.get("NEXUS_CODE", Path(__file__).resolve().parents[2]))


REPO = Path(__file__).resolve().parent.parent
KTS = (CODE_ROOT / "know_this_summer")
FRAMES = KTS / "frames_per_sec"
PKL = KTS / "keywords_tokens_scenes_borders_and_numbers.pkl"  # GPT-4o KEYWORDS (not prose)
OUT = REPO / "figures" / "fig7_multimodal.png"

# representative frames (Seconds) + how many leading keywords to show
PICKS = [800, 2900, 2200, 3400]
N_KW = 9


def main():
    df = pd.read_pickle(PKL).reset_index()
    df["sec"] = df["Seconds"].astype(int)
    kw_by_sec = {int(r["sec"]): str(r["keywords"]) for _, r in df.iterrows()}

    fig, axes = plt.subplots(2, 2, figsize=(12, 9.6))
    axes = axes.ravel()
    for ax, sid in zip(axes, PICKS):
        img_path = FRAMES / f"frame_{sid}.jpg"
        if img_path.exists():
            ax.imshow(mpimg.imread(img_path), aspect="equal")
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_edgecolor("#888"); s.set_linewidth(0.8)
        kws = [k.strip() for k in kw_by_sec.get(sid, "").split(",") if k.strip()][:N_KW]
        gloss = "GPT-4o: " + ", ".join(kws)
        cap = "\n".join(textwrap.wrap(gloss, 64))
        ax.set_xlabel(cap, fontsize=9, color="#222", labelpad=6)

    fig.suptitle(
        "Front multimodalny — wynik, nie obietnica:  dokument o protestach 2020 (Abramczyk)\n"
        "62 min → 3 730 klatek → adnotacja GPT-4o → 13 stabilnych tematów (Ensemble LDA)",
        fontsize=12.5, y=0.99)
    fig.text(0.5, 0.012,
             "Ten sam protest co w korpusie tekstowym — druga modalność, ta sama rodzina metod "
             "(adnotacja LLM + modelowanie tematyczne).  Sulzhytski & Howanitz 2025, w recenzji.",
             ha="center", fontsize=9.5, style="italic", color="#a02020")
    fig.subplots_adjust(left=0.03, right=0.97, top=0.91, bottom=0.07, wspace=0.12, hspace=0.28)
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
