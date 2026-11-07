"""Validation metrics — Cohen's κ, Krippendorff's α, per-class F1, confusion.

Run AFTER the human coding sheet is filled. Computes the slide-9 numbers:
  - Cohen's κ: human × each LLM config (overall + per-class one-vs-rest)
  - Krippendorff's α (nominal) across {human, claude, gpt}
  - Per-class precision / recall / F1 (human = gold)
  - Confusion matrices (human × claude_A, human × gpt_A) → figures/fig4_kappa.png

Inputs:
  mini_study/coding_sheet_for_human_FILLED.csv   (REQUIRED — human labels)
  mini_study/all_predictions_wide.csv            (LLM labels)

If the FILLED sheet is absent, runs in SELF-TEST mode using claude_A as a
stand-in "human" so the pipeline is verified end-to-end before real labels exist.

Outputs:
  mini_study/validation_metrics.md
  figures/fig4_kappa.png
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import cohen_kappa_score, classification_report, confusion_matrix

REPO = Path(__file__).resolve().parent.parent
FILLED = REPO / "mini_study" / "coding_sheet_for_human_FILLED.csv"
WIDE = REPO / "mini_study" / "all_predictions_wide.csv"
OUT_MD = REPO / "mini_study" / "validation_metrics.md"
FIG = REPO / "figures" / "fig4_kappa.png"

LABELS = ["prokremlowski", "antywojenny", "prozachodni", "bialorusko-narodowy", "neutralny-informacyjny"]


def krippendorff_alpha_nominal(data: np.ndarray) -> float:
    """Nominal Krippendorff's alpha.
    data: (n_coders, n_items) array of labels (object dtype); use None/np.nan for missing.
    """
    # Build coincidence over items with >=2 coders
    # Map labels to ints
    vals = pd.unique(data[~pd.isnull(data)].ravel())
    val_idx = {v: i for i, v in enumerate(vals)}
    n_vals = len(vals)

    coincidence = np.zeros((n_vals, n_vals))
    for item in range(data.shape[1]):
        col = data[:, item]
        col = [c for c in col if not (c is None or (isinstance(c, float) and np.isnan(c)))]
        m = len(col)
        if m < 2:
            continue
        for a in range(m):
            for b in range(m):
                if a == b:
                    continue
                coincidence[val_idx[col[a]], val_idx[col[b]]] += 1.0 / (m - 1)

    n_total = coincidence.sum()
    if n_total == 0:
        return float("nan")
    nc = coincidence.sum(axis=1)  # marginal
    # observed disagreement
    Do = 0.0
    for c in range(n_vals):
        for k in range(n_vals):
            if c != k:
                Do += coincidence[c, k]
    # expected disagreement
    De = 0.0
    for c in range(n_vals):
        for k in range(n_vals):
            if c != k:
                De += nc[c] * nc[k]
    De = De / (n_total - 1)
    if De == 0:
        return float("nan")
    return 1.0 - Do / De


def main():
    wide = pd.read_csv(WIDE)
    self_test = not FILLED.exists()

    if self_test:
        print("[SELF-TEST MODE] No FILLED sheet — using claude_A as stand-in 'human' to verify pipeline.")
        wide["human_label"] = wide["claude_A"]
        human_src = "claude_A (SELF-TEST stand-in)"
    else:
        filled = pd.read_csv(FILLED, dtype=str, keep_default_na=False, na_values=[""])
        filled = filled.rename(columns={"YT_ID": "yt_id"})[["yt_id", "human_label"]]
        filled["human_label"] = filled["human_label"].str.strip().str.lower().str.replace("ł", "l").str.replace("białorusko", "bialorusko")
        wide = wide.merge(filled, on="yt_id", how="left")
        human_src = "coding_sheet_for_human_FILLED.csv"

    # Keep only items with a human label
    coded = wide[wide["human_label"].notna() & (wide["human_label"] != "")].copy()
    n = len(coded)
    print(f"Items with human label: {n}")

    configs = [c for c in ["claude_A", "claude_B", "gpt_A", "gpt_B"] if c in coded.columns]

    R = []
    R.append("# Validation metrics — human × LLM\n")
    R.append(f"Human source: **{human_src}**  |  N = {n} coded items\n")
    if self_test:
        R.append("> ⚠ **SELF-TEST MODE** — numbers below are placeholders (claude_A used as the "
                 "'human'). Re-run after `coding_sheet_for_human_FILLED.csv` exists for real κ.\n")

    # ---- Cohen's kappa: human vs each config ----
    R.append("## Cohen's κ — human vs each LLM config\n")
    R.append("| Config | Cohen's κ | Accuracy |")
    R.append("|---|---:|---:|")
    kappas = {}
    for c in configs:
        sub = coded[coded[c].notna()]
        if len(sub) < 2:
            continue
        k = cohen_kappa_score(sub["human_label"], sub[c])
        acc = (sub["human_label"] == sub[c]).mean()
        kappas[c] = k
        R.append(f"| {c} | {k:.3f} | {acc:.3f} |")
    R.append("")

    # ---- Krippendorff alpha across human + claude_A + gpt_A ----
    triplet = ["human_label"] + [c for c in ["claude_A", "gpt_A"] if c in coded.columns]
    arr = coded[triplet].to_numpy(dtype=object)
    alpha = krippendorff_alpha_nominal(arr.T)
    R.append("## Krippendorff's α (nominal)\n")
    R.append(f"- Across {{{', '.join(triplet)}}}: **α = {alpha:.3f}**\n")

    # ---- Per-class precision/recall/F1 (human = gold), for claude_A and gpt_A ----
    for c in [x for x in ["claude_A", "gpt_A"] if x in coded.columns]:
        sub = coded[coded[c].notna()]
        R.append(f"## Per-class precision / recall / F1 — {c} (human = gold)\n")
        rep = classification_report(sub["human_label"], sub[c], labels=LABELS,
                                    output_dict=True, zero_division=0)
        R.append("| Class | precision | recall | F1 | support |")
        R.append("|---|---:|---:|---:|---:|")
        for lbl in LABELS:
            d = rep.get(lbl, {})
            R.append(f"| {lbl} | {d.get('precision',0):.2f} | {d.get('recall',0):.2f} | "
                     f"{d.get('f1-score',0):.2f} | {int(d.get('support',0))} |")
        R.append(f"| **macro avg** | {rep['macro avg']['precision']:.2f} | "
                 f"{rep['macro avg']['recall']:.2f} | {rep['macro avg']['f1-score']:.2f} | {n} |")
        R.append(f"| **weighted avg** | {rep['weighted avg']['precision']:.2f} | "
                 f"{rep['weighted avg']['recall']:.2f} | {rep['weighted avg']['f1-score']:.2f} | {n} |")
        R.append("")

    # ---- Confusion matrices figure ----
    cms = [c for c in ["claude_A", "gpt_A"] if c in coded.columns]
    if cms:
        fig, axes = plt.subplots(1, len(cms), figsize=(6.5 * len(cms), 5.5))
        if len(cms) == 1:
            axes = [axes]
        short = [l.split("-")[0][:8] for l in LABELS]
        for ax, c in zip(axes, cms):
            sub = coded[coded[c].notna()]
            cm = confusion_matrix(sub["human_label"], sub[c], labels=LABELS)
            im = ax.imshow(cm, cmap="Blues")
            ax.set_xticks(range(len(LABELS))); ax.set_xticklabels(short, rotation=45, ha="right", fontsize=8)
            ax.set_yticks(range(len(LABELS))); ax.set_yticklabels(short, fontsize=8)
            ax.set_xlabel(f"{c} label"); ax.set_ylabel("human label")
            kv = kappas.get(c, float('nan'))
            ax.set_title(f"human × {c}   κ={kv:.2f}", fontsize=11)
            for i in range(len(LABELS)):
                for j in range(len(LABELS)):
                    ax.text(j, i, cm[i, j], ha="center", va="center",
                            color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=9)
        fig.suptitle("Confusion matrices — where the LLM diverges from the human coder", fontsize=13)
        fig.tight_layout()
        fig.savefig(FIG, dpi=150, bbox_inches="tight")
        R.append(f"## Confusion matrices\n\nSee `figures/fig4_kappa.png`.\n")
        print(f"Wrote {FIG}")

    OUT_MD.write_text("\n".join(R), encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    if kappas:
        print("\n>>> κ:", {k: round(v, 3) for k, v in kappas.items()})
        print(f">>> Krippendorff α = {alpha:.3f}")


if __name__ == "__main__":
    main()
