"""Figure 9 — the Slavic gap, made concrete: one frame, two readings.

A documentary information card (sec 0:16:12) carrying the factual backbone of
the protest story in Russian. GPT-4o transcribes and extracts the content;
LLaVA (open-weight) cannot read Cyrillic — it only guesses the language and
emits index numbers.

Quantified over the corpus: GPT-4o transcribes Cyrillic in 12% of frames;
LLaVA in 0% (and labels text as "foreign" in 8.1%).

This is the reproducibility-vs-capability trade-off (Spirling 2023) made
literal on Slavic visual material: the open model is reproducible but blind to
the script; the closed model reads it but is not reproducible.

Frame: know_this_summer/frames_per_sec/frame_972.jpg
Annotations: the two models' actual output for this frame.

Output: figures/fig9_slavic_gap.png
"""
import os
from pathlib import Path
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# Sibling projects live next to this repo (nexus/code on the Mac, C:\code on the PC);
# override with the NEXUS_CODE environment variable.
CODE_ROOT = Path(os.environ.get("NEXUS_CODE", Path(__file__).resolve().parents[2]))


REPO = Path(__file__).resolve().parent.parent
FRAME = (CODE_ROOT / "know_this_summer" / "frames_per_sec" / "frame_972.jpg")
OUT = REPO / "figures" / "fig9_slavic_gap.png"

GPT_KW = ("настоящe время, tekst, data, 9 sierpnia, Białoruś, protesty, ludzie, "
          "żądanie uczciwego liczenia głosów, zatrzymania, informacja, nowości, "
          "czarne tło, biały tekst")
GPT_NOTE = "GPT-4o czyta i transkrybuje treść karty (fakt: «dziesiątki tysięcy… ok. 3 tys. zatrzymanych»)"

LLA_KW = ('5, 2, 3, "the text is in Cyrillic characters", 1, "the text is in '
          'Russian", "foreign language text", 4, "the text is in Bulgarian", '
          '"white text on black background"')
LLA_NOTE = "LLaVA (open-weight) nie czyta cyrylicy — zgaduje język i zwraca numery"


def main():
    fig = plt.figure(figsize=(13, 6.2))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], height_ratios=[1, 1],
                          wspace=0.08, hspace=0.18)

    # left: the frame, spanning both rows
    axf = fig.add_subplot(gs[:, 0])
    axf.imshow(mpimg.imread(FRAME))
    axf.set_xticks([]); axf.set_yticks([])
    for s in axf.spines.values():
        s.set_edgecolor("#888")
    axf.set_title("Kadr 0:16:12 — karta informacyjna (tekst rosyjski)", fontsize=10.5, loc="left")

    # right top: GPT
    axg = fig.add_subplot(gs[0, 1]); axg.axis("off")
    axg.add_patch(plt.Rectangle((0, 0), 1, 1, transform=axg.transAxes,
                  fc="#eafaef", ec="#27ae60", lw=2))
    axg.text(0.04, 0.93, "GPT-4o (closed)", fontsize=12, fontweight="bold",
             color="#1a7a3a", va="top")
    axg.text(0.04, 0.75, "\n".join(textwrap.wrap(GPT_KW, 46)), fontsize=8.8, va="top", color="#143")
    axg.text(0.04, 0.20, "\n".join(textwrap.wrap(GPT_NOTE, 52)), fontsize=8.2,
             va="top", style="italic", color="#1a7a3a")

    # right bottom: LLaVA
    axl = fig.add_subplot(gs[1, 1]); axl.axis("off")
    axl.add_patch(plt.Rectangle((0, 0), 1, 1, transform=axl.transAxes,
                  fc="#fdeeea", ec="#c0392b", lw=2))
    axl.text(0.04, 0.93, "LLaVA-v1.5 (open-weight)", fontsize=12, fontweight="bold",
             color="#a02020", va="top")
    axl.text(0.04, 0.75, "\n".join(textwrap.wrap(LLA_KW, 46)), fontsize=8.8, va="top", color="#411")
    axl.text(0.04, 0.20, "\n".join(textwrap.wrap(LLA_NOTE, 52)), fontsize=8.2,
             va="top", style="italic", color="#a02020")

    fig.suptitle("Luka słowiańska, konkretnie: ten sam kadr, dwa odczyty",
                 fontsize=14, y=0.99)
    fig.text(0.5, 0.005,
             "W całym korpusie: GPT-4o transkrybuje cyrylicę w 12% klatek, LLaVA w 0% "
             "(„foreign” w 8,1%).  Na materiale słowiańskim wybór modelu decyduje, co w ogóle da się odczytać.\n"
             "Reprodukowalność vs zdolność (Spirling 2023): model otwarty jest powtarzalny, ale ślepy na pismo; "
             "zamknięty czyta, ale nie jest powtarzalny.",
             ha="center", fontsize=9, style="italic", color="#444")
    fig.subplots_adjust(top=0.91, bottom=0.10)
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
