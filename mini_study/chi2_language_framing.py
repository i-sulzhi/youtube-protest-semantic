"""χ² test: is the FRAMING label independent of LANGUAGE? (slide-8 companion)

Uses GPT-4o framing labels on the full 200-item sample (gpt_promptA_full200.jsonl)
cross-tabulated against language_norm. If framing were purely a function of
language, the cross-tab would be highly dependent (large χ², high Cramér's V).
If framing cross-cuts language, dependence is weaker.

This complements the embedding-level centroid analysis (language_vs_framing.py):
that one asks "how is the vector space organised"; this one asks "does the
discrete framing label track language".

Outputs:
  mini_study/chi2_language_framing.md
  figures/data/lang_framing_crosstab.csv
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

REPO = Path(__file__).resolve().parent.parent
SAMPLE = REPO / "mini_study" / "sample.csv"
GPT_FULL = REPO / "mini_study" / "llm_predictions" / "gpt_promptA_full200.jsonl"
OUT_MD = REPO / "mini_study" / "chi2_language_framing.md"
CROSSTAB_CSV = REPO / "figures" / "data" / "lang_framing_crosstab.csv"

LABELS = ["prokremlowski", "antywojenny", "prozachodni", "bialorusko-narodowy", "neutralny-informacyjny"]


def cramers_v(confusion):
    chi2 = chi2_contingency(confusion, correction=False)[0]
    n = confusion.sum().sum()
    r, k = confusion.shape
    phi2 = chi2 / n
    return np.sqrt(phi2 / min(k - 1, r - 1))


def main():
    sample = pd.read_csv(SAMPLE, dtype=str, keep_default_na=False, na_values=[""])
    preds = []
    for ln in GPT_FULL.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln:
            preds.append(json.loads(ln))
    pred_df = pd.DataFrame(preds)[["yt_id", "label"]].rename(columns={"yt_id": "YT_ID", "label": "framing"})
    pred_df["framing"] = pred_df["framing"].str.strip().str.lower().str.replace("ł", "l").str.replace("białorusko", "bialorusko")

    df = sample.merge(pred_df, on="YT_ID", how="inner")
    print(f"merged: {len(df)} items with framing labels")

    # Cross-tab language × framing
    ct = pd.crosstab(df["language_norm"], df["framing"])
    # keep only main languages (drop tiny buckets that break χ²)
    ct = ct.loc[ct.sum(axis=1) >= 5]
    ct = ct.reindex(columns=[l for l in LABELS if l in ct.columns], fill_value=0)
    ct.to_csv(CROSSTAB_CSV)

    chi2, p, dof, exp = chi2_contingency(ct.values, correction=False)
    v = cramers_v(ct.values)

    # Within-language framing entropy vs overall
    def entropy(counts):
        p = counts / counts.sum()
        p = p[p > 0]
        return float(-(p * np.log2(p)).sum())

    overall_ent = entropy(df["framing"].value_counts().values)
    per_lang_ent = {lang: entropy(sub["framing"].value_counts().values)
                    for lang, sub in df.groupby("language_norm") if len(sub) >= 5}

    R = []
    R.append("# χ² test — is framing independent of language? (N=200 sample, GPT-4o labels)\n")
    R.append(f"Items: {len(df)}  |  GPT-4o prompt A framing labels on the full stratified sample.\n")
    R.append("## Cross-tabulation: language × framing\n")
    R.append("```")
    R.append(ct.to_string())
    R.append("```\n")
    R.append("## χ² test of independence\n")
    R.append(f"- χ²({dof}) = **{chi2:.1f}**, p = **{p:.2e}**")
    R.append(f"- Cramér's V = **{v:.3f}**  (0=independent, 1=perfect dependence)\n")
    if p < 0.05:
        strength = ("weak" if v < 0.2 else "moderate" if v < 0.4 else "strong")
        R.append(f"> Framing and language are **statistically dependent** (p<0.05), but the "
                 f"association is **{strength}** (V={v:.3f}). ")
        if v < 0.4:
            R.append(f"> A {strength} V means framing is **not reducible to language** — the same "
                     f"framing category appears across multiple languages, and each language hosts "
                     f"multiple framings. This supports the talk's thesis that **framing cross-cuts "
                     f"language**.\n")
        else:
            R.append(f"> A strong V means framing is **largely predictable from language** in this "
                     f"sample — an honest qualification of the thesis.\n")
    else:
        R.append("> No statistically significant dependence — framing labels are distributed "
                 "independently of language (supports framing cross-cuts language).\n")

    R.append("## Framing entropy (bits) — how mixed is each language's framing?\n")
    R.append(f"- Overall framing entropy: {overall_ent:.2f} bits (max for 5 classes = 2.32)")
    R.append("")
    R.append("| Language | n | framing entropy |")
    R.append("|---|---:|---:|")
    for lang, sub in df.groupby("language_norm"):
        if len(sub) >= 5:
            R.append(f"| {lang} | {len(sub)} | {per_lang_ent[lang]:.2f} |")
    R.append("")
    R.append("> High per-language entropy = that language hosts many framings (framing not "
             "determined by language). Low entropy = that language is dominated by one framing.\n")

    R.append("## Framing distribution by language (row %)\n")
    pct = (ct.div(ct.sum(axis=1), axis=0) * 100).round(1)
    R.append("```")
    R.append(pct.to_string())
    R.append("```")

    OUT_MD.write_text("\n".join(R), encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f">>> chi2={chi2:.1f}, p={p:.2e}, Cramér's V={v:.3f}")


if __name__ == "__main__":
    main()
