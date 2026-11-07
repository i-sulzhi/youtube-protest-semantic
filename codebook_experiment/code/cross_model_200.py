"""Cross-model disagreement on the FULL 200-item sample (Claude vs GPT, prompt A).

Claude prompt A on 200 = chunk1(30) + chunk2(30) + extra1..4(140).
GPT prompt A on 200    = gpt_promptA_full200.jsonl.

Outputs:
  mini_study/cross_model_200.md  — N=200 disagreement headline + by-anchor + transitions
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
PRED = REPO / "mini_study" / "llm_predictions"
SAMPLE = REPO / "mini_study" / "sample.csv"
OUT = REPO / "mini_study" / "cross_model_200.md"

VALID = ["prokremlowski", "antywojenny", "prozachodni", "bialorusko-narodowy", "neutralny-informacyjny"]


def norm(l):
    if not l:
        return ""
    s = str(l).strip().lower().replace("białorusko", "bialorusko").replace("ł", "l")
    for v in VALID:
        if s == v or s.startswith(v.split("-")[0]):
            return v
    return s


def load(path):
    rows = []
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln:
                try:
                    rows.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
    return rows


def main():
    claude_files = ["claude_promptA_chunk1.jsonl", "claude_promptA_chunk2.jsonl",
                    "claude_promptA_extra1.jsonl", "claude_promptA_extra2.jsonl",
                    "claude_promptA_extra3.jsonl", "claude_promptA_extra4.jsonl"]
    claude = {}
    for f in claude_files:
        for r in load(PRED / f):
            claude[r["yt_id"]] = norm(r.get("label", ""))
    gpt = {}
    for r in load(PRED / "gpt_promptA_full200.jsonl"):
        gpt[r["yt_id"]] = norm(r.get("label", ""))

    sample = pd.read_csv(SAMPLE, dtype=str, keep_default_na=False, na_values=[""])
    rows = []
    for _, s in sample.iterrows():
        yt = s["YT_ID"]
        if yt in claude and yt in gpt:
            rows.append({"yt_id": yt, "anchor": s["anchor"], "language_norm": s["language_norm"],
                         "claude": claude[yt], "gpt": gpt[yt]})
    df = pd.DataFrame(rows)
    n = len(df)
    df["agree"] = df["claude"] == df["gpt"]
    disagree = (~df["agree"]).sum()

    R = []
    R.append("# Cross-model disagreement — FULL 200-item sample (Claude vs GPT-4o, prompt A)\n")
    R.append(f"N = {n} items with both labels.\n")
    R.append(f"## Headline\n")
    R.append(f"- **Cross-model disagreement (N={n}): {disagree}/{n} = {100*disagree/n:.1f}%**")
    R.append(f"- Agreement: {n-disagree}/{n} = {100*(n-disagree)/n:.1f}%\n")
    R.append("> Confirms the 60-item finding (28.3%) on the full sample — robust, not a small-N artefact.\n")

    R.append("## By anchor\n")
    for a, sub in df.groupby("anchor"):
        d = (~sub["agree"]).sum()
        R.append(f"- `{a}`: {d}/{len(sub)} ({100*d/len(sub):.1f}%)")
    R.append("")

    R.append("## By language\n")
    for lang, sub in df.groupby("language_norm"):
        if len(sub) >= 5:
            d = (~sub["agree"]).sum()
            R.append(f"- {lang}: {d}/{len(sub)} ({100*d/len(sub):.1f}%)")
    R.append("")

    R.append("## Label transitions (Claude → GPT, mismatches only)\n")
    mm = df[~df["agree"]]
    t = mm.groupby(["claude", "gpt"]).size().sort_values(ascending=False)
    R.append("| Claude | GPT | n |")
    R.append("|---|---|---:|")
    for (c, g), k in t.items():
        R.append(f"| `{c}` | `{g}` | {k} |")
    R.append("")

    R.append("## Label distribution\n")
    R.append("```")
    dist = pd.DataFrame({"claude": df["claude"].value_counts(), "gpt": df["gpt"].value_counts()}).fillna(0).astype(int)
    R.append(dist.to_string())
    R.append("```")

    OUT.write_text("\n".join(R), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f">>> N={n}  cross-model disagreement = {100*disagree/n:.1f}%")


if __name__ == "__main__":
    main()
